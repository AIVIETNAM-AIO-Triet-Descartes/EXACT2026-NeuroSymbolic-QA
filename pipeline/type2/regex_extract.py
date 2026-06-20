"""
pipeline/type2/regex_extract.py

Deterministic regex pre-pass for physics variable extraction — NO LLM required.

Addresses weakness #3 (docs/weakness.md): variable extraction was fully
LLM-dependent, so a malformed JSON or a down vLLM server left `given={}` /
`find=""` and dropped confidence to 0.3. This module extracts the obvious
`symbol = value unit` assignments (with SI conversion, scientific/bare-power
notation, chained and negated-chain assignments) before the LLM is called.

The patterns here are the proven ones from `scripts/demo_type2.py` (regex demo
path, ~78% on the evaluable subset), lifted into a shared module so the pipeline
node `physics_parser_node` and the demo can converge on one source of truth.

Public API:
    extract_given(question)        -> dict[str, float]   # {symbol: SI_value}
    detect_find_from_verb(question)-> str | None         # target symbol from verb context
"""

import re
from typing import Optional

# ── SI unit conversion table (prefix+base → SI factor) ────────────────────────
# Micro prefix is keyed ASCII "u" ONLY (μF → uF). Both Unicode micro glyphs
# (μ U+03BC greek mu, µ U+00B5 micro sign) are normalized to "u" by
# _unit_factor() before lookup, so an input may use μF / µF / uF interchangeably
# and resolve to the single canonical key. This kills the old dual-maintenance
# bug class where μV existed but uV did not (silent 1e6 error). Ω stays Unicode
# here (the table is Ω-keyed: Ω/kΩ/MΩ); ASCII-ohm is an OUTPUT concern (units.py).
_UNIT_FACTORS: dict[str, float] = {
    # Capacitance
    "pF": 1e-12, "nF": 1e-9, "uF": 1e-6, "mF": 1e-3, "F": 1.0,
    # Resistance
    "mΩ": 1e-3, "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
    # Current
    "uA": 1e-6, "mA": 1e-3, "A": 1.0, "kA": 1e3,
    # Voltage
    "uV": 1e-6, "mV": 1e-3, "V": 1.0, "kV": 1e3,
    # Power
    "uW": 1e-6, "mW": 1e-3, "W": 1.0, "kW": 1e3, "MW": 1e6,
    # Energy
    "uJ": 1e-6, "mJ": 1e-3, "J": 1.0, "kJ": 1e3,
    # Charge
    "nC": 1e-9, "uC": 1e-6, "mC": 1e-3, "C": 1.0,
    # Inductance
    "uH": 1e-6, "mH": 1e-3, "H": 1.0,
    # Length (for distance-based formulas)
    "mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3,
    # Frequency
    "Hz": 1.0, "kHz": 1e3, "MHz": 1e6,
    # Force
    "N": 1.0,
    # Time
    "s": 1.0, "ms": 1e-3, "us": 1e-6, "min": 60.0, "minute": 60.0, "minutes": 60.0, "h": 3600.0, "hour": 3600.0, "hours": 3600.0,
    # Area
    "mm2": 1e-6, "mm²": 1e-6, "mm^2": 1e-6, "cm2": 1e-4, "cm²": 1e-4, "cm^2": 1e-4,
    # Velocity & Acceleration
    "m/s": 1.0, "m/s2": 1.0, "m/s²": 1.0, "m/s^2": 1.0,
}


def _unit_factor(unit_str: str) -> float:
    """SI factor for a unit token. Normalizes the micro prefix (μ/µ → u) so the
    Unicode and ASCII spellings share one canonical key. Unknown unit → 1.0
    (numeric still extracted; only the prefix scaling is lost)."""
    u = unit_str.replace("μ", "u").replace("µ", "u")
    return _UNIT_FACTORS.get(u, 1.0)

