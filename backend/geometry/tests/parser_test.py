"""Unit tests for the DXF parser: one group per entity type, plus units,
model-space-only, robustness and the real test files in tests/data/."""

import json
import math
from pathlib import Path

import ezdxf
import pytest

from geometry.dxf_parser import main, parse_document, parse_dxf

DATA_DIR = Path(__file__).parent / "data"


def new_doc(insunits: int | None = 4):
    """A fresh drawing. Default units: millimetres."""
    doc = ezdxf.new("R2010")
    if insunits is None:
        del doc.header["$INSUNITS"]  # ezdxf.new() sets it to 6 by default
    else:
        doc.header["$INSUNITS"] = insunits
    return doc


# --------------------------------------------------------------------------
# The geometry format from 01 (nothing extra allowed)
# --------------------------------------------------------------------------
FORMAT_01_KEYS = {
    "version", "units", "source", "walls", "openings", "rooms",
    "labels", "items", "flags", "scale",
}  # fmt: skip


def test_geometry_has_exactly_the_keys_of_the_agreed_format():
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (1000, 0))
    g = parse_document(doc, provisional_walls=True).geometry
    assert set(g) == FORMAT_01_KEYS
    assert g["scale"] is None
    assert set(g["walls"][0]) == {
        "key", "x1", "y1", "x2", "y2", "thickness", "height", "exterior", "confidence",
    }  # fmt: skip


# --------------------------------------------------------------------------
# LINE
# --------------------------------------------------------------------------
def test_line_is_converted_from_mm_to_metres():
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (4200, 0))
    out = parse_document(doc)
    assert out.geometry["units"] == "m" and out.geometry["source"] == "dxf"
    [ln] = out.raw["lines"]
    assert (ln["x1"], ln["y1"], ln["x2"], ln["y2"]) == (0.0, 0.0, 4.2, 0.0)


def test_line_units_cm_and_feet():
    doc = new_doc(5)
    doc.modelspace().add_line((0, 0), (420, 0))
    assert parse_document(doc).raw["lines"][0]["x2"] == 4.2

    doc = new_doc(2)
    doc.modelspace().add_line((0, 0), (10, 0))
    assert parse_document(doc).raw["lines"][0]["x2"] == 3.048


def test_zero_length_line_is_dropped():
    doc = new_doc(4)
    msp = doc.modelspace()
    msp.add_line((5, 5), (5, 5))
    msp.add_line((0, 0), (1000, 0))
    assert len(parse_document(doc).raw["lines"]) == 1


def test_layer_name_is_only_a_hint():
    doc = new_doc(4)
    msp = doc.modelspace()
    doc.layers.add("A-WALL")
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 0), (0, 1000), dxfattribs={"layer": "MISC"})
    lines = {ln["layer"]: ln for ln in parse_document(doc).raw["lines"]}
    assert lines["A-WALL"]["layer_hint"] is True
    assert lines["MISC"]["layer_hint"] is False  # still kept as a line


# --------------------------------------------------------------------------
# LWPOLYLINE
# --------------------------------------------------------------------------
def test_open_lwpolyline_becomes_segments():
    doc = new_doc(4)
    doc.modelspace().add_lwpolyline([(0, 0), (1000, 0), (1000, 2000)])
    lines = parse_document(doc).raw["lines"]
    assert len(lines) == 2
    assert (lines[1]["x1"], lines[1]["y1"], lines[1]["x2"], lines[1]["y2"]) == (
        1.0,
        0.0,
        1.0,
        2.0,
    )
    assert all(ln["origin"] == "lwpolyline" for ln in lines)


def test_closed_lwpolyline_includes_closing_segment():
    doc = new_doc(4)
    doc.modelspace().add_lwpolyline(
        [(0, 0), (4000, 0), (4000, 3500), (0, 3500)], close=True
    )
    assert len(parse_document(doc).raw["lines"]) == 4


def test_lwpolyline_bulge_becomes_an_arc_not_a_wall():
    doc = new_doc(4)
    # bulge 1 = semicircle over a 1000 mm chord -> radius 500 mm
    doc.modelspace().add_lwpolyline([(0, 0, 1), (1000, 0, 0)], format="xyb")
    out = parse_document(doc)
    assert out.raw["lines"] == []
    [arc] = out.raw["arcs"]
    assert arc["radius"] == pytest.approx(0.5)


# --------------------------------------------------------------------------
# ARC
# --------------------------------------------------------------------------
def test_arc_keeps_centre_radius_and_angles():
    doc = new_doc(4)
    doc.modelspace().add_arc((1000, 2000), 900, 0, 90)
    out = parse_document(doc)
    assert out.raw["lines"] == []  # arcs are door swings, not walls
    [arc] = out.raw["arcs"]
    assert (arc["cx"], arc["cy"], arc["radius"]) == (1.0, 2.0, 0.9)
    assert (arc["start_angle"], arc["end_angle"]) == (0.0, 90.0)


