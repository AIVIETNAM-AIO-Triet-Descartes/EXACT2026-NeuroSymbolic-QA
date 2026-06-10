"""
pipeline/type2/units.py

ASCII-unit conversion for the official `/predict` response.

Submission Guide §4: the response `unit` field MUST be ASCII — "ohm" not "Ω",
"uF" not "μF", "V/m" for E-field, etc. Internally the solvers emit display units
with Unicode glyphs (Ω, μ) because that reads better in CoT/explanation steps.
This module is the single conversion point: the API response builder calls
`ascii_unit()` on `SolverResult["unit"]` right before emitting the response.

Owned by Track 2 (the solvers decide what glyphs they emit, so the ASCII map
lives next to them). The API layer just imports and calls — no duplicated map.

Inventory of every unit string the solvers currently emit (2026-06-09):
    sympy_solver._UNIT_MAP : V A Ω W J F C N Hz H T
    vector_solver          : N  N/C  degree
    circuit_solver         : Ω A W   (+ "; "-joined multi e.g. "A; A")
    error_solver           : %  Ω  W  + ORIGINAL question unit (μF/μV/Ω/cm/g/...)
                             + "; "-joined multi (e.g. "cm; %", "Ω; %")
    resonance_solver       : "" (Yes/No)
Only Ω and the μ-prefix are non-ASCII; everything else passes through unchanged.
"""

# Character-level substitutions applied to each unit token.
#   Ω           U+03A9 ohm sign
#   μ / µ       U+03BC greek mu  /  U+00B5 micro sign  (both → "u")
#   °           U+00B0 degree sign
_CHAR_MAP = {
    "Ω": "ohm",   # Ω
    "μ": "u",     # μ (greek small letter mu)
    "µ": "u",     # µ (micro sign)
    "°": "degree",
}


def ascii_unit(unit: str | None) -> str:
    """
    Convert a solver display unit to the ASCII form required by the response.

    Handles "; "-joined multi-answer units ("cm; %", "A; A") token-by-token so a
    multi result stays aligned with its multi answer. Empty / None → "".

    Examples:
        "Ω"        -> "ohm"
        "kΩ"       -> "kohm"
        "μF"       -> "uF"
        "A; A"     -> "A; A"
        "Ω; %"     -> "ohm; %"
        ""         -> ""
    """
    if not unit:
        return ""
    out = []
    for part in unit.split(";"):
        token = part.strip()
        for src, dst in _CHAR_MAP.items():
            token = token.replace(src, dst)
        out.append(token)
    return "; ".join(out)