# Voltage symbol convention (Vietnamese curriculum):
#   U = hiệu điện thế (potential difference / voltage)  ← canonical in the RAG DB
#   V = điện thế      (electric potential, only V = k*q/r)
# Questions may use V for hiệu điện thế (foreign convention); normalize V→U
# UNLESS the question is about điện thế (electric potential at a point). See the
# normalizer at the end of extract_given().
_POTENTIAL_CONTEXT_PAT = re.compile(
    r'electric\s+potential(?!\s+energy)|'   # "electric potential" but not "...energy"
    r'potential\s+at\s+a?\s*point|'
    r'điện\s+thế',
    re.IGNORECASE,
)

# Matches: SYM = MANTISSA [× 10^EXP] [UNIT]
_ASSIGN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'              # symbol =
    r'([+-]?[\d.]+)'                         # mantissa (optional sign)
    r'(?:\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'  # × 10^exp (optional, hex \xd7 for ×)
    r'\s*([μuμnmkMGp]?[A-Za-z0-9\^²Ωμµ/]{1,6})?'   # unit prefix+base (optional)
)

# Bare power notation: SYM = MANTISSA^EXP UNIT  e.g. "q1 = 10^-8 C"
_BARE_POWER_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'
    r'([+-]?[\d.]+)\^([+-]?\d+)'            # mantissa^exp (pure power, no ×10)
    r'\s*([μuμnmkMGp]?[A-Za-z0-9\^²Ωμµ/]{1,6})?'
)

# "X cm apart" / "separated by X cm" → AB distance
_APART_PAT = re.compile(
    r'([\d.]+)\s*(cm|m)\s+apart|'
    r'separated\s+by\s+([\d.]+)\s*(cm|m)',
    re.IGNORECASE,
)

# Triangle/polygon side length → `a`. Covers "side length of 10 cm", "sides of
# length 10 cm", "side of 10 cm", "legs of 0.1 m", "side length 10 cm". The old
# pattern allowed "length " OR "of " but NOT "length of " together, so the common
# "side length of 10 cm" phrasing was missed (LD010 etc. fell back).
_SIDE_PAT = re.compile(
    r'\b(?:sides?|legs?)\s+(?:length\s+)?(?:of\s+(?:length\s+)?)?([\d.]+)\s*(cm|m)\b',
    re.IGNORECASE,
)

# "X cm away from AB" / "X cm from AB" → perpendicular bisector distance
_BISECTOR_DIST_PAT = re.compile(
    r'([\d.]+)\s*(cm|m)\s+(?:away\s+from|from)\s+(?:AB|the\s+line|segment\s+AB)',
    re.IGNORECASE,
)

# Chained assignment: q1 = q2 = q3 = value unit
_CHAIN_PAT = re.compile(
    r'\b([A-Za-z_]\w*(?:\s*=\s*[A-Za-z_]\w*)+)'  # q1 = q2 = q3
    r'\s*=\s*([-]?[\d.]+)'                          # = value
    r'(?:\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'
    r'\s*([μuμnmkMGp]?[A-Za-z0-9\^²Ωμµ/]{1,6})?',
)

# Verb-context target detector: "calculate the energy" → "E"
# NOTE: dict order matters — detect_find_from_verb returns the FIRST kw substring
# match. "potential energy" and "electric potential" must precede the looser
# "potential"/"energy" cues so U (hiệu điện thế) vs V (điện thế) vs W (thế năng)
# disambiguate correctly. U = hiệu điện thế, V = điện thế.
from pipeline.type2.symbol_registry import CANONICAL as _VERB_TARGET_MAP
_VERB_PAT = re.compile(
    r'\b(?:calculate|find|determine|compute|what\s+is)\s+(?:the\s+)?'
    r'((?:[a-zA-Z]+\s+){0,2}[a-zA-Z]+)',
    re.IGNORECASE,
)
_FORCE_PHRASE_PAT = re.compile(
    r'magnitude\s+of\s+(?:the\s+)?(?:net\s+)?(?:electric\s+)?force|'
    r'net\s+(?:electric\s+)?force|'
    r'resultant\s+force\s+(?:acting|on)|'
    r'force\s+exerted|'
    r'force\s+acting',
    re.IGNORECASE,
)
_E_FIELD_PHRASE_PAT = re.compile(
    r'electric\s+field\s+(?:strength|intensity|vector|magnitude|at)|'
    r'field\s+strength|'
    r'electric\s+field\s+caused|'
    r'electric\s+field\s+produced|'
    r'resultant\s+electric\s+field',
    re.IGNORECASE,
)
_ANGLE_PHRASE_PAT = re.compile(
    r'find\s+the\s+angle|'
    r'determine\s+the\s+angle|'
    r'angle\s+between\s+the\s+two\s+force',
    re.IGNORECASE,
)
# Negated chain: "q1 = -q2 = VALUE UNIT" → q1=+val, q2=-val
_NEG_CHAIN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*-([A-Za-z_]\w*)\s*=\s*([+-]?[\d.]+)'
    r'(?:\^([+-]?\d+)|\s*[x\*\xd7]\s*10\^?([=\-]?\d+))?'  # bare ^exp OR ×10^exp
    r'\s*([μuμnmkMGp]?[A-Za-z0-9\^²Ωμµ/]{1,6})?'
)

