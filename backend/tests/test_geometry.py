import json
from math import hypot
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.dev import FIXTURE_PATH
from app.geometry import GeometryV1
from geometry.dxf_parser import parse_dxf


@pytest.fixture
def document():
    return json.loads(FIXTURE_PATH.read_text())


def test_fixture_round_trips(document):
    assert GeometryV1.model_validate(document).model_dump(exclude_unset=True) == document


def test_package_a_parser_output_matches_the_geometry_contract():
    sample = Path(__file__).parents[1] / "geometry" / "tests" / "data" / "plan01.dxf"
    document = parse_dxf(sample, provisional_walls=True).geometry
    validated = GeometryV1.model_validate(document)
    assert validated.walls
    assert validated.model_dump(exclude_unset=True) == document


def test_fixture_opening_fits_its_wall_and_has_a_review_flag(document):
    opening, = document["openings"]
    wall = next(wall for wall in document["walls"] if opening["wall"] == wall["key"])
    wall_length = hypot(wall["x2"] - wall["x1"], wall["y2"] - wall["y1"])
    assert opening["offset"] + opening["width"] <= wall_length
    assert opening["sill"] + opening["height"] <= wall["height"]
    assert opening["confidence"] < 0.6
    assert any(
        flag["element_kind"] == "opening" and flag["element_ref"] == f"{wall['key']}/{opening['no']}"
        for flag in document["flags"]
    )


def test_key_and_id_references_round_trip(document):
    document["openings"][0]["wall"] = document["walls"][0]["id"]
    document["items"][0]["room"] = document["rooms"][0]["id"]
    assert GeometryV1.model_validate(document).model_dump(exclude_unset=True) == document


def test_photo_import_can_omit_ids_and_rooms(document):
    document.update(
        source="photo",
        rooms=[],
        scale={"m_per_px": 0.01, "method": "ocr", "confirmed": False},
    )
    for element in document["walls"] + document["items"]:
        element.pop("id")
    document["items"][0].pop("room")
    assert GeometryV1.model_validate(document).model_dump(exclude_unset=True) == document


@pytest.mark.parametrize(("path", "value"), [
    (("version",), 2),
    (("version",), True),
    (("version",), 1.0),
    (("units",), "px"),
    (("source",), "photo"),
    (("scale",), {"m_per_px": 0.01, "method": "ocr", "confirmed": False}),
    (("walls", 0, "confidence"), 1.01),
    (("walls", 0, "x1"), float("inf")),
    (("walls", 0, "thickness"), 0),
    (("walls", 1, "key"), "w1"),
    (("rooms", 0, "key"), "w1"),
    (("openings", 0, "wall"), "unknown"),
    (("openings", 0, "no"), 0),
    (("openings", 0, "offset"), -0.1),
    (("rooms", 0, "polygon", 0), [0, 0, 0]),
    (("rooms", 0, "walls", 0, "wall"), 999),
    (("items", 0, "room"), "unknown"),
    (("items", 0, "rotation"), 360),
])
def test_rejects_noncanonical_geometry(document, path, value):
    node = document
    for segment in path[:-1]:
        node = node[segment]
    node[path[-1]] = value
    with pytest.raises(ValidationError):
        GeometryV1.model_validate(document)


def test_rejects_repeated_opening_number_across_key_and_id(document):
    document["openings"].append({**document["openings"][0], "wall": 101})
    with pytest.raises(ValidationError, match="Opening numbers"):
        GeometryV1.model_validate(document)
