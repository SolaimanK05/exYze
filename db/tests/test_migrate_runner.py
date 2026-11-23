"""Tests for db/migrate.sh.

Each test gets its own scratch database on the server that DATABASE_URL points at, and a temporary
migrations folder, so nothing here touches real data. The tests are skipped when bash, psql or the
database are not available (for example on a laptop without psql).
"""

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "db" / "migrate.sh"


def database_url() -> str | None:
    url = os.environ.get("DATABASE_URL")
    env_file = REPO / ".env"
    if not url and env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip()
    return url


def with_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path="/" + name))


def psql(url: str, sql: str) -> str:
    done = subprocess.run(
        ["psql", url, "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@pytest.fixture
def scratch_url():
    admin = database_url()
    if not (admin and shutil.which("psql") and shutil.which("bash")):
        pytest.skip("needs bash, psql and DATABASE_URL")
    reachable = subprocess.run(
        ["psql", admin, "-X", "-c", "SELECT 1"], capture_output=True, check=False
    )
    if reachable.returncode != 0:
        pytest.skip("database is not reachable")

    name = "exyze_migrate_" + uuid.uuid4().hex[:8]
    psql(admin, f'CREATE DATABASE "{name}"')
    try:
        yield with_database(admin, name)
    finally:
        psql(admin, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "migrations"
    path.mkdir()
    return path


def migrate(url: str, folder: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": url, "MIGRATIONS_DIR": str(folder)}
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def write(folder: Path, name: str, sql: str) -> None:
    (folder / name).write_text(sql)


def recorded(url: str) -> list[str]:
    out = psql(url, "SELECT filename FROM schema_migrations ORDER BY filename")
    return out.splitlines()


def test_applies_files_in_name_order_and_records_them(scratch_url, folder):
    write(folder, "20261122_1000_a_first.sql", "CREATE TABLE one (id int PRIMARY KEY);")
    write(
        folder,
        "20261122_1100_b_second.sql",
        "CREATE TABLE two (one_id int REFERENCES one);",
    )

    result = migrate(scratch_url, folder)

    assert result.returncode == 0, result.stderr
    assert "2 applied" in result.stdout
    assert recorded(scratch_url) == [
        "20261122_1000_a_first.sql",
        "20261122_1100_b_second.sql",
    ]


def test_second_run_skips_applied_files_and_picks_up_new_ones(scratch_url, folder):
    write(folder, "20261122_1000_a_first.sql", "CREATE TABLE one (id int);")
    assert migrate(scratch_url, folder).returncode == 0

    again = migrate(scratch_url, folder)
    assert again.returncode == 0
    assert "0 applied, 1 already up to date" in again.stdout

    write(folder, "20261122_1100_b_second.sql", "CREATE TABLE two (id int);")
    third = migrate(scratch_url, folder)
    assert third.returncode == 0
    assert "1 applied, 1 already up to date" in third.stdout


def test_failed_file_is_rolled_back_and_not_recorded(scratch_url, folder):
    write(folder, "20261122_1000_a_good.sql", "CREATE TABLE good (id int);")
    write(
        folder,
        "20261122_1100_b_broken.sql",
        "CREATE TABLE half_done (id int);\nSELECT 1 / 0;\n",
    )
    write(folder, "20261122_1200_c_never_reached.sql", "CREATE TABLE later (id int);")

    result = migrate(scratch_url, folder)

    assert result.returncode != 0
    assert "20261122_1100_b_broken.sql failed" in result.stderr
    assert recorded(scratch_url) == ["20261122_1000_a_good.sql"]
    assert psql(scratch_url, "SELECT to_regclass('half_done')") == ""
    assert psql(scratch_url, "SELECT to_regclass('later')") == ""


def test_editing_an_applied_file_is_rejected(scratch_url, folder):
    write(folder, "20261122_1000_a_first.sql", "CREATE TABLE one (id int);")
    assert migrate(scratch_url, folder).returncode == 0

    write(folder, "20261122_1000_a_first.sql", "CREATE TABLE one (id bigint);")
    result = migrate(scratch_url, folder)

    assert result.returncode != 0
    assert "edited after it was applied" in result.stderr
    status = migrate(scratch_url, folder, "status")
    assert "CHANGED  20261122_1000_a_first.sql" in status.stdout


def test_file_with_a_misspelled_name_is_rejected(scratch_url, folder):
    write(folder, "add_walls.sql", "CREATE TABLE wall (id int);")

    result = migrate(scratch_url, folder)

    assert result.returncode != 0
    assert "does not match" in result.stderr


def test_file_that_manages_its_own_transaction_is_rejected(scratch_url, folder):
    write(
        folder,
        "20261122_1000_a_txn.sql",
        "BEGIN;\nCREATE TABLE one (id int);\nCOMMIT;\n",
    )

    result = migrate(scratch_url, folder)

    assert result.returncode != 0
    assert "manages its own transaction" in result.stderr
    assert psql(scratch_url, "SELECT to_regclass('one')") == ""


def test_status_lists_applied_and_pending(scratch_url, folder):
    write(folder, "20261122_1000_a_first.sql", "CREATE TABLE one (id int);")
    assert migrate(scratch_url, folder).returncode == 0
    write(folder, "20261122_1100_b_second.sql", "CREATE TABLE two (id int);")

    status = migrate(scratch_url, folder, "status")

    assert status.returncode == 0
    assert "applied  20261122_1000_a_first.sql" in status.stdout
    assert "pending  20261122_1100_b_second.sql" in status.stdout