# Expression-valued assignment (fraction / sqrt / mixed scientific) that the
# plain decimal _ASSIGN_PAT cannot represent, e.g. "q = (1)/(3) × 10^-6 C",
# "q = 9*sqrt(3)×10^-27 C", "F = √3 N". The value blob is a run of math tokens
# (digits, operators, parens, sqrt, √); a trailing alphabetic unit is captured
# separately. The blob is validated by SymPy in _eval_value_expr — an over-greedy
# or garbage capture simply fails to evaluate to a finite real and is dropped
# (safe). Only used when the value carries an expression marker (see _EXPR_MARKERS)
# so it never steals plain numerics from _ASSIGN_PAT.
_EXPR_ASSIGN_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'
    r'((?:sqrt|[\d.+\-*/()^×x√])(?:sqrt|[\d.\s+\-*/()^×x√])*)'  # math blob
    r'\s*([μuµnmkMGp]?[A-Za-z0-9\^²Ωμµ/]{1,6})?'                          # optional unit
)
_EXPR_MARKERS = ('(', ')', '/', 'sqrt', '√')

# Unicode superscript digits/minus → ASCII helper
_SUP_TABLE = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺', '0123456789-+')

# Unicode minus-sign variants → ASCII '-'. The dataset writes negative charges
# with en-dash/minus-sign ("q2 = –5 × 10^-9 C") which _ASSIGN_PAT's [+-] class
# does NOT match → the charge was silently dropped (E-field computed from one
# charge instead of two → confident-wrong, e.g. LD060/LD064). Normalize first.
_MINUS_TABLE = str.maketrans('–—−‐‑', '-----')


def _normalize_superscripts(text: str) -> str:
    return text.translate(_SUP_TABLE)


def _eval_value_expr(expr: str) -> Optional[float]:
    """
    Evaluate a math-expression value (fraction / sqrt / scientific) to a float via
    SymPy — deterministic, NO LLM. Notation is normalized to SymPy form first
    (√→sqrt, ^→**, ×·→*). Returns None unless the expression resolves to a finite
    real with no free symbols, so a garbage capture is safely dropped rather than
    poisoning the solver. Keeps the symbolic math in SymPy (PAL): the LLM never
    does the arithmetic.
    """
    s = _normalize_superscripts(expr).strip()
    if not s or len(s) > 200:
        return None
    s = re.sub(r'√\s*\(', 'sqrt(', s)                      # √( → sqrt(
    s = re.sub(r'√\s*(\d+(?:\.\d+)?)', r'sqrt(\1)', s)     # √3 → sqrt(3)
    s = s.replace('×', '*').replace('·', '*').replace('^', '**')  # ^ is XOR in SymPy
    s = re.sub(r'(?<=[\d).])\s*x\s*(?=[\d(])', '*', s)     # "3 x 10" → "3*10"
    try:
        from sympy import sympify
        val = sympify(s, locals={})
        if not val.free_symbols and val.is_real:
            return float(val.evalf())
    except Exception:
        return None
    return None


