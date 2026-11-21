import json
from unittest.mock import Mock, PropertyMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import Principal, request_db, require_principal
from app.dev import FIXTURE_PATH, app as dev_app
from app.main import create_app


@pytest.fixture
def authenticated():
    app = create_app()
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=17, role="architect")
    db = Mock()
    app.dependency_overrides[request_db] = lambda: db
    with TestClient(app) as client:
        yield client, db


@pytest.mark.parametrize("path", ["/api/projects", "/api/floors/1", "/api/revisions/1"])
def test_normal_routes_require_verified_identity(path):
    with TestClient(create_app()) as client:
        response = client.get(path, headers={"X-User-Id": "1", "X-Role": "admin"})
    assert response.status_code == 401
    assert response.json() == {"error": "AUTH_REQUIRED", "message": "Sign-in required."}


def test_client_role_has_no_core_table_reads():
    app = create_app()
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=17, role="client")
    with TestClient(app) as client:
        for path in ("/api/projects", "/api/floors/1", "/api/revisions/1"):
            assert client.get(path).status_code == 403


def test_project_list_and_floor_detail(authenticated):
    client, db = authenticated
    db.execute.return_value.fetchall.return_value = [{"id": 3, "name": "Home", "site_address": None}]
    assert client.get("/api/projects").json() == [{"id": 3, "name": "Home", "siteAddress": None}]

    db.execute.return_value.fetchone.return_value = {"id": 4, "level_no": 0, "name": "Ground"}
    assert client.get("/api/floors/4").json() == {"id": 4, "levelNo": 0, "name": "Ground"}
    assert db.execute.call_args.args[-1] == (4,)


@pytest.mark.parametrize("table", ["floors", "revisions"])
def test_missing_or_inaccessible_resource(authenticated, table):
    client, db = authenticated
    db.execute.return_value.fetchone.return_value = None
    assert client.get(f"/api/{table}/1").status_code == 404
    assert client.get(f"/api/{table}/0").json()["error"] == "INVALID_REQUEST"
    assert client.get(f"/api/{table}/9223372036854775808").status_code == 422


def test_persisted_revision_waits_for_geometry_read(authenticated):
    client, db = authenticated
    db.execute.return_value.fetchone.return_value = {"revision_id": 1}
    response = client.get("/api/revisions/1")
    assert response.status_code == 503
    assert response.json()["error"] == "GEOMETRY_UNAVAILABLE"


def test_development_revision_uses_only_the_labeled_fixture():
    with TestClient(dev_app) as client:
        response = client.get("/api/revisions/1")
        assert response.status_code == 200
        assert response.headers["X-Exyze-Geometry"] == "dev-fixture"
        assert response.json() == json.loads(FIXTURE_PATH.read_text())
        assert client.get("/api/revisions/2").status_code == 404
        assert client.get("/api/projects").status_code == 404


@pytest.mark.parametrize(("state", "status", "name"), [
    ("EXY01", 422, "OPENING_DOES_NOT_FIT"), ("EXY02", 422, "ITEM_OUTSIDE_ROOM"),
    ("EXY03", 422, "WALL_ROOM_LIMIT"), ("EXY04", 409, "REVISION_LOCKED"),
    ("EXY05", 422, "SCALE_UNDETERMINED"), ("EXY06", 409, "OPEN_REVIEW_FLAGS"),
    ("EXY07", 409, "SCALE_NOT_CONFIRMED"), ("EXY08", 409, "UPLOAD_NOT_READY"),
    ("EXY09", 422, "INVALID_EDIT"), ("EXY10", 404, "SHARE_LINK_INVALID"),
])
def test_canonical_sqlstate_errors(authenticated, monkeypatch, state, status, name):
    client, db = authenticated
    error = type("TestRuleError", (psycopg.DatabaseError,), {"sqlstate": state})("example")
    monkeypatch.setattr(type(error), "diag", PropertyMock(return_value=Mock(message_primary="Rule failed.")))
    db.execute.side_effect = error
    response = client.get("/api/projects")
    assert response.status_code == status
    assert response.json() == {"error": name, "message": "Rule failed."}


def test_unknown_database_error_is_logged_and_sanitized(authenticated, caplog):
    client, db = authenticated
    db.execute.side_effect = psycopg.errors.UndefinedTable("private_table")
    response = client.get("/api/projects")
    assert response.status_code == 500
    assert response.json() == {"error": "INTERNAL_ERROR", "message": "An internal error occurred."}
    assert "private_table" in caplog.text
