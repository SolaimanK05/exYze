# Package D Sprint 2 API

Use Python 3.13 and the checked-in `uv.lock`.

```sh
cd backend
uv sync --locked
uv run --locked python -m pytest
```

## Geometry and conversion demo

Run this standalone app on loopback. It serves one sample revision with illustrative IDs and converts uploaded DXF plans in the request. It has no database connection.

```sh
uv run --locked fastapi dev app/dev.py --host 127.0.0.1
curl -i http://127.0.0.1:8000/api/revisions/1
```

The response is a v1 document with the `X-Exyze-Geometry: dev-fixture` header. Other revision IDs return 404.

### POST /api/convert

Send a single multipart field named `file` with a DXF, JPEG, or PNG of up to 10 MiB. Photos are limited to 32 megapixels. The endpoint uses temporary processing and creates no upload, job, or revision records.

```sh
curl -fsS -F 'file=@geometry/tests/data/plan01.dxf' http://127.0.0.1:8000/api/convert
```

DXF success returns HTTP 200 and the Geometry V1 document directly. It includes `version: 1`, `units: "m"`, `source: "dxf"`, and `scale: null`. The parser on `main` produces provisional wall centrelines and labels. The endpoint translates those coordinates to the plan's bottom-left origin. Use the returned document as the geometry input to the 2D and 3D views.

Jahidul can send the selected file through Vite’s `/api` proxy. Let the browser set the multipart boundary.

```ts
const body = new FormData()
body.append('file', file)
const response = await fetch('/api/convert', { method: 'POST', body })
const payload = await response.json()
if (!response.ok) throw new Error(payload.message)
// Pass payload to the existing Geometry V1 view.
```

| HTTP | Meaning |
| --- | --- |
| 400 | Malformed multipart request or missing or extra fields |
| 413 | Upload or photo dimensions exceed the limit |
| 415 | Unsupported request or file type |
| 422 | Empty or unreadable file, or a DXF with no supported wall lines |
| 503 | Valid photo received, but conversion to metre-based Geometry V1 is unavailable |

For example, a valid JPEG currently returns `{"error":"PHOTO_CONVERSION_UNAVAILABLE","message":"Photo conversion needs a processor that turns model masks into metre-scaled geometry."}`. Solaiman’s CLI can demonstrate rough pixel masks separately. Photo Geometry V1 still needs the mask-to-wall and metre-scaling integration.

## Main service

```sh
uv run --locked fastapi dev app/main.py
```

For integration, set `EXYZE_DATABASE_URL` to the `exyze_app` connection URL. E will wire `app.db.require_principal` to its verified session dependency, yielding a `Principal` with the database user ID and role. Until then the main service returns 401. The connection pool sets the role and user ID transaction-locally. Core reads require active RLS on the tables they touch and also check architect ownership. During a request, a connection failure, a different login role, or inactive RLS yields `503 DATABASE_UNAVAILABLE`. Client access remains on E/F's shared-view path.

The main service requires a verified architect or admin session before accepting a conversion upload. Conversion itself uses no database connection.

E’s database bootstrap and migration runner use `DATABASE_URL` with a schema-owner login. Keep that connection separate from the request pool’s `exyze_app` connection. See the [database setup](../db/README.md).

The shared spec leaves project and floor response fields open. The initial summaries use names from F's frontend branch for the fields they return. `/api/projects` returns `id`, `name` and `siteAddress`. `/api/floors/{id}` returns `id`, `levelNo` and `name`. Confirm the list/detail shape and latest-revision navigation with F before frontend wiring.

Once authorization and the schema are in place, the main revision route returns 404 for missing or inaccessible rows and 503 for accessible rows until `revision_geometry` is available. Migration prerequisites and SQL tests are documented with the [staged SQL](../db/pending/package-d/README.md).

To include the pooled-connection test, set `EXYZE_TEST_DB_DSN` to a disposable database with the staged schema, test grants and RLS policies. Use a fixture-writer connection for that variable and the same database's `exyze_app` connection for `EXYZE_TEST_API_DSN`. The test creates two architects and an admin, then removes them and their project afterward.

See the [Sprint 2 demo](../docs/package-d/sprint2-demo.md) for the HTTP smoke checks and database test commands.
