import json

import pytest
from pydantic import ValidationError

from app.dev import FIXTURE_PATH
from app.geometry import GeometryV1


@pytest.fixture
def document():
    return json.loads(FIXTURE_PATH.read_text())


def test_fixture_round_trips(document):
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
    (("walls", 1, "key"), "w1"),
    (("openings", 0, "wall"), "unknown"),
    (("openings", 0, "no"), 0),
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
