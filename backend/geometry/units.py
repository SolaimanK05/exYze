"""Unit handling for DXF files.

Everything exYze stores is in metres. A DXF file says what its drawing units
are in the $INSUNITS header variable. This module turns that code into a
multiplier (drawing units -> metres) and applies the fallback rule from the
Package A spec when the header is missing or 0.
"""

from dataclasses import dataclass

# $INSUNITS code -> metres per drawing unit
INSUNITS_TO_METRES: dict[int, float] = {
    1: 0.0254,  # inches
    2: 0.3048,  # feet
    3: 1609.344,  # miles
    4: 0.001,  # millimetres
    5: 0.01,  # centimetres
    6: 1.0,  # metres
    7: 1000.0,  # kilometres
    8: 0.0254e-6,  # microinches
    9: 0.0254e-3,  # mils
    10: 0.9144,  # yards
    13: 1e-6,  # microns
    14: 0.1,  # decimetres
    15: 10.0,  # decametres
    16: 100.0,  # hectometres
}

# Spec: if $INSUNITS is missing or 0, assume millimetres when the drawing is
# wider than this many units, metres otherwise.
ASSUME_MM_ABOVE = 1000.0


@dataclass(frozen=True)
class UnitResolution:
    factor: float  # multiply drawing units by this to get metres
    assumed: bool  # True when we guessed instead of reading $INSUNITS
    reason: str | None  # human-readable text for the review flag


def insunits_to_metres(code: int | None) -> float | None:
    """Metres per drawing unit for an $INSUNITS code, or None if the code is
    0 (unitless), missing or not one we support."""
    if code is None:
        return None
    return INSUNITS_TO_METRES.get(int(code))


def resolve_units(code: int | None, extent: float) -> UnitResolution:
    """Decide the metres-per-unit factor for a drawing.

    code:   value of $INSUNITS (None if the header variable is missing)
    extent: the larger side of the drawing's bounding box, in drawing units
    """
    factor = insunits_to_metres(code)
    if factor is not None:
        return UnitResolution(factor=factor, assumed=False, reason=None)

    if extent > ASSUME_MM_ABOVE:
        return UnitResolution(
            factor=0.001,
            assumed=True,
            reason=(
                f"$INSUNITS missing or unsupported (value {code}); "
                f"assumed millimetres because the drawing is {extent:.0f} units wide"
            ),
        )
    return UnitResolution(
        factor=1.0,
        assumed=True,
        reason=(
            f"$INSUNITS missing or unsupported (value {code}); "
            f"assumed metres because the drawing is {extent:.1f} units wide"
        ),
    )