# ── Phrasal value extraction ──────────────────────────────────────────────────
# The dataset frequently states quantities in PROSE — "impedance of 120 Ω",
# "charged to a voltage of 600 V", "current is 0.5 A" — not the `symbol = value`
# form _ASSIGN_PAT needs. Measured on the full no-LLM floor, ~446 of 977 fallback
# questions had EMPTY regex `given` purely because of this. Each entry maps a noun
# cue to a canonical symbol PLUS the SI-dimension units that legitimise the match,
# so a length ("radius of 10 cm") can never be mistaken for a resistance. Explicit
# `sym = value` always wins — phrasal only fills a symbol NOT already extracted.
#
# Ordering matters: multi-word cues ("inductive reactance") precede the looser
# substrings ("reactance"); the first field that fills a symbol wins via setdefault.
_PHRASAL_CONNECT = (
    r'(?:\s+(?:[A-Za-z_]\w*\s+)?'                       # optional symbol token (e.g. "Z")
    r'(?:of\s+about|of|is|are|was|equal\s+to|equals?|'
    r'reads?|measured(?:\s+(?:as|to\s+be))?|measuring|about|at|=|:)\s+)'
)
_PHRASAL_NUM = r'([+-]?\d+(?:\.\d+)?)(?:\s*[x×*]\s*10\^?([-]?\d+))?\s*'
_OHM = r'(m?Ω|[kM]?Ω|ohms?)'
_VOLT = r'(k?V|mV)(?![/\w])'
_AMP = r'([umµμ]?A|kA)\b'
_FARAD = r'([pnumµμ]?F)\b'
_HENRY = r'([umµμ]?H)\b'
_HZ = r'(k?Hz|MHz)'
_WATT = r'([umµμkM]?W)\b'
_JOULE = r'([umµμk]?J)\b'
_COUL = r'([numµμ]?C)\b'
_TESLA = r'(m?T)\b'
_M_S = r'(m/s)'
_M_S2 = r'(m/s\^2|m/s²|m/s2)'
_M = r'(m|cm|mm)\b'
_SEC = r'(s|ms|us|min|minutes|minute|h|hour|hours)\b'

_PHRASAL_FIELDS: list[tuple[str, str, str]] = [
    (r'inductive\s+reactance', 'Z_L', _OHM),
    (r'capacitive\s+reactance', 'Z_C', _OHM),
    (r'impedance',              'Z',   _OHM),
    (r'resistance',             'R',   _OHM),
    (r'capacitance',            'C',   _FARAD),
    (r'self[-\s]?inductance',   'L',   _HENRY),
    (r'inductance',             'L',   _HENRY),
    (r'potential\s+difference', 'U',   _VOLT),
    (r'voltage',                'U',   _VOLT),
    (r'electromotive\s+force',  'e', _VOLT),
    (r'\bemf\b',                'e', _VOLT),
    (r'current',                'I',   _AMP),
    (r'frequency',              'f',   _HZ),
    (r'\bpower\b',              'P',   _WATT),
    (r'energy',                 'E',   _JOULE),
    (r'charge',                 'Q',   _COUL),
    (r'magnetic\s+field',       'B',   _TESLA),
    (r'initial\s+velocity|initial\s+speed', 'u', _M_S),
    (r'final\s+velocity|final\s+speed', 'v', _M_S),
    (r'velocity|speed',         'v',   _M_S),
    (r'acceleration',           'a',   _M_S2),
    (r'distance|displacement|braking\s+distance', 's', _M),
    (r'time|duration',          't',   _SEC),
]
_PHRASAL_COMPILED = [
    (re.compile(f"(?:{noun}){_PHRASAL_CONNECT}{_PHRASAL_NUM}{unit}", re.IGNORECASE), sym)
    for noun, sym, unit in _PHRASAL_FIELDS
]


