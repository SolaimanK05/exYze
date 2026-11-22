# Package D Sprint 2 migration staging

Shanto (E) owns both prerequisites. As of 22 Nov 2026, `origin/main` has neither migration nor the runner. These drafts are outside the runner’s `db/migrations` path while E confirms the release sequence.

1. E lands the canonical `app_user` migration.
2. D promotes `project` and `floor` with filenames ordered after `app_user`.
3. E lands the canonical `upload` migration referencing `floor`. Coordinate its timestamp after `floor` and, if present, C’s `material` migration.
4. D promotes `revision` with a filename ordered after `upload`.
5. Run E’s clean-install migration runner twice, then run the constraint suite below. Make the second runner invocation a check that the migration ledger has no new entries.

Draft timestamps are provisional. Agree the final order with Shanto before promoting any draft. D and E must also coordinate D table grants, E’s login roles and the RLS policies before enabling authenticated reads.

## Integration checks

- The three drafts match the 19 Nov canonical table definitions, including identity keys, foreign keys, cascade rules, and revision approval checks.
- With Shanto, verify `exyze_app` can switch to the approved roles and that architect and admin reads use active RLS. Architects need owner-scoped reads and admins need policies that allow their full access. Clients use shared views.
- After promotion, verify a fresh PostgreSQL 18/PostGIS 3.6 database through E’s runner. Confirm the migration ledger stays unchanged on the second run. The [Sprint 2 demo](../../../docs/package-d/sprint2-demo.md) shows how to inspect the tables and run verification.

Run the constraint tests from the repo root against a disposable database with all five tables loaded. Use a fixture-writer login with the required insert, select and delete privileges. Each constraint test rolls back its rows.

```sh
EXYZE_TEST_DB_DSN='postgresql:///exyze_test' backend/.venv/bin/python -m pytest db/tests
```
