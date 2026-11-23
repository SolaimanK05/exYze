from io import BytesIO, StringIO
from pathlib import Path

import ezdxf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import dev
from app.api import convert
from app.db import Principal, require_principal
from app.geometry import GeometryV1
from app.main import create_app


@pytest.fixture
def client():
    with TestClient(dev.app, raise_server_exceptions=False) as test_client:
        yield test_client


def drawing(*, wall: bool = True) -> bytes:
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4  # millimetres
    layout = doc.modelspace()
    if wall:
        layout.add_line((-2000, -500), (2200, -500))
    layout.add_text("ROOM", dxfattribs={"insert": (100, 1000)})
    output = StringIO()
    doc.write(output)
    return output.getvalue().encode()


def photo(image_format: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (20, 10), "white").save(output, image_format)
    return output.getvalue()


def test_dxf_returns_v1_in_metres_with_plan_origin(client):
    result = client.post("/api/convert", files={"file": ("plan.DXF", drawing())})
    assert result.status_code == 200
    assert result.headers["Cache-Control"] == "no-store"
    geometry = GeometryV1.model_validate(result.json())
    assert (geometry.version, geometry.source, geometry.units, geometry.scale) == (1, "dxf", "m", None)
    wall, = geometry.walls
    assert (wall.x1, wall.y1, wall.x2, wall.y2) == (0, 0, 4.2, 0)
    assert "id" not in result.json()["walls"][0]
    label, = geometry.labels
    assert (label.text, label.x, label.y) == ("ROOM", 2.1, 1.5)


def test_dxf_converts_real_package_a_sample(client):
    sample = Path(__file__).parents[1] / "geometry" / "tests" / "data" / "plan01.dxf"
    result = client.post("/api/convert", files={"file": (sample.name, sample.read_bytes())})
    assert result.status_code == 200
    geometry = GeometryV1.model_validate(result.json())
    assert geometry.walls
    assert geometry.labels


@pytest.mark.parametrize(("name", "contents", "status", "code"), [
    ("plan.dxf", b"not a dxf", 422, "INVALID_DXF"),
    ("plan.dxf", b"", 422, "EMPTY_UPLOAD"),
    ("plan.pdf", b"%PDF-1.7", 415, "UNSUPPORTED_FILE_TYPE"),
    ("plan.jpg", b"not a jpg", 422, "INVALID_PHOTO"),
    ("plan.png", b"not a png", 422, "INVALID_PHOTO"),
])
def test_rejects_invalid_files(client, name, contents, status, code):
    result = client.post("/api/convert", files={"file": (name, contents)})
    assert result.status_code == status
    assert result.json()["error"] == code


def test_dxf_without_supported_wall_lines_is_rejected(client):
    result = client.post("/api/convert", files={"file": ("labels.dxf", drawing(wall=False))})
    assert result.status_code == 422
    assert result.json()["error"] == "NO_PLAN_GEOMETRY"


@pytest.mark.parametrize(("suffix", "image_format"), [("jpg", "JPEG"), ("PNG", "PNG")])
def test_valid_photo_reports_pending_processor(client, suffix, image_format):
    result = client.post("/api/convert", files={"file": (f"plan.{suffix}", photo(image_format))})
    assert result.status_code == 503
    assert result.json()["error"] == "PHOTO_CONVERSION_UNAVAILABLE"


def test_image_content_must_match_the_suffix(client):
    result = client.post("/api/convert", files={"file": ("plan.jpg", photo("PNG"))})
    assert result.status_code == 422
    assert result.json()["error"] == "INVALID_PHOTO"


def test_photo_dimensions_are_bounded(client, monkeypatch):
    monkeypatch.setattr(convert, "MAX_PHOTO_PIXELS", 100)
    result = client.post("/api/convert", files={"file": ("plan.png", photo("PNG"))})
    assert result.status_code == 413
    assert result.json()["error"] == "PHOTO_TOO_LARGE"


def test_wrong_form_and_missing_boundary(client):
    result = client.post("/api/convert", json={"file": "plan.dxf"})
    assert result.status_code == 415
    assert result.json()["error"] == "INVALID_UPLOAD_TYPE"

    result = client.post("/api/convert", headers={"Content-Type": "multipart/form-data"})
    assert result.status_code == 400
    assert result.json()["error"] == "INVALID_UPLOAD"


@pytest.mark.parametrize("fields", [
    [("drawing", ("one.dxf", b"one"))],
    [("file", ("one.dxf", b"one")), ("file", ("two.dxf", b"two"))],
])
def test_requires_one_file_with_the_expected_field_name(client, fields):
    result = client.post("/api/convert", files=fields)
    assert result.status_code == 400
    assert result.json()["error"] == "INVALID_UPLOAD"


def test_file_size_is_bounded(client, monkeypatch):
    monkeypatch.setattr(convert, "MAX_FILE_BYTES", 4)
    result = client.post("/api/convert", files={"file": ("plan.dxf", b"12345")})
    assert result.status_code == 413
    assert result.json()["error"] == "UPLOAD_TOO_LARGE"


def test_multipart_body_is_bounded_without_content_length(client, monkeypatch):
    monkeypatch.setattr(convert, "MAX_BODY_BYTES", 12)
    result = client.post(
        "/api/convert",
        content=iter([b"--plan\r\n", b"Content-Disposition: form-data; name=file\r\n"]),
        headers={"Content-Type": "multipart/form-data; boundary=plan"},
    )
    assert result.status_code == 413
    assert result.json()["error"] == "UPLOAD_TOO_LARGE"


def test_unexpected_processor_error_is_sanitized_and_temp_file_removed(client, monkeypatch):
    attempted = []

    def fail(path, *, provisional_walls):
        assert provisional_walls
        assert path.name == "plan.dxf" and path.is_file()
        attempted.append(path)
        raise RuntimeError("private processor diagnostic")

    monkeypatch.setattr(convert, "parse_dxf", fail)
    result = client.post("/api/convert", files={"file": ("../../nested.dxf", b"contents")})
    assert result.status_code == 500
    assert result.json() == {"error": "INTERNAL_ERROR", "message": "An internal error occurred."}
    path, = attempted
    assert not path.parent.exists()


def test_main_conversion_requires_auth_and_can_run_without_database():
    app = create_app()
    actor = Principal(user_id=1, role="architect")
    with TestClient(app) as main_client:
        result = main_client.post("/api/convert", json={"file": "plan.dxf"})
        assert result.status_code == 401
        assert result.json()["error"] == "AUTH_REQUIRED"

        app.dependency_overrides[require_principal] = lambda: actor
        result = main_client.post("/api/convert", files={"file": ("plan.dxf", drawing())})
        assert result.status_code == 200
        assert main_client.get("/api/revisions/1").json()["error"] == "DATABASE_UNAVAILABLE"
