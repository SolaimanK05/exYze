import pytest

from geometry.units import insunits_to_metres, resolve_units


@pytest.mark.parametrize(
    "code, expected",
    [(1, 0.0254), (2, 0.3048), (4, 0.001), (5, 0.01), (6, 1.0)],
)
def test_known_codes(code, expected):
    assert insunits_to_metres(code) == pytest.approx(expected)


@pytest.mark.parametrize("code", [None, 0, 999])
def test_unknown_codes_return_none(code):
    assert insunits_to_metres(code) is None


def test_explicit_units_are_not_assumed():
    r = resolve_units(4, extent=12000)
    assert r.factor == 0.001
    assert r.assumed is False
    assert r.reason is None


def test_missing_units_wide_drawing_assumes_millimetres():
    r = resolve_units(None, extent=12000)
    assert r.factor == 0.001
    assert r.assumed is True
    assert "millimetres" in r.reason


def test_zero_units_narrow_drawing_assumes_metres():
    r = resolve_units(0, extent=12.5)
    assert r.factor == 1.0
    assert r.assumed is True
    assert "metres" in r.reason


def test_threshold_is_wider_than_1000_units():
    assert resolve_units(0, extent=1000).factor == 1.0
    assert resolve_units(0, extent=1000.1).factor == 0.001


# --------------------------------------------------------------------------
# Wrong headers: the plan size decides
# --------------------------------------------------------------------------
METRE_DOORS = [0.9] * 6  # door swings drawn in metres
FOOT_DOORS = [3.0] * 6  # door swings drawn in feet


def test_believable_size_keeps_the_header_even_if_arcs_disagree():
    r = resolve_units(4, extent=12000, arc_radii=FOOT_DOORS)
    assert (r.factor, r.assumed, r.reason) == (0.001, False, None)


def test_empty_drawing_keeps_the_header():
    assert resolve_units(4, extent=0).reason is None


def test_mm_header_on_plan_drawn_in_metres_is_corrected():
    r = resolve_units(4, extent=28, arc_radii=METRE_DOORS)  # would be 0.028 m wide
    assert r.factor == 1.0
    assert r.assumed is True
    assert "millimetres" in r.reason and "metres" in r.reason


def test_mm_header_on_plan_drawn_in_feet_is_corrected():
    r = resolve_units(4, extent=28, arc_radii=FOOT_DOORS)
    assert r.factor == 0.3048
    assert r.assumed is True


def test_inch_header_on_a_small_raw_plan_is_corrected():
    r = resolve_units(1, extent=19, arc_radii=METRE_DOORS)  # 0.48 m wide as inches
    assert r.factor == 1.0


def test_metre_header_on_plan_drawn_in_mm_is_corrected():
    r = resolve_units(6, extent=12000, arc_radii=[900] * 5)  # 12000 m wide as metres
    assert r.factor == 0.001


def test_inconclusive_doors_prefer_metres_for_metric_drawings():
    mixed = [0.9] * 5 + [3.0] * 4  # no clear winner
    assert resolve_units(4, extent=28, arc_radii=mixed, measurement=1).factor == 1.0


def test_inconclusive_doors_prefer_feet_for_imperial_drawings():
    mixed = [0.9] * 5 + [3.0] * 4
    assert resolve_units(4, extent=28, arc_radii=mixed, measurement=0).factor == 0.3048


def test_no_arcs_at_all_falls_back_to_measurement_preference():
    assert resolve_units(4, extent=28, measurement=1).factor == 1.0
    assert resolve_units(4, extent=28, measurement=0).factor == 0.3048


def test_nothing_believable_keeps_header_but_explains():
    r = resolve_units(4, extent=0.0001, arc_radii=[])
    assert r.factor == 0.001 and r.assumed is False
    assert "check the units" in r.reason