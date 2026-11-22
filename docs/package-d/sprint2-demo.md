# Package D Sprint 2 demo

Use Python 3.13, uv and curl. Start in the repository root.

```sh
cd backend
uv sync --locked
uv run --locked python -m pytest geometry/tests tests ../db/tests -q -ra
```

Without test database connection strings, pytest reports the PostgreSQL tests as skipped.

## Geometry fixture

In the first terminal, from `backend/`, start the standalone demo app.

```sh
uv run --locked fastapi dev app/dev.py --host 127.0.0.1 --port 8000 --no-reload
```

In a second terminal, run the fixture and invalid-ID checks.

```sh
curl -i http://127.0.0.1:8000/api/revisions/1
curl -i http://127.0.0.1:8000/api/revisions/2
curl -i http://127.0.0.1:8000/api/revisions/invalid
```

Revision 1 returns HTTP 200 with `X-Exyze-Geometry: dev-fixture` and `Cache-Control: no-store`. Show `version: 1`, metre units, and the DXF fixture's `scale: null`. The IDs in this sample are illustrative. Revision 2 returns 404 and the nonnumeric ID returns 422.

## Main API without an authenticated session

Stop the demo app. Start the main app from `backend/`.

```sh
env -u EXYZE_DATABASE_URL uv run --locked fastapi dev app/main.py --host 127.0.0.1 --port 8000 --no-reload
```

```sh
for route in projects floors/1 revisions/1; do
  curl -i "http://127.0.0.1:8000/api/$route"
done
```

All three calls return HTTP 401 and `AUTH_REQUIRED`. Once E supplies verified sessions and the database policy integration, project and floor reads can return database rows. The main revision route returns 404 for an inaccessible or missing revision and 503 for an accessible row until Sprint 3 adds `revision_geometry`.

## Database evidence

The [migration staging notes](../../db/pending/package-d/README.md) give the order `app_user → project → floor → upload → revision`. Against an already migrated disposable test database, set `EXYZE_TEST_DB_DSN` for the fixture-writer login and set `EXYZE_TEST_API_DSN` for `exyze_app` on the same database. The API integration tests need the expected grants and RLS policies on the three core tables.

From `backend/`, inspect the schema and run the tests with those variables set.

```sh
psql -X "$EXYZE_TEST_DB_DSN" -c '\d project' -c '\d floor' -c '\d revision'
uv run --locked python -m pytest geometry/tests tests ../db/tests -q -ra
```

The schema checks cover foreign keys, uniqueness, cascade deletion, positive floor height, and the revision state and approval timestamp. The API tests exercise architect isolation and confirm the role and user context clear after pooled requests.
