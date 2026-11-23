# Package D Sprint 2 migration staging

Shanto’s platform changes on `main` provide the migration runner and the PostGIS bootstrap. The runner currently applies only the PostGIS migration. The E-owned `app_user` and `upload` migrations are still pending, so the Package D drafts stay outside its default `db/migrations` path.

1. E lands the canonical `app_user` migration.
2. D promotes `project` and `floor` with filenames ordered after `app_user`.
3. E lands the canonical `upload` migration referencing `floor`. Coordinate its timestamp after `floor` and, if present, C’s `material` migration.
4. D promotes `revision` with a filename ordered after `upload`.
5. At each promotion, run `./db/migrate.sh` twice on a fresh database. The first run should apply the available migrations. The second should report zero applied, and `./db/migrate.sh status` should list them as applied.

Draft timestamps are provisional. Agree the final order with Shanto before promoting any draft. D and E must also coordinate D table grants, E’s login roles and the RLS policies before enabling authenticated reads.

## Integration checks

- The three drafts match the 19 Nov canonical table definitions, including identity keys, foreign keys, cascade rules, and revision approval checks.
- With Shanto, verify `exyze_app` can switch to the approved roles and that architect and admin reads use active RLS. Architects need owner-scoped reads and admins need policies that allow their full access. Clients use shared views.
- Verify promotions through E’s runner on PostgreSQL 18/PostGIS 3.6. The [Sprint 2 demo](../../../docs/package-d/sprint2-demo.md) shows how to inspect the available tables and run verification.

Set `EXYZE_TEST_DB_DSN` to a fixture-writer connection on a disposable database. Each constraint test rolls back its rows. From the repo root, the first migration stage can be tested as soon as `app_user`, `project` and `floor` are present.

```sh
uv run --project backend --locked python -m pytest db/tests/test_package_d_schema.py -k project_floor
```

Remove `-k project_floor` once `upload` and `revision` are present to run all Package D constraints.
