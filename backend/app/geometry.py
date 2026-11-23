from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Positive = Annotated[float, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Id = Annotated[int, Field(gt=0)]
Key = Annotated[str, Field(min_length=1)]
Reference = Id | Key
Point = Annotated[list[float], Field(min_length=2, max_length=2)]


class GeometryModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class Element(GeometryModel):
    id: Id | None = None
    key: Key


class Wall(Element):
    x1: float
    y1: float
    x2: float
    y2: float
    thickness: Positive
    height: Positive
    exterior: bool = False
    finish: Id | None = None
    confidence: Confidence | None = None


class Opening(GeometryModel):
    wall: Reference
    no: Id
    kind: Literal["door", "window"]
    offset: NonNegative
    width: Positive
    height: Positive
    sill: NonNegative
    confidence: Confidence | None = None


class RoomWall(GeometryModel):
    wall: Reference
    side: Literal["left", "right"]


class Room(Element):
    name: str
    type: Literal["bedroom", "living", "kitchen", "bathroom", "dining",
                  "corridor", "balcony", "store", "other"]
    polygon: Annotated[list[Point], Field(min_length=3)]
    floor_finish: Id | None = None
    walls: list[RoomWall] = Field(default_factory=list)


class Label(GeometryModel):
    text: str
    x: float
    y: float


class Item(Element):
    catalog: str
    room: Reference | None = None
    x: float
    y: float
    rotation: Annotated[float, Field(ge=0, lt=360)]
    confidence: Confidence | None = None


class Flag(GeometryModel):
    element_kind: Literal["wall", "opening", "room", "item", "scale"]
    element_ref: str
    reason: str


class Scale(GeometryModel):
    m_per_px: Positive
    method: Literal["ocr", "manual"]
    confirmed: bool


class GeometryV1(GeometryModel):
    version: Literal[1]
    units: Literal["m"]
    source: Literal["dxf", "photo"]
    walls: list[Wall]
    openings: list[Opening]
    rooms: list[Room]
    labels: list[Label]
    items: list[Item]
    flags: list[Flag]
    scale: Scale | None

    @field_validator("version", mode="before")
    @classmethod
    def check_integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Geometry version must be an integer")
        return value

    @model_validator(mode="after")
    def check_document_links(self) -> Self:
        if (self.source == "photo") != (self.scale is not None):
            raise ValueError("Scale is required for photo geometry and must be null for DXF")
        keys = [element.key for element in [*self.walls, *self.rooms, *self.items]]
        if len(keys) != len(set(keys)):
            raise ValueError("Geometry keys must be unique within the document")
        for kind, elements in (("wall", self.walls), ("room", self.rooms), ("item", self.items)):
            stored_ids = [element.id for element in elements if element.id is not None]
            if len(stored_ids) != len(set(stored_ids)):
                raise ValueError(f"Stored {kind} IDs must be unique within the document")

        walls = {wall.key: wall.key for wall in self.walls}
        walls.update({wall.id: wall.key for wall in self.walls if wall.id is not None})
        openings = set()
        for opening in self.openings:
            wall_key = walls.get(opening.wall)
            if wall_key is None:
                raise ValueError("Opening references an unknown wall")
            number = (wall_key, opening.no)
            if number in openings:
                raise ValueError("Opening numbers must be unique within a wall")
            openings.add(number)
        if any(ref.wall not in walls for room in self.rooms for ref in room.walls):
            raise ValueError("Room references an unknown wall")
        rooms = {room.key for room in self.rooms} | {room.id for room in self.rooms}
        if any(item.room is not None and item.room not in rooms for item in self.items):
            raise ValueError("Item references an unknown room")
        return self
