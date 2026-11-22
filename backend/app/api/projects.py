from fastapi import APIRouter, Depends, Response
from psycopg.rows import DictRow
from pydantic import BaseModel, Field

from ..db import RequestDB, require_project_reader, require_row_security

router = APIRouter(dependencies=[Depends(require_project_reader)])


class ProjectSummary(BaseModel):
    id: int
    name: str
    site_address: str | None = Field(serialization_alias="siteAddress")


@router.get("/projects", response_model=list[ProjectSummary])
def list_projects(db: RequestDB, response: Response) -> list[DictRow]:
    require_row_security(db, "project")
    response.headers["Cache-Control"] = "no-store"
    return db.execute("""
        SELECT project_id AS id, name, site_address
        FROM project
        WHERE current_user = 'exyze_admin' OR owner_id = current_setting('app.user_id')::bigint
        ORDER BY project_id
        """).fetchall()