# Multi-charge / vector-geometry cue. Phrasal extraction must NOT fire on these:
# LD/DT Coulomb problems are solved by vector_solver (which does its own parsing),
# and injecting a phrasal "charge of … / force of …" value pollutes `given` and
# breaks the vector strategy selection (measured: 30 previously-correct vector
# solves regressed). vector_solver territory stays phrasal-free.
_VECTOR_CUE_PAT = re.compile(
    r'\bq_?[1-9]\b|\bcharges\b|triangle|vertic|equilateral|midpoint|'
    r'placed\s+at|corner|two\s+charges|three\s+charges',
    re.IGNORECASE,
)


def _extract_phrasal(question: str, given: dict) -> set:
    """Fill `given` from prose statements of quantities (unit-dimension gated).
    Mutates `given` in place; only sets symbols NOT already present. Skipped for
    multi-charge/vector problems (vector_solver owns those — see _VECTOR_CUE_PAT).
    Returns the set of symbols this pass added (for downstream reliability gating)."""
    added: set = set()
    if _VECTOR_CUE_PAT.search(question):
        return added
    for pat, sym in _PHRASAL_COMPILED:
        if sym in given:
            continue
        m = pat.search(question)
        if not m:
            continue
        mantissa = float(m.group(1))
        exp_str = m.group(2)
        unit_str = m.group(3) or ""
        val = mantissa * (10 ** int(exp_str) if exp_str else 1)
        given[sym] = val * _unit_factor(unit_str)
        added.add(sym)
    return added


def detect_find_from_verb(question: str) -> Optional[str]:
    """Extract target variable from verb context ('calculate the force' → 'F')."""
    if _ANGLE_PHRASE_PAT.search(question):
        return "angle"
    # E-field check before force check (some E-field questions mention "force")
    if _E_FIELD_PHRASE_PAT.search(question):
        return "E_field"
    if _FORCE_PHRASE_PAT.search(question):
        return "F"
    for m in _VERB_PAT.finditer(question):
        noun = m.group(1).lower().strip()
        for kw, sym in _VERB_TARGET_MAP.items():
            if kw in noun:
                return sym
    return None


