import os
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest


@pytest.fixture
def db():
    dsn = os.getenv("EXYZE_TEST_DB_DSN")
    if not dsn:
        pytest.skip("Set EXYZE_TEST_DB_DSN to a disposable database with the schema under test")
    with psycopg.connect(dsn) as connection:
        try:
            yield connection
        finally:
            connection.rollback()


@pytest.fixture
def project_floor_rows(db):
    user_id = db.execute("""
        INSERT INTO app_user (email, full_name, role, password_hash)
        VALUES (%s, 'Package D test', 'architect', 'test-only') RETURNING user_id
        """, (f"{uuid4()}@example.invalid",)).fetchone()[0]
    client_id = db.execute("""
        INSERT INTO app_user (email, full_name, role, password_hash)
        VALUES (%s, 'Package D client', 'client', 'test-only') RETURNING user_id
        """, (f"{uuid4()}@example.invalid",)).fetchone()[0]
    project_id, created_at = db.execute("""
        INSERT INTO project (owner_id, client_id, name)
        VALUES (%s, %s, 'Test project') RETURNING project_id, created_at
        """, (user_id, client_id)).fetchone()
    assert created_at is not None
    floor_id, height = db.execute("""
        INSERT INTO floor (project_id, level_no, name)
        VALUES (%s, 0, 'Ground') RETURNING floor_id, default_height_m
        """, (project_id,)).fetchone()
    assert height == Decimal("3.00")
    return {"user": user_id, "project": project_id, "floor": floor_id}


@pytest.fixture
def revision_rows(db, project_floor_rows):
    upload_id = db.execute("""
        INSERT INTO upload (floor_id, uploaded_by, source, file_path)
        VALUES (%(floor)s, %(user)s, 'dxf', 'test.dxf') RETURNING upload_id
        """, project_floor_rows).fetchone()[0]
    revision_id, state, approved_at, created_at, parent_id = db.execute("""
        INSERT INTO revision (floor_id, rev_no, upload_id, created_by)
        VALUES (%(floor)s, 1, %(upload)s, %(user)s)
        RETURNING revision_id, state, approved_at, created_at, parent_id
        """, {**project_floor_rows, "upload": upload_id}).fetchone()
    assert state == "draft" and approved_at is None and created_at is not None
    assert parent_id is None
    return {
        **project_floor_rows,
        "upload": upload_id,
        "revision": revision_id,
    }


@pytest.mark.parametrize(("sqlstate", "statement"), [
    ("23503", "INSERT INTO project (owner_id, name) VALUES (-1, 'Unknown owner')"),
    ("23503", "INSERT INTO project (owner_id, client_id, name) VALUES (%(user)s, -1, 'Unknown client')"),
    ("23502", "INSERT INTO project (owner_id, name) VALUES (NULL, 'Missing owner')"),
    ("23502", "INSERT INTO project (owner_id, name) VALUES (%(user)s, NULL)"),
    ("23502", "INSERT INTO project (owner_id, name, created_at) VALUES (%(user)s, 'Test', NULL)"),
    ("428C9", "INSERT INTO project (project_id, owner_id, name) VALUES (10, %(user)s, 'Test')"),
    ("23505", """INSERT INTO project (project_id, owner_id, name) OVERRIDING SYSTEM VALUE
                 VALUES (%(project)s, %(user)s, 'Duplicate ID')"""),
    ("23503", "INSERT INTO floor (project_id, level_no, name) VALUES (-1, 0, 'Ground')"),
    ("23502", "INSERT INTO floor (project_id, level_no, name) VALUES (NULL, 1, 'First')"),
    ("23502", "INSERT INTO floor (project_id, level_no, name) VALUES (%(project)s, NULL, 'First')"),
    ("23502", "INSERT INTO floor (project_id, level_no, name) VALUES (%(project)s, 1, NULL)"),
    ("23502", """INSERT INTO floor (project_id, level_no, name, default_height_m)
                 VALUES (%(project)s, 1, 'No height', NULL)"""),
    ("428C9", """INSERT INTO floor (floor_id, project_id, level_no, name)
                 VALUES (10, %(project)s, 1, 'First')"""),
    ("23505", """INSERT INTO floor (floor_id, project_id, level_no, name) OVERRIDING SYSTEM VALUE
                 VALUES (%(floor)s, %(project)s, 1, 'Duplicate ID')"""),
    ("23505", "INSERT INTO floor (project_id, level_no, name) VALUES (%(project)s, 0, 'Duplicate')"),
    ("23514", """INSERT INTO floor (project_id, level_no, name, default_height_m)
                 VALUES (%(project)s, 1, 'Zero', 0)"""),
    ("23514", """INSERT INTO floor (project_id, level_no, name, default_height_m)
                 VALUES (%(project)s, 1, 'Negative', -1)"""),
])
def test_project_floor_rejected_insert(db, project_floor_rows, sqlstate, statement):
    with pytest.raises(psycopg.Error) as error, db.transaction():
        db.execute(statement, project_floor_rows)
    assert error.value.sqlstate == sqlstate


