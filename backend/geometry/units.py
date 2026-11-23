"""Unit handling for DXF files.

Everything exYze stores is in metres. A DXF file says what its drawing units
are in the $INSUNITS header variable. This module turns that code into a
multiplier (drawing units -> metres) and applies the fallback rule from the
Package A spec when the header is missing or 0.

Real files often carry a wrong $INSUNITS (for example "mm" on a plan drawn in
metres, which converters tend to write). When the header's answer gives an
impossible plan size, we pick a better unit and add a review flag.
"""

from collections.abc import Sequence
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

# A converted plan narrower/wider than this (larger side, in metres) is not a
# believable building, so the header is treated as wrong.
PLAUSIBLE_MIN_M = 1.0
PLAUSIBLE_MAX_M = 500.0

# Units we try when the header gives an impossible size.
CANDIDATE_UNITS: dict[str, float] = {
    "m": 1.0,
    "ft": 0.3048,
    "mm": 0.001,
    "cm": 0.01,
    "in": 0.0254,
}

# A door swing is about this wide, in metres. Used to tell metres from feet.
DOOR_MIN_M = 0.7
DOOR_MAX_M = 1.0

UNIT_NAMES = {1: "inches", 2: "feet", 4: "millimetres", 5: "centimetres", 6: "metres"}

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


def _infer_from_plan(
    code: int | None,
    header_factor: float,
    extent: float,
    arc_radii: Sequence[float],
    measurement: int | None,
) -> UnitResolution:
    """The header gives an impossible plan size, so pick a better unit.

    Only units that give a believable size are candidates. Among them, the one
    under which the most arcs look like door swings wins, if it wins clearly
    (at least twice the runner-up). Otherwise $MEASUREMENT decides: imperial
    (0) prefers feet, anything else prefers metres.
    """
    header_name = UNIT_NAMES.get(code, f"code {code}")
    header_size = extent * header_factor
    candidates = [
        name
        for name, f in CANDIDATE_UNITS.items()
        if PLAUSIBLE_MIN_M <= extent * f <= PLAUSIBLE_MAX_M
    ]
    if not candidates:
        return UnitResolution(
            factor=header_factor,
            assumed=False,
            reason=(
                f"$INSUNITS says {header_name}, which makes the plan {header_size:.3f} m wide, "
                "and no other unit gives a believable size; check the units"
            ),
        )

    preference = (
        ["ft", "in", "m", "cm", "mm"] if measurement == 0 else list(CANDIDATE_UNITS)
    )
    candidates.sort(key=preference.index)

    def doors(name: str) -> int:
        f = CANDIDATE_UNITS[name]
        return sum(DOOR_MIN_M <= r * f <= DOOR_MAX_M for r in arc_radii)

    scores = {name: doors(name) for name in candidates}
    ranked = sorted(
        candidates, key=lambda n: -scores[n]
    )  # stable: ties keep preference order
    best = ranked[0]
    runner_up = scores[ranked[1]] if len(ranked) > 1 else 0
    if len(ranked) == 1:
        why = "it is the only unit that gives a believable size"
    elif scores[best] > 0 and scores[best] >= 2 * runner_up:
        why = f"{scores[best]} arcs match door swings in that unit"
    else:
        best = candidates[0]  # preference order decides
        why = "door swings were inconclusive, so the plan's measurement system decided"

    size = extent * CANDIDATE_UNITS[best]
    return UnitResolution(
        factor=CANDIDATE_UNITS[best],
        assumed=True,
        reason=(
            f"$INSUNITS says {header_name}, which makes the plan {header_size:.3f} m wide. "
            f"Used {best} instead ({size:.1f} m wide): {why}. Please confirm the scale"
        ),
    )


def resolve_units(
    code: int | None,
    extent: float,
    arc_radii: Sequence[float] = (),
    measurement: int | None = None,
) -> UnitResolution:
    """Decide the metres-per-unit factor for a drawing.

    code:        value of $INSUNITS (None if the header variable is missing)
    extent:      the larger side of the drawing's bounding box, in drawing units
    arc_radii:   radii of all arcs, in drawing units (door swings help pick the unit)
    measurement: value of $MEASUREMENT (0 imperial, 1 metric), if present
    """
    factor = insunits_to_metres(code)
    if factor is not None:
        size = extent * factor
        if extent == 0 or PLAUSIBLE_MIN_M <= size <= PLAUSIBLE_MAX_M:
            return UnitResolution(factor=factor, assumed=False, reason=None)
        return _infer_from_plan(code, factor, extent, arc_radii, measurement)

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