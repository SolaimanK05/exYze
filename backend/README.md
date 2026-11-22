# Package D Sprint 2 API

Use Python 3.13 and the checked-in `uv.lock`.

```sh
cd backend
uv sync --locked
uv run --locked python -m pytest tests
```

## Geometry demo

Run this standalone app on loopback. It serves one sample revision with illustrative IDs, and has no database connection.

```sh
uv run --locked fastapi dev app/dev.py --host 127.0.0.1
curl -i http://127.0.0.1:8000/api/revisions/1
```

The response is a v1 document with the `X-Exyze-Geometry: dev-fixture` header. Other revision IDs return 404.

## Main service

```sh
uv run --locked fastapi dev app/main.py
```

For integration, set `EXYZE_DATABASE_URL` to the `exyze_app` connection URL. E will wire `app.db.require_principal` to its verified session dependency, yielding a `Principal` with the database user ID and role. Until then the main service returns 401. The connection pool sets the role and user ID transaction-locally. Core reads require active RLS on the tables they touch and also check architect ownership. During a request, a connection failure, a different login role, or inactive RLS yields `503 DATABASE_UNAVAILABLE`. Client access remains on E/F's shared-view path.

The shared spec leaves project and floor response fields open. The initial summaries use names from F's frontend branch for the fields they return. `/api/projects` returns `id`, `name` and `siteAddress`. `/api/floors/{id}` returns `id`, `levelNo` and `name`. Confirm the list/detail shape and latest-revision navigation with F before frontend wiring.

Once authorization and the schema are in place, the main revision route returns 404 for missing or inaccessible rows and 503 for accessible rows until `revision_geometry` is available. Migration prerequisites and SQL tests are documented with the [staged SQL](../db/pending/package-d/README.md).

To include the pooled-connection test, set `EXYZE_TEST_DB_DSN` to a disposable database with the staged schema, test grants and RLS policies. Use a fixture-writer connection for that variable and the same database's `exyze_app` connection for `EXYZE_TEST_API_DSN`. The test creates two architects and removes them and their project afterward.

See the [Sprint 2 demo](../docs/package-d/sprint2-demo.md) for the HTTP smoke checks and database test commands.
