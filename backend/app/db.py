import logging
from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import Depends, Path, Request
from psycopg import Connection, sql
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, ConfigDict, Field

from .errors import ApiError, DatabaseUnavailable

logger = logging.getLogger(__name__)
MAX_BIGINT = 2**63 - 1
ResourceId = Annotated[int, Path(gt=0, le=MAX_BIGINT)]
DB_ROLES = {
    "admin": "exyze_admin",
    "architect": "exyze_architect",
    "client": "exyze_client",
}


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    user_id: Annotated[int, Field(gt=0, le=MAX_BIGINT)]
    role: Literal["admin", "architect", "client"]


def require_principal() -> Principal:
    """Integration point for E's verified session dependency."""
    raise ApiError(401, "AUTH_REQUIRED", "Sign-in required.")


def make_pool(dsn: str) -> ConnectionPool[Connection[DictRow]]:
    return ConnectionPool(dsn, kwargs={"row_factory": dict_row}, min_size=1, timeout=5, open=False)


def request_db(
    request: Request, actor: Annotated[Principal, Depends(require_principal)]
) -> Iterator[Connection[DictRow]]:
    role = DB_ROLES.get(actor.role)
    if role is None:
        raise ApiError(403, "FORBIDDEN", "Database role is unavailable.")
    pool = request.app.state.pool
    if pool is None:
        raise DatabaseUnavailable()

    with pool.connection() as connection, connection.transaction():
        if connection.info.user != "exyze_app":
            logger.error("Database pool must connect as exyze_app")
            raise DatabaseUnavailable()
        connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(role)))
        connection.execute("SELECT set_config('app.user_id', %s, true)", (str(actor.user_id),))
        yield connection


RequestDB = Annotated[Connection[DictRow], Depends(request_db, scope="function")]


def require_row_security(connection: Connection[DictRow], *tables: str) -> None:
    result = connection.execute("""
        SELECT bool_and(COALESCE(row_security_active(to_regclass(table_name)), false)) AS active
        FROM unnest(%s::text[]) AS t(table_name)
        """, (list(tables),)).fetchone()
    if not result or not result["active"]:
        logger.error("Core reads require active row security on %s", ", ".join(tables))
        raise DatabaseUnavailable()


def require_project_reader(actor: Annotated[Principal, Depends(require_principal)]) -> None:
    if actor.role not in ("admin", "architect"):
        raise ApiError(403, "FORBIDDEN", "Project reads require an architect or admin.")