def extract_given(question: str, return_phrasal: bool = False):
    """
    Extract {symbol: SI_value} from question text via regex.

    When return_phrasal=True, returns (given, phrasal_keys) where phrasal_keys is
    the set of symbols filled ONLY by the prose/phrasal pass (less reliable than
    explicit `sym = value`) — callers use it to gate fallback. Default returns the
    plain dict (backward-compatible with demo / existing callers).
    Handles: C = 100 μF, q1 = 6 × 10^-8 C, chained and negated-chain assignments,
    bare-power notation, expression values evaluated by SymPy (q = (1)/(3)×10^-6 C,
    F = 9*sqrt(3)×10^-27 N, √3), and a few geometry distances (AB, side, bisector).
    """
    given: dict[str, float] = {}
    # Normalize Unicode superscripts (⁻⁸ → -8) and minus-sign variants (– − → -)
    # before regex matching, so signed values parse regardless of glyph.
    question = _normalize_superscripts(question).translate(_MINUS_TABLE)

    for m in _ASSIGN_PAT.finditer(question):
        sym = m.group(1)
        mantissa = float(m.group(2).rstrip("."))  # tolerate value at sentence end ("0.8.")
        exp_str = m.group(3)
        unit_str = m.group(4) or ""

        val = mantissa
        if exp_str:
            val *= 10 ** int(exp_str.replace("−", "-"))

        val_si = val * _unit_factor(unit_str)
        given[sym] = val_si

    # Expression-valued assignments (fraction / sqrt / mixed scientific) that the
    # plain decimal pattern above cannot represent. SymPy-evaluated, deterministic.
    # Only fires when the value carries an expression marker — plain numerics are
    # left to _ASSIGN_PAT, so this adds no regression on the common case.
    for m in _EXPR_ASSIGN_PAT.finditer(question):
        raw_val = m.group(2)
        if not any(mk in raw_val for mk in _EXPR_MARKERS):
            continue
        val = _eval_value_expr(raw_val)
        if val is None:
            continue
        given[m.group(1)] = val * _unit_factor(m.group(3) or "")

    # "X cm apart" / "separated by X cm" → AB separation distance
    for m in _APART_PAT.finditer(question):
        if m.group(1):
            val, unit = float(m.group(1)), m.group(2)
        else:
            val, unit = float(m.group(3)), m.group(4)
        factor = 0.01 if unit.lower() == "cm" else 1.0
        if "AB" not in given:
            given["AB"] = val * factor

    # "side length X cm" → a (equilateral/polygon side length)
    for m in _SIDE_PAT.finditer(question):
        if "a" not in given:
            val = float(m.group(1))
            factor = 0.01 if m.group(2).lower() == "cm" else 1.0
            given["a"] = val * factor

    # Chained: q1 = q2 = q3 = value unit → assign all
    for m in _CHAIN_PAT.finditer(question):
        syms_part = m.group(1)
        mantissa = float(m.group(2))
        exp_str = m.group(3)
        unit_str = m.group(4) or ""
        val = mantissa * (10 ** int(exp_str.replace("−", "-")) if exp_str else 1)
        val_si = val * _unit_factor(unit_str)
        for sym in re.findall(r'[A-Za-z_]\w*', syms_part):
            given[sym] = val_si

    # Bare power: "q1 = 10^-8 C" → 10^(-8) = 1e-8
    for m in _BARE_POWER_PAT.finditer(question):
        sym = m.group(1)
        mantissa = float(m.group(2))
        exp = int(m.group(3))
        unit_str = m.group(4) or ""
        sign = -1.0 if mantissa < 0 else 1.0
        val_si = sign * (abs(mantissa) ** exp) * _unit_factor(unit_str)
        given[sym] = val_si

    # Negated chain: "q1 = -q2 = 10^-7 C" → q1=+1e-7, q2=-1e-7
    for m in _NEG_CHAIN_PAT.finditer(question):
        sym_pos, sym_neg = m.group(1), m.group(2)
        mantissa = float(m.group(3))
        bare_exp = m.group(4)
        sci_exp = m.group(5)
        unit_str = m.group(6) or ""
        if bare_exp:
            sign = -1.0 if mantissa < 0 else 1.0
            val = sign * (abs(mantissa) ** int(bare_exp))
        elif sci_exp:
            val = mantissa * (10 ** int(sci_exp.replace("−", "-")))
        else:
            val = mantissa
        val_si = val * _unit_factor(unit_str)
        given[sym_pos] = val_si
        given[sym_neg] = -val_si

    # "X cm away from AB" → d_perp (perpendicular bisector offset)
    for m in _BISECTOR_DIST_PAT.finditer(question):
        if "d_perp" not in given:
            val = float(m.group(1))
            factor = 0.01 if m.group(2).lower() == "cm" else 1.0
            given["d_perp"] = val * factor

    # Phrasal value extraction (prose form: "impedance of 120 Ω", "current is
    # 0.5 A") — runs AFTER explicit `sym = value` so deterministic assignments
    # win; only fills symbols still missing. Unit-dimension gated (see above).
    phrasal_keys = _extract_phrasal(question, given)

    # Bare unit extraction (prose form: "across an 18 V battery", "connected to a 12 V source")
    # Only maps units to their canonical symbols when the symbol is completely missing from given.
    normalized_q = question.replace("μ", "u").replace("µ", "u")
    bare_pattern = re.compile(
        r'\b([+-]?\d+(?:\.\d+)?)\s*(?:[x\*\xd7]\s*10\^?([=\-]?\d+))?\s*'
        r'(uV|mV|V|kV|uA|mA|A|kA|mΩ|Ω|kΩ|MΩ|ohm|ohms|pF|nF|uF|mF|F|uH|mH|H|Hz|kHz|MHz|uW|mW|W|kW|MW|uJ|mJ|J|kJ|nC|uC|mC|C|N|mT|T|s|ms|us|min|minute|minutes|h|hour|hours|mm2|mm²|mm\^2|cm2|cm²|cm\^2|m/s|m/s2|m/s²|m/s\^2)\b',
        re.IGNORECASE
    )
    unit_to_sym = {
        "V": "U", "uV": "U", "mV": "U", "kV": "U",
        "A": "I", "uA": "I", "mA": "I", "kA": "I",
        "Ω": "R", "mΩ": "R", "kΩ": "R", "MΩ": "R", "ohm": "R", "ohms": "R",
        "F": "C", "pF": "C", "nF": "C", "uF": "C", "mF": "C",
        "H": "L", "uH": "L", "mH": "L",
        "Hz": "f", "kHz": "f", "MHz": "f",
        "W": "P", "uW": "P", "mW": "P", "kW": "P", "MW": "P",
        "J": "W", "uJ": "W", "mJ": "W", "kJ": "W",
        "C": "Q", "nC": "Q", "uC": "Q", "mC": "Q",
        "N": "F",
        "T": "B", "mT": "B",
        "s": "t", "ms": "t", "us": "t", "min": "t", "minute": "t", "minutes": "t", "h": "t", "hour": "t", "hours": "t",
        "mm2": "S", "mm²": "S", "mm^2": "S", "cm2": "S", "cm²": "S", "cm^2": "S",
        "m/s": "v", "m/s2": "a", "m/s²": "a", "m/s^2": "a",
    }
    for m in bare_pattern.finditer(normalized_q):
        # Compound unit guard: do not match simple units if they are part of a compound unit
        # (e.g. followed or preceded by * or / or -)
        start_idx = m.start()
        end_idx = m.end()
        if start_idx > 0 and normalized_q[start_idx-1] in ('*', '/', '·'):
            continue
        if end_idx < len(normalized_q) and normalized_q[end_idx] in ('*', '/', '·'):
            continue

        mantissa = float(m.group(1))
        exp_str = m.group(2)
        unit = m.group(3)
        val = mantissa
        if exp_str:
            val *= 10 ** int(exp_str)
        canonical_sym = unit_to_sym.get(unit.upper() if unit.upper() in unit_to_sym else unit)
        if not canonical_sym:
            u_norm = unit.lower()
            if u_norm in ("ohm", "ohms"):
                canonical_sym = "R"
            elif u_norm == "μf" or u_norm == "uf":
                canonical_sym = "C"
            else:
                continue
        has_sym = any(k == canonical_sym or k.startswith(canonical_sym) and k[len(canonical_sym):].isdigit() for k in given)
        if not has_sym:
            given[canonical_sym] = val * _unit_factor(unit)
            if return_phrasal:
                phrasal_keys.add(canonical_sym)

    # Voltage symbol normalization: a question may write V for hiệu điện thế
    # (foreign convention). The RAG DB uses U for hiệu điện thế and reserves V
    # for điện thế (V = k*q/r). Remap V→U unless điện-thế context is present.
    if "V" in given and not _POTENTIAL_CONTEXT_PAT.search(question):
        v_val = given.pop("V")
        given.setdefault("U", v_val)   # keep an explicit U if one already exists

    # Reactance symbol canonicalization (VN curriculum): international X_L/X_C →
    # Z_L (cảm kháng) / Z_C (dung kháng). The RAG DB + solver use Z_L/Z_C.
    for foreign, canon in (("X_L", "Z_L"), ("X_C", "Z_C")):
        if foreign in given:
            given.setdefault(canon, given.pop(foreign))

    # Kinematics helper: map speed to initial/final velocity depending on stop/rest keywords
    if "v" in given and any(stop_word in normalized_q.lower() for stop_word in ["rest", "stop", "stops"]):
        # If the car comes to rest, the velocity given is the initial velocity 'u', and final velocity 'v' is 0
        given["u"] = given.pop("v")
        given["v"] = 0.0
    elif any(stop_word in normalized_q.lower() for stop_word in ["from rest", "start from rest", "starts from rest"]):
        # If the car starts from rest, 'u' is 0
        given["u"] = 0.0

    # Resistivity conversion helper: if rho is given in ohm*mm^2/m, scale by 1e-6 to convert to SI (ohm*m)
    if "rho" in given and any(pat in normalized_q.lower() for pat in ["ohm*mm", "ohm·mm", "ohm mm"]):
        given["rho"] = given["rho"] * 1e-6

    if return_phrasal:
        return given, phrasal_keys
    return given
