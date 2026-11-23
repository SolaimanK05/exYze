# Database

PostgreSQL 18 with PostGIS 3.6, run by `docker-compose.yml` at the repository root.

## Run it locally

You need Git and Docker (Docker Desktop on Windows and macOS, or Docker Engine with the Compose plugin on Linux). On Windows, run the commands from Git Bash, which comes with Git for Windows.

```
git clone https://github.com/SolaimanK05/exYze.git
cd exYze
cp .env.example .env          # local settings; never commit .env
docker compose up -d db       # PostgreSQL 18 with PostGIS 3.6 on localhost:5432
./db/migrate.sh               # applies every file in db/migrations, in order
```

- `docker compose ps` should show the `db` service as healthy.
- `./db/migrate.sh status` lists which migrations are applied and which are pending.
- If `./db/migrate.sh` says permission denied (some Windows setups), run `bash db/migrate.sh` instead.
- `docker compose down -v` deletes the local database. Start again with the two commands above.
- Port 5432 already in use? Set `DB_PORT` in `.env` and change the port in `DATABASE_URL` to match.

## Migrations

Every schema change is a SQL file in `db/migrations/`, named `YYYYMMDD_HHMM_<package letter>_<what>.sql`, for example `20261125_1430_a_wall_table.sql`. The date and time set the order, so use the time you wrote the file.

`./db/migrate.sh` applies the files that are not in the `schema_migrations` table yet, in name order. Rules it enforces:

- Each file runs in its own transaction. If a statement fails, the whole file is rolled back and the run stops.
- Do not write `BEGIN`, `COMMIT` or `ROLLBACK` in a migration. The runner adds them.
- A file is never edited after it is merged. The runner stores a checksum and refuses to continue if an applied file has changed. Fix mistakes with a new migration.
- A file whose name does not follow the pattern above is rejected.

## Tests

SQL tests live in `db/tests/` and run with pytest. They need `psql` and a reachable database:

```
uv run --project backend pytest db/tests
```

`test_migrate_runner.py` checks the runner itself. It creates a scratch database for each test and drops it afterwards.
