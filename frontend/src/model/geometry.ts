// The geometry format from 01 Architecture and Contracts ("The geometry format").
// Lengths are metres, the origin is the bottom-left of the plan, x points right and y points up.
// Angles are degrees, counter-clockwise from the positive x axis.

export type Point = [number, number]

export type OpeningKind = 'door' | 'window'

export type RoomType =
  | 'bedroom'
  | 'living'
  | 'kitchen'
  | 'bathroom'
  | 'dining'
  | 'corridor'
  | 'balcony'
  | 'store'
  | 'other'

/** A wall is its centre line from (x1, y1) to (x2, y2), plus a thickness and a height. */
export interface Wall {
  /** Database id. Present when the wall is already stored. */
  id?: number
  /** Unique within one document. Imports use w1, w2, ... and the web app uses UUIDs. */
  key: string
  x1: number
  y1: number
  x2: number
  y2: number
  thickness: number
  height: number
  exterior?: boolean
  finish?: number | null
  confidence?: number
}

export interface Opening {
  /** The key or the id of the wall the opening is in. */
  wall: string | number
  /** The opening's number within its wall, starting at 1. */
  no: number
  kind: OpeningKind
  /** Distance along the wall from (x1, y1) to the near edge of the opening. */
  offset: number
  width: number
  height: number
  sill: number
  confidence?: number
}

export interface RoomWallRef {
  wall: string | number
  side: 'left' | 'right'
}

export interface Room {
  id?: number
  key: string
  name: string
  type: RoomType
  polygon: Point[]
  floor_finish?: number | null
  walls?: RoomWallRef[]
}

/** Room names found in the plan's text. They are used only to name rooms. */
export interface Label {
  text: string
  x: number
  y: number
}

export interface Item {
  id?: number
  key: string
  /** The code of a catalogue item, for example sofa_3. */
  catalog: string
  room?: string | number | null
  x: number
  y: number
  rotation: number
  confidence?: number
}

export type FlagElementKind = 'wall' | 'opening' | 'room' | 'item' | 'scale'

export interface Flag {
  element_kind: FlagElementKind
  /** A wall, room or item key, or "<wall key>/<opening no>" for an opening. */
  element_ref: string
  reason: string
}

export interface Scale {
  m_per_px: number | null
  method: 'ocr' | 'manual' | null
  confirmed: boolean
}

export interface Geometry {
  version: 1
  units: 'm'
  source: 'dxf' | 'photo'
  walls: Wall[]
  openings: Opening[]
  rooms: Room[]
  labels: Label[]
  items: Item[]
  flags: Flag[]
  scale: Scale | null
}

/** Finds a wall by the key or the id that an opening or a room uses to refer to it. */
export function findWall(walls: readonly Wall[], ref: string | number): Wall | undefined {
  return walls.find((w) => w.key === ref || w.id === ref)
}

/** The element_ref of an opening in a flag: "<wall key>/<opening no>". */
export function openingRef(wall: Wall, opening: Opening): string {
  return `${wall.key}/${opening.no}`
}
