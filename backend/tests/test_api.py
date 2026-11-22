import json
from unittest.mock import DEFAULT, Mock, PropertyMock

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg_pool import PoolClosed, PoolTimeout
from pydantic import ValidationError

from app import dev
from app.db import Principal, request_db, require_principal
from app.dev import FIXTURE_PATH, app as dev_app
from app.main import create_app


@pytest.fixture
def authenticated():
    app = create_app()
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=17, role="architect")
    db = Mock()
    rls_cursor = Mock()
    rls_cursor.fetchone.return_value = {"active": True}
    db.execute.side_effect = lambda query, *_: rls_cursor if "row_security_active" in query else DEFAULT
    app.dependency_overrides[request_db] = lambda: db
    with TestClient(app) as client:
        yield client, db


@pytest.mark.parametrize("path", ["/api/projects", "/api/floors/1", "/api/revisions/1"])
def test_normal_routes_require_verified_identity(path):
    with TestClient(create_app()) as client:
        response = client.get(
            path, headers={"X-User-Id": "1", "X-Role": "admin", "Authorization": "Bearer dev"}
        )
    assert response.status_code == 401
    assert response.json() == {"error": "AUTH_REQUIRED", "message": "Sign-in required."}
    assert response.headers["Cache-Control"] == "no-store"


def test_client_role_has_no_core_table_reads():
    app = create_app()
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=17, role="client")
    with TestClient(app) as client:
        for path in ("/api/projects", "/api/floors/1", "/api/revisions/1"):
            assert client.get(path).status_code == 403


def test_project_list_and_floor_detail(authenticated):
    client, db = authenticated
    db.execute.return_value.fetchall.return_value = [{"id": 3, "name": "Home", "site_address": None}]
    projects = client.get("/api/projects")
    assert projects.json() == [{"id": 3, "name": "Home", "siteAddress": None}]
    assert projects.headers["Cache-Control"] == "no-store"

    db.execute.return_value.fetchone.return_value = {"id": 4, "level_no": 0, "name": "Ground"}
    floor = client.get("/api/floors/4")
    assert floor.json() == {"id": 4, "levelNo": 0, "name": "Ground"}
    assert floor.headers["Cache-Control"] == "no-store"
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
    assert "X-Exyze-Geometry" not in response.headers


@pytest.mark.parametrize(("path", "tables"), [
    ("/api/projects", ["project"]),
    ("/api/floors/1", ["project", "floor"]),
    ("/api/revisions/1", ["project", "floor", "revision"]),
])
def test_missing_or_inactive_rls_prevents_core_reads(authenticated, path, tables):
    client, db = authenticated
    db.execute.side_effect = None
    db.execute.return_value.fetchone.return_value = {"active": False}
    response = client.get(path)
    assert response.status_code == 503
    assert response.json()["error"] == "DATABASE_UNAVAILABLE"
    assert response.headers["Cache-Control"] == "no-store"
    assert db.execute.call_count == 1
    assert db.execute.call_args.args[1] == (tables,)


def test_no_pool_is_a_structured_unavailable_error():
    app = create_app()
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=17, role="architect")
    with TestClient(app) as client:
        response = client.get("/api/projects")
    assert response.status_code == 503
    assert response.json() == {"error": "DATABASE_UNAVAILABLE", "message": "Database is unavailable."}


def test_development_revision_uses_only_the_labeled_fixture():
    with TestClient(dev_app) as client:
        response = client.get("/api/revisions/1")
        assert response.status_code == 200
        assert response.headers["X-Exyze-Geometry"] == "dev-fixture"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json() == json.loads(FIXTURE_PATH.read_text())
        assert client.get("/api/revisions/2").status_code == 404
        assert client.get("/api/projects").status_code == 404
        assert client.get("/api/revisions/invalid").status_code == 422


def test_development_app_rejects_an_invalid_fixture_at_startup(tmp_path, monkeypatch):
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"version": 2}')
    monkeypatch.setattr(dev, "FIXTURE_PATH", invalid)
    with pytest.raises(ValidationError), TestClient(dev_app):
        pytest.fail("The dev server started with an invalid geometry document")


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
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("error_type", [
    PoolTimeout, PoolClosed, psycopg.OperationalError,
    psycopg.errors.ConnectionFailure, psycopg.errors.AdminShutdown,
])
def test_database_connection_failures_return_sanitized_503(authenticated, error_type, caplog):
    client, db = authenticated
    db.execute.side_effect = error_type("private credentials")
    response = client.get("/api/projects")
    assert response.status_code == 503
    assert response.json() == {"error": "DATABASE_UNAVAILABLE", "message": "Database is unavailable."}
    assert "private credentials" not in caplog.text


def test_unknown_database_error_is_logged_and_sanitized(authenticated, caplog):
    client, db = authenticated
    db.execute.side_effect = psycopg.errors.UndefinedTable("private_table")
    response = client.get("/api/projects")
    assert response.status_code == 500
    assert response.json() == {"error": "INTERNAL_ERROR", "message": "An internal error occurred."}
    assert "private_table" in caplog.text


def test_http_error_preserves_protocol_headers_and_prevents_caching():
    app = create_app()

    def require_session():
        raise HTTPException(401, "Sign-in required.", {
            "WWW-Authenticate": "Bearer", "Cache-Control": "public",
        })

    app.dependency_overrides[require_principal] = require_session
    with TestClient(app) as client:
        response = client.get("/api/projects")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.headers["Cache-Control"] == "no-store"
        assert client.post("/api/projects").headers["Allow"] == "GET"


def test_unexpected_http_error_does_not_expose_its_detail():
    app = create_app()

    def failing_session():
        raise HTTPException(500, "private upstream detail")

    app.dependency_overrides[require_principal] = failing_session
    with TestClient(app) as client:
        response = client.get("/api/projects")
    assert response.status_code == 500
    assert response.json() == {"error": "INTERNAL_ERROR", "message": "An internal error occurred."}
    assert response.headers["Cache-Control"] == "no-store"
