# Package D Sprint 2 migration staging

Shanto’s platform changes on `main` provide the migration runner and the PostGIS bootstrap. The runner currently applies only the PostGIS migration. The E-owned `app_user` and `upload` migrations are still pending, so the Package D drafts stay outside its default `db/migrations` path.

## Sprint 2 Task 3 coordination

The owners and dependencies are documented. Requests for confirmation are out. Task 3 remains open while owners confirm landing dates and publish their migrations.

| Pending work | Owner | Dependencies | Landing date |
| --- | --- | --- | --- |
| `app_user` | Shanto (E) | Required by `project`, `upload`, and `revision`. | TBD, awaiting owner confirmation. |
| `material` | Rakin (C) | Required by the `wall.finish_id` and `room.floor_finish_id` foreign keys. | TBD, awaiting owner confirmation. |
| `upload` | Shanto (E) | References `floor` and `app_user` and is required by `revision`. | TBD, awaiting owner confirmation. |
| `wall` | Turjo (A) | References `revision` and `material` and is required by `opening`. | TBD, awaiting owner confirmation. |
| `opening` | Solaiman (B) | References `wall`. | TBD, awaiting owner confirmation. |
| `room` | Turjo (A) | References `revision` and `material`. Its polygon needs PostGIS. | TBD, awaiting owner confirmation. |
| Verified sessions, database roles, and RLS | Shanto (E), with Package D for table grants and API wiring | Roles and policies must be in place before enabling authenticated database reads. | TBD, awaiting owner confirmation. |

## Migration order

Enable PostGIS first. The shared order for the affected tables is `app_user → project → floor → material → upload → revision → wall → opening → room`.

1. When E lands `app_user`, D can promote `project` and `floor` and run their constraint tests.
2. Order C’s `material` and E’s `upload` after `floor` in the shared sequence. D can promote `revision` after `upload` lands.
3. A’s `wall` and `room` follow `revision` and `material`. B’s `opening` follows `wall`.
4. At each promotion, run `./db/migrate.sh` twice on a fresh database. The first run should apply the available migrations. The second should report zero applied, and `./db/migrate.sh status` should list them as applied.

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
