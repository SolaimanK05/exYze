import os
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import Principal, require_principal
from app.main import create_app


def test_project_visibility_and_transaction_context():
    seed_dsn = os.getenv("EXYZE_TEST_DB_DSN")
    api_dsn = os.getenv("EXYZE_TEST_API_DSN")
    if not seed_dsn or not api_dsn:
        pytest.skip("Provide disposable database and exyze_app test connection URLs")

    with psycopg.connect(seed_dsn) as seed:
        users = [
            seed.execute("""
                INSERT INTO app_user (email, full_name, role, password_hash)
                VALUES (%s, %s, %s, 'test-only') RETURNING user_id
                """, (f"{uuid4()}@example.invalid", name, role)).fetchone()[0]
            for name, role in (("Owner", "architect"), ("Other architect", "architect"), ("Admin", "admin"))
        ]
        project, floor, revision = seed.execute("""
            WITH p AS (
                INSERT INTO project (owner_id, name) VALUES (%s, 'API test') RETURNING project_id
            ), f AS (
                INSERT INTO floor (project_id, level_no, name)
                SELECT project_id, 0, 'Ground' FROM p RETURNING floor_id
            ), r AS (
                INSERT INTO revision (floor_id, rev_no, created_by)
                SELECT floor_id, 1, %s FROM f RETURNING revision_id
            )
            SELECT project_id, floor_id, revision_id FROM p, f, r
            """, (users[0], users[0])).fetchone()
        seed.commit()
        try:
            app = create_app(api_dsn)
            actor = Principal(user_id=users[0], role="architect")
            app.dependency_overrides[require_principal] = lambda: actor
            with TestClient(app) as client:
                with app.state.pool.connection() as conn:
                    backend_pid = conn.info.backend_pid
                assert {row["id"] for row in client.get("/api/projects").json()} == {project}
                assert client.get(f"/api/floors/{floor}").json()["name"] == "Ground"
                assert client.get(f"/api/revisions/{revision}").json()["error"] == "GEOMETRY_UNAVAILABLE"

                actor = Principal(user_id=users[1], role="architect")
                assert client.get("/api/projects").json() == []
                for resource, resource_id in (("floors", floor), ("revisions", revision)):
                    hidden = client.get(f"/api/{resource}/{resource_id}")
                    missing = client.get(f"/api/{resource}/9223372036854775807")
                    assert hidden.status_code == missing.status_code == 404
                    assert hidden.json() == missing.json()

                actor = Principal(user_id=users[2], role="admin")
                assert project in {row["id"] for row in client.get("/api/projects").json()}
                assert client.get(f"/api/floors/{floor}").status_code == 200
                admin_revision = client.get(f"/api/revisions/{revision}")
                assert admin_revision.status_code == 503
                assert admin_revision.json()["error"] == "GEOMETRY_UNAVAILABLE"
                with app.state.pool.connection() as conn:
                    assert conn.info.backend_pid == backend_pid
                    context = conn.execute("""
                        SELECT current_user AS role,
                               NULLIF(current_setting('app.user_id', true), '') AS user_id
                        """).fetchone()
                    assert context == {"role": "exyze_app", "user_id": None}
        finally:
            seed.execute("DELETE FROM project WHERE project_id = %s", (project,))
            seed.execute("DELETE FROM app_user WHERE user_id = ANY(%s)", (users,))


def test_core_reads_reject_a_different_database_login():
    seed_dsn = os.getenv("EXYZE_TEST_DB_DSN")
    if not seed_dsn:
        pytest.skip("Provide the separate disposable fixture-writer connection")

    app = create_app(seed_dsn)
    app.dependency_overrides[require_principal] = lambda: Principal(user_id=1, role="admin")
    with TestClient(app) as client:
        response = client.get("/api/projects")
    assert response.status_code == 503
    assert response.json()["error"] == "DATABASE_UNAVAILABLE"
