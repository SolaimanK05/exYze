# Package D Sprint 2 migration staging

Shanto (E) owns both prerequisites. The published branches have neither migration. These drafts are outside the runner’s `db/migrations` path while E confirms the release sequence.

1. E lands the canonical `app_user` migration.
2. D promotes `project` and `floor` with filenames ordered after `app_user`.
3. E lands the canonical `upload` migration referencing `floor`. Coordinate its timestamp after `floor` and, if present, C’s `material` migration.
4. D promotes `revision` with a filename ordered after `upload`.
5. Run E’s clean-install migration runner twice, then run the constraint suite below. Make the second runner invocation a check that the migration ledger has no new entries.

Draft timestamps are provisional. Agree the final order with Shanto before promoting any draft. D and E must also coordinate D table grants, E’s login roles and the RLS policies before enabling authenticated reads.

Run the constraint tests from the repo root against a disposable database with all five tables loaded. Use a test role with permission to insert and delete fixtures. Each test rolls back its rows.

```sh
EXYZE_TEST_DB_DSN='postgresql:///exyze_test' backend/.venv/bin/python -m pytest db/tests
```