def test_arc_angles_are_normalised_below_360():
    doc = new_doc(4)
    doc.modelspace().add_arc((0, 0), 500, 270, 360)
    [arc] = parse_document(doc).raw["arcs"]
    assert arc["start_angle"] == 270.0
    assert arc["end_angle"] == 0.0


# --------------------------------------------------------------------------
# INSERT
# --------------------------------------------------------------------------
def make_door_block(doc):
    blk = doc.blocks.new("DOOR")
    blk.add_line((0, 0), (1000, 0))
    blk.add_arc((0, 0), 1000, 0, 90)


def test_insert_is_recorded_with_name_position_rotation_and_scale():
    doc = new_doc(4)
    make_door_block(doc)
    doc.modelspace().add_blockref(
        "DOOR", (3000, 1500), dxfattribs={"rotation": 90, "xscale": 2, "yscale": 1}
    )
    [ins] = parse_document(doc).raw["inserts"]
    assert ins["block"] == "DOOR"
    assert (ins["x"], ins["y"]) == (3.0, 1.5)
    assert ins["rotation"] == 90.0
    assert (ins["xscale"], ins["yscale"]) == (2.0, 1.0)


def test_insert_is_exploded_into_world_coordinates():
    doc = new_doc(4)
    make_door_block(doc)
    doc.modelspace().add_blockref("DOOR", (1000, 2000), dxfattribs={"rotation": 90})
    out = parse_document(doc)
    [ln] = out.raw["lines"]
    # block line (0,0)-(1000,0), rotated 90 degrees about (1000,2000)
    assert (ln["x1"], ln["y1"]) == (1.0, 2.0)
    assert ln["x2"] == pytest.approx(1.0) and ln["y2"] == pytest.approx(3.0)
    assert ln["origin"] == "block:DOOR"
    [arc] = out.raw["arcs"]  # the swing arc is also kept, rotated 90 degrees
    assert arc["start_angle"] == pytest.approx(90.0)
    assert arc["end_angle"] == pytest.approx(180.0)


def test_insert_with_negative_scale_mirrors_the_lines():
    doc = new_doc(4)
    make_door_block(doc)
    doc.modelspace().add_blockref("DOOR", (0, 0), dxfattribs={"xscale": -1})
    [ln] = parse_document(doc).raw["lines"]
    assert ln["x2"] == pytest.approx(-1.0)
    [arc] = parse_document(doc).raw["arcs"]
    assert (arc["start_angle"], arc["end_angle"]) == (
        90.0,
        180.0,
    )  # mirrored quarter circle


def test_nested_blocks_are_exploded():
    doc = new_doc(4)
    make_door_block(doc)
    outer = doc.blocks.new("ROOM_UNIT")
    outer.add_blockref("DOOR", (500, 0))
    doc.modelspace().add_blockref("ROOM_UNIT", (0, 0))
    out = parse_document(doc)
    assert len(out.raw["lines"]) == 1
    assert out.raw["lines"][0]["x1"] == 0.5
    inserts = out.raw["inserts"]
    assert [(i["block"], i["nested"]) for i in inserts] == [
        ("ROOM_UNIT", False),
        ("DOOR", True),
    ]
    assert inserts[1]["x"] == 0.5  # nested position is in world coordinates


def test_block_on_layer_zero_inherits_the_insert_layer():
    doc = new_doc(4)
    make_door_block(doc)
    doc.layers.add("A-DOOR")
    doc.modelspace().add_blockref("DOOR", (0, 0), dxfattribs={"layer": "A-DOOR"})
    assert parse_document(doc).raw["lines"][0]["layer"] == "A-DOOR"


def test_self_referencing_block_does_not_loop_forever():
    doc = new_doc(4)
    blk = doc.blocks.new("LOOP")
    blk.add_line((0, 0), (1000, 0))
    blk.add_blockref("LOOP", (0, 0))
    doc.modelspace().add_blockref("LOOP", (0, 0))
    out = parse_document(doc)
    assert any("nested deeper" in s["reason"] for s in out.raw["skipped"])


# --------------------------------------------------------------------------
# TEXT and MTEXT
# --------------------------------------------------------------------------
def test_text_becomes_a_label():
    doc = new_doc(4)
    doc.modelspace().add_text(
        "BEDROOM 1", dxfattribs={"insert": (2100, 1700), "height": 200}
    )
    assert parse_document(doc).geometry["labels"] == [
        {"text": "BEDROOM 1", "x": 2.1, "y": 1.7}
    ]


def test_empty_text_is_ignored():
    doc = new_doc(4)
    doc.modelspace().add_text("   ", dxfattribs={"insert": (0, 0)})
    assert parse_document(doc).geometry["labels"] == []