@pytest.mark.parametrize(("sqlstate", "statement"), [
    ("23503", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (-1, 2, %(user)s)"),
    ("23503", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (%(floor)s, 2, -1)"),
    ("23502", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (NULL, 2, %(user)s)"),
    ("23502", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (%(floor)s, NULL, %(user)s)"),
    ("23502", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (%(floor)s, 2, NULL)"),
    ("23502", """INSERT INTO revision (floor_id, rev_no, created_by, state)
                 VALUES (%(floor)s, 2, %(user)s, NULL)"""),
    ("23502", """INSERT INTO revision (floor_id, rev_no, created_by, created_at)
                 VALUES (%(floor)s, 2, %(user)s, NULL)"""),
    ("428C9", """INSERT INTO revision (revision_id, floor_id, rev_no, created_by)
                 VALUES (10, %(floor)s, 2, %(user)s)"""),
    ("23505", """INSERT INTO revision (revision_id, floor_id, rev_no, created_by) OVERRIDING SYSTEM VALUE
                 VALUES (%(revision)s, %(floor)s, 2, %(user)s)"""),
    ("23505", "INSERT INTO revision (floor_id, rev_no, created_by) VALUES (%(floor)s, 1, %(user)s)"),
    ("23503", """INSERT INTO revision (floor_id, rev_no, created_by, parent_id)
                 VALUES (%(floor)s, 2, %(user)s, -1)"""),
    ("23503", """INSERT INTO revision (floor_id, rev_no, created_by, upload_id)
                 VALUES (%(floor)s, 2, %(user)s, -1)"""),
    ("23505", """INSERT INTO revision (floor_id, rev_no, created_by, upload_id)
                 VALUES (%(floor)s, 2, %(user)s, %(upload)s)"""),
    ("23514", """INSERT INTO revision (floor_id, rev_no, created_by, state)
                 VALUES (%(floor)s, 2, %(user)s, 'published')"""),
    ("23514", """INSERT INTO revision (floor_id, rev_no, created_by, state)
                 VALUES (%(floor)s, 2, %(user)s, 'approved')"""),
    ("23514", """INSERT INTO revision (floor_id, rev_no, created_by, approved_at)
                 VALUES (%(floor)s, 2, %(user)s, now())"""),
    ("23514", """INSERT INTO revision (floor_id, rev_no, created_by, state, approved_at)
                 VALUES (%(floor)s, 2, %(user)s, 'in_review', now())"""),
])
def test_revision_rejected_insert(db, revision_rows, sqlstate, statement):
    with pytest.raises(psycopg.Error) as error, db.transaction():
        db.execute(statement, revision_rows)
    assert error.value.sqlstate == sqlstate


def test_project_floor_levels_are_scoped(db, project_floor_rows):
    height = db.execute("""
        INSERT INTO floor (project_id, level_no, name, default_height_m)
        VALUES (%(project)s, 1, 'First', 2.75) RETURNING default_height_m
        """, project_floor_rows).fetchone()[0]
    assert height == Decimal("2.75")
    other_height = db.execute("""
        WITH other_project AS (
            INSERT INTO project (owner_id, name)
            VALUES (%(user)s, 'Other') RETURNING project_id
        )
        INSERT INTO floor (project_id, level_no, name)
        SELECT project_id, 0, 'Ground' FROM other_project
        RETURNING default_height_m
        """, project_floor_rows).fetchone()[0]
    assert other_height == Decimal("3.00")


def test_project_floor_delete_cascades(db, project_floor_rows):
    db.execute("DELETE FROM project WHERE project_id = %(project)s", project_floor_rows)
    assert db.execute(
        "SELECT 1 FROM floor WHERE floor_id = %(floor)s", project_floor_rows,
    ).fetchone() is None


def test_revision_number_scope_and_approval(db, revision_rows):
    other_floor = db.execute("""
        INSERT INTO floor (project_id, level_no, name)
        VALUES (%(project)s, 1, 'First') RETURNING floor_id
        """, revision_rows).fetchone()[0]
    db.execute("""
        INSERT INTO revision (floor_id, rev_no, created_by) VALUES (%s, 1, %s)
        """, (other_floor, revision_rows["user"]))

    child = db.execute("""
        INSERT INTO revision (floor_id, rev_no, parent_id, created_by, state)
        VALUES (%(floor)s, 2, %(revision)s, %(user)s, 'in_review')
        RETURNING parent_id, state, approved_at, upload_id
        """, revision_rows).fetchone()
    assert child == (revision_rows["revision"], "in_review", None, None)
    state, approved_at = db.execute("""
        INSERT INTO revision (floor_id, rev_no, parent_id, created_by, state, approved_at)
        VALUES (%(floor)s, 3, %(revision)s, %(user)s, 'approved', now())
        RETURNING state, approved_at
        """, revision_rows).fetchone()
    assert state == "approved" and approved_at is not None


@pytest.mark.parametrize("delete_from", [
    "DELETE FROM project WHERE project_id = %(project)s",
    "DELETE FROM floor WHERE floor_id = %(floor)s",
])
def test_revision_delete_cascades(db, revision_rows, delete_from):
    db.execute("""
        INSERT INTO revision (floor_id, rev_no, parent_id, created_by)
        VALUES (%(floor)s, 2, %(revision)s, %(user)s)
        """, revision_rows)
    db.execute(delete_from, revision_rows)
    assert db.execute("SELECT 1 FROM floor WHERE floor_id = %(floor)s", revision_rows).fetchone() is None
    assert db.execute(
        "SELECT 1 FROM revision WHERE floor_id = %(floor)s", revision_rows,
    ).fetchone() is None
