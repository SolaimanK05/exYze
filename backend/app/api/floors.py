from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import RequestDB, ResourceId, require_project_reader
from ..errors import ApiError

router = APIRouter(dependencies=[Depends(require_project_reader)])


class FloorSummary(BaseModel):
    id: int
    level_no: int = Field(serialization_alias="levelNo")
    name: str


@router.get("/floors/{id}", response_model=FloorSummary)
def get_floor(id: ResourceId, db: RequestDB):
    floor = db.execute("""
        SELECT f.floor_id AS id, f.level_no, f.name
        FROM floor AS f JOIN project AS p USING (project_id)
        WHERE f.floor_id = %s
          AND (current_user = 'exyze_admin' OR p.owner_id = current_setting('app.user_id')::bigint)
        """, (id,)).fetchone()
    if floor is None:
        raise ApiError(404, "NOT_FOUND", "Floor not found.")
    return floor
