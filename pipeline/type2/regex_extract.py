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
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'   # unit prefix+base (optional)
)

# Bare power notation: SYM = MANTISSA^EXP UNIT  e.g. "q1 = 10^-8 C"
_BARE_POWER_PAT = re.compile(
    r'\b([A-Za-z_]\w*)\s*=\s*'
    r'([+-]?[\d.]+)\^([+-]?\d+)'            # mantissa^exp (pure power, no ×10)
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'
)

# "X cm apart" / "separated by X cm" → AB distance
_APART_PAT = re.compile(
    r'([\d.]+)\s*(cm|m)\s+apart|'
    r'separated\s+by\s+([\d.]+)\s*(cm|m)',
    re.IGNORECASE,
)

# "side length X cm" / "side of X cm" → a distance
_SIDE_PAT = re.compile(
    r'side\s+(?:length\s+|of\s+)?([\d.]+)\s*(cm|m)\b', re.IGNORECASE
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
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?',
)

# Verb-context target detector: "calculate the energy" → "E"
# NOTE: dict order matters — detect_find_from_verb returns the FIRST kw substring
# match. "potential energy" and "electric potential" must precede the looser
# "potential"/"energy" cues so U (hiệu điện thế) vs V (điện thế) vs W (thế năng)
# disambiguate correctly. U = hiệu điện thế, V = điện thế.
_VERB_TARGET_MAP = {
    "potential energy": "W", "electric potential": "V", "potential difference": "U",
    "voltage": "U", "energy": "E", "resistance": "R",
    "current": "I", "power": "P", "charge": "Q", "capacitance": "C",
    "force": "F", "frequency": "f", "inductance": "L",
    "electric field": "E_field", "field strength": "E_field",
    # reactance: VN convention Z_L (cảm kháng) / Z_C (dung kháng) / Z (tổng trở).
    # Specific kinds MUST precede the generic "reactance" (substring match order).
    "impedance": "Z", "inductive reactance": "Z_L", "capacitive reactance": "Z_C",
    "reactance": "Z_L", "power factor": "cos_phi",
}
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
    r'\s*([μuμnmkMGp]?[A-Z\xd6a-z]{1,4})?'
)

# Unicode superscript digits/minus → ASCII helper
_SUP_TABLE = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺', '0123456789-+')


def _normalize_superscripts(text: str) -> str:
    return text.translate(_SUP_TABLE)


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


def extract_given(question: str) -> dict[str, float]:
    """
    Extract {symbol: SI_value} from question text via regex.
    Handles: C = 100 μF, q1 = 6 × 10^-8 C, chained and negated-chain assignments,
    bare-power notation, and a few geometry distances (AB, side a, perpendicular).
    """
    given: dict[str, float] = {}
    # Normalize Unicode superscript chars (⁻⁸ → -8) before regex matching
    question = _normalize_superscripts(question)

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

    return given
