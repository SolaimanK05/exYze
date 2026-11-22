#!/usr/bin/env bash
# Applies the SQL files in db/migrations that have not been applied yet.
#
#   ./db/migrate.sh           apply pending migrations
#   ./db/migrate.sh status    list applied and pending migrations
#
# Which database it talks to:
#   - DATABASE_URL set and psql installed: psql connects straight to it (CI works this way).
#   - otherwise: psql runs inside the compose "db" container, so nothing needs installing on the host.
# MIGRATIONS_DIR overrides the folder to read, which the tests use.
#
# Each file runs in its own transaction together with its schema_migrations row, so a failed file
# leaves nothing behind. Files must not contain BEGIN, COMMIT or ROLLBACK.

set -euo pipefail
export LC_ALL=C

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

migrations_dir="${MIGRATIONS_DIR:-$root/db/migrations}"
name_pattern='^[0-9]{8}_[0-9]{4}_[a-f]_[a-z0-9_]+\.sql$'

die() {
  echo "migrate: $*" >&2
  exit 1
}

# Reads .env without overriding variables that are already set in the environment.
load_env() {
  local line key value
  [[ -f .env ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      if [[ -z "${!key+x}" ]]; then
        export "$key=$value"
      fi
    fi
  done < .env
}

load_env

if [[ -n "${DATABASE_URL:-}" ]] && command -v psql >/dev/null 2>&1; then
  run_psql() { psql "$DATABASE_URL" -X -q -v ON_ERROR_STOP=1 "$@"; }
else
  [[ -n "${POSTGRES_USER:-}" && -n "${POSTGRES_DB:-}" ]] \
    || die "no .env found. Run: cp .env.example .env"
  run_psql() {
    docker compose exec -T db psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"
  }
fi

checksum() {
  # CRLF is stripped first so Windows and Linux checkouts give the same value.
  if command -v sha256sum >/dev/null 2>&1; then
    tr -d '\r' < "$1" | sha256sum | cut -d' ' -f1
  else
    tr -d '\r' < "$1" | shasum -a 256 | cut -d' ' -f1
  fi
}

run_psql -c 'SELECT 1' >/dev/null 2>&1 \
  || die "cannot reach the database. Start it with: docker compose up -d db"

run_psql -c "SET client_min_messages = warning;
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename   text PRIMARY KEY,
  checksum   text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
)"

applied="$(run_psql -t -A -F '|' -c 'SELECT filename, checksum FROM schema_migrations' | tr -d '\r')"

recorded_checksum() {
  printf '%s\n' "$applied" | awk -F'|' -v n="$1" '$1 == n { print $2 }'
}

files=()
for f in "$migrations_dir"/*.sql; do
  [[ -e "$f" ]] && files+=("$f")
done

for f in ${files[@]+"${files[@]}"}; do
  name="$(basename "$f")"
  [[ "$name" =~ $name_pattern ]] \
    || die "$name does not match YYYYMMDD_HHMM_<package letter>_<what>.sql"
done

if [[ "${1:-}" == "status" ]]; then
  for f in ${files[@]+"${files[@]}"}; do
    name="$(basename "$f")"
    old="$(recorded_checksum "$name")"
    if [[ -z "$old" ]]; then
      echo "pending  $name"
    elif [[ "$old" != "$(checksum "$f")" ]]; then
      echo "CHANGED  $name"
    else
      echo "applied  $name"
    fi
  done
  exit 0
fi

[[ $# -eq 0 ]] || die "unknown argument '$1' (use no argument, or 'status')"

n_applied=0
n_skipped=0
for f in ${files[@]+"${files[@]}"}; do
  name="$(basename "$f")"
  sum="$(checksum "$f")"
  old="$(recorded_checksum "$name")"

  if [[ -n "$old" ]]; then
    [[ "$old" == "$sum" ]] \
      || die "$name was edited after it was applied. Revert the edit and fix forward with a new migration."
    n_skipped=$((n_skipped + 1))
    continue
  fi

  if grep -Eiq '^[[:space:]]*(begin|commit|rollback|start[[:space:]]+transaction)\b' "$f"; then
    die "$name manages its own transaction. The runner already wraps each file in one."
  fi

  echo "applying $name"
  if ! {
    echo 'BEGIN;'
    tr -d '\r' < "$f"
    echo
    echo "INSERT INTO schema_migrations (filename, checksum) VALUES ('$name', '$sum');"
    echo 'COMMIT;'
  } | run_psql -f -; then
    die "$name failed and was rolled back. Nothing after it was run."
  fi
  n_applied=$((n_applied + 1))
done

echo "done: $n_applied applied, $n_skipped already up to date"