def test_mtext_formatting_codes_are_stripped():
    doc = new_doc(4)
    doc.modelspace().add_mtext(
        "{\\fArial|b0;LIVING}\\PROOM", dxfattribs={"insert": (4000, 3000)}
    )
    [label] = parse_document(doc).geometry["labels"]
    assert label["text"] == "LIVING ROOM"
    assert (label["x"], label["y"]) == (4.0, 3.0)


# --------------------------------------------------------------------------
# Units fallback, model space only, robustness
# --------------------------------------------------------------------------
def test_missing_insunits_wide_drawing_assumed_mm_with_flag():
    doc = new_doc(None)
    doc.modelspace().add_line((0, 0), (12000, 0))
    out = parse_document(doc)
    assert out.raw["lines"][0]["x2"] == 12.0
    assert out.raw["units_assumed"] is True
    [flag] = out.geometry["flags"]
    assert flag["element_kind"] == "scale"
    assert "millimetres" in flag["reason"]


def test_insunits_zero_small_drawing_assumed_metres_with_flag():
    doc = new_doc(0)
    doc.modelspace().add_line((0, 0), (12, 0))
    out = parse_document(doc)
    assert out.raw["lines"][0]["x2"] == 12.0
    assert len(out.geometry["flags"]) == 1


def test_explicit_units_give_no_flag():
    doc = new_doc(6)
    doc.modelspace().add_line((0, 0), (12, 0))
    assert parse_document(doc).geometry["flags"] == []


def test_paper_space_is_ignored():
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (1000, 0))
    doc.layout("Layout1").add_line((0, 0), (0, 5000))
    assert len(parse_document(doc).raw["lines"]) == 1


def test_empty_drawing_does_not_crash():
    out = parse_document(new_doc(4))
    assert out.raw["lines"] == [] and out.geometry["labels"] == []


def test_output_is_json_serialisable_and_rounded_to_3_decimals():
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (1234.56789, 0))
    out = parse_document(doc)
    json.dumps(out.geometry)
    json.dumps(out.raw)
    assert out.raw["lines"][0]["x2"] == 1.235


# --------------------------------------------------------------------------
# Provisional walls (placeholder until wall pairing exists)
# --------------------------------------------------------------------------
def test_provisional_walls_use_spec_defaults():
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (4200, 0))
    [w] = parse_document(doc, provisional_walls=True).geometry["walls"]
    assert w["key"] == "w1"
    assert (w["x1"], w["x2"]) == (0.0, 4.2)
    assert w["thickness"] == 0.125 and w["confidence"] == 0.5


def test_provisional_walls_skip_block_lines_and_prefer_wall_layers():
    doc = new_doc(4)
    make_door_block(doc)
    doc.layers.add("A-WALL")
    msp = doc.modelspace()
    msp.add_line((0, 0), (4000, 0), dxfattribs={"layer": "A-WALL"})
    msp.add_line((0, 100), (4000, 100), dxfattribs={"layer": "DIMS"})
    msp.add_blockref("DOOR", (500, 0))
    walls = parse_document(doc, provisional_walls=True).geometry["walls"]
    assert len(walls) == 1 and walls[0]["y1"] == 0.0


# --------------------------------------------------------------------------
# Command line and files
# --------------------------------------------------------------------------
def test_command_line_writes_json(tmp_path, capsys):
    doc = new_doc(4)
    doc.modelspace().add_line((0, 0), (1000, 0))
    path = tmp_path / "plan.dxf"
    doc.saveas(path)
    assert main([str(path), "--walls"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["walls"]) == 1
    assert "raw" not in data


def test_parse_dxf_reads_a_saved_file(tmp_path):
    doc = new_doc(5)
    doc.modelspace().add_line((0, 0), (420, 0))
    path = tmp_path / "plan.dxf"
    doc.saveas(path)
    assert parse_dxf(path).raw["lines"][0]["x2"] == 4.2


DXF_FILES = sorted(DATA_DIR.glob("*.dxf"))


@pytest.mark.skipif(not DXF_FILES, reason="no DXF files in tests/data yet")
@pytest.mark.parametrize("path", DXF_FILES, ids=lambda p: p.name)
def test_real_plan_parses_without_crashing(path):
    out = parse_dxf(path, provisional_walls=True)
    json.dumps(out.geometry)  # must be serialisable
    assert out.geometry["units"] == "m"
    raw = out.raw
    coords = [
        v for ln in raw["lines"] for v in (ln["x1"], ln["y1"], ln["x2"], ln["y2"])
    ]
    assert all(math.isfinite(v) for v in coords)
    for ln in raw["lines"]:
        assert (ln["x1"], ln["y1"]) != (ln["x2"], ln["y2"])