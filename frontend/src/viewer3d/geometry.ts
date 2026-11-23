import { Box3, BoxGeometry, Shape, ShapeGeometry, Sphere } from 'three'
import type { BufferGeometry } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import type { Geometry, Opening, Point, Wall } from '../model/geometry'

interface WallSection {
  start: number
  end: number
  bottom: number
  top: number
}

export function toWorld([x, y]: Point, height = 0): [number, number, number] {
  return [x, height, -y]
}

/** Subtract the union of the openings using solid rectangles in wall-local coordinates. */
export function wallSections(length: number, height: number, openings: readonly Opening[]): WallSection[] {
  if (length <= 0 || height <= 0) return []

  const holes = openings
    .map((opening) => ({
      start: Math.max(0, opening.offset),
      end: Math.min(length, opening.offset + opening.width),
      bottom: Math.max(0, opening.sill),
      top: Math.min(height, opening.sill + opening.height),
    }))
    .filter((hole) => hole.end > hole.start && hole.top > hole.bottom)
    .sort((a, b) => a.bottom - b.bottom)

  const edges = [...new Set([0, length, ...holes.flatMap(({ start, end }) => [start, end])])]
    .sort((a, b) => a - b)
  const sections: WallSection[] = []

  for (let i = 1; i < edges.length; i++) {
    const start = edges[i - 1]
    const end = edges[i]
    let bottom = 0
    for (const hole of holes) {
      if (hole.start >= end || hole.end <= start) continue
      if (hole.bottom > bottom) sections.push({ start, end, bottom, top: hole.bottom })
      bottom = Math.max(bottom, hole.top)
    }
    if (bottom < height) sections.push({ start, end, bottom, top: height })
  }

  return sections
}

function wallBoxes(wall: Wall, openings: readonly Opening[]): BoxGeometry[] {
  const dx = wall.x2 - wall.x1
  const dy = wall.y2 - wall.y1
  const length = Math.hypot(dx, dy)
  const angle = Math.atan2(dy, dx)
  if (wall.thickness <= 0) return []

  return wallSections(length, wall.height, openings).map((section) => {
    // Match the 2D viewer's half-thickness end caps to close square corners.
    const start = section.start === 0 ? -wall.thickness / 2 : section.start
    const end = section.end === length ? length + wall.thickness / 2 : section.end
    const box = new BoxGeometry(end - start, section.top - section.bottom, wall.thickness)
    const center = (start + end) / 2
    const planCenter: Point = [wall.x1 + center * dx / length, wall.y1 + center * dy / length]
    return box.rotateY(angle).translate(...toWorld(planCenter, (section.bottom + section.top) / 2))
  })
}

function roomFloor(polygon: readonly Point[]): ShapeGeometry {
  const shape = new Shape()
  shape.moveTo(...polygon[0])
  for (const point of polygon.slice(1)) shape.lineTo(...point)
  shape.closePath()
  // Shape coordinates are in the XY plane. The rotation maps (x, y) to (x, 0, -y).
  return new ShapeGeometry(shape).rotateX(-Math.PI / 2)
}

function mergeParts(parts: BufferGeometry[]): BufferGeometry | null {
  if (!parts.length) return null
  const merged = mergeGeometries(parts)
  for (const part of parts) part.dispose()
  merged?.computeBoundingBox()
  return merged
}

export function buildScene(geometry: Geometry) {
  const wallKeys = new Map(geometry.walls.map(({ id, key }) => [id, key]))
  const openingsByWall = new Map<string, Opening[]>()
  for (const opening of geometry.openings) {
    const key = typeof opening.wall === 'number' ? wallKeys.get(opening.wall) : opening.wall
    if (key === undefined) continue
    const group = openingsByWall.get(key)
    if (group) group.push(opening)
    else openingsByWall.set(key, [opening])
  }

  const walls = mergeParts(geometry.walls.flatMap((wall) => wallBoxes(wall, openingsByWall.get(wall.key) ?? [])))
  const floorsByFinish = new Map<number | null, ShapeGeometry[]>()
  for (const room of geometry.rooms) {
    if (room.polygon.length < 3) continue
    const finish = room.floor_finish ?? null
    const floor = roomFloor(room.polygon)
    const group = floorsByFinish.get(finish)
    if (group) group.push(floor)
    else floorsByFinish.set(finish, [floor])
  }

  const floors = [...floorsByFinish].flatMap(([finish, parts]) => {
    const surface = mergeParts(parts)
    return surface ? [{ finish, surface }] : []
  })
  const bounds = new Box3()
  if (walls?.boundingBox) bounds.union(walls.boundingBox)
  for (const { surface } of floors) {
    if (surface.boundingBox) bounds.union(surface.boundingBox)
  }

  return { walls, floors, framing: bounds.getBoundingSphere(new Sphere()) }
}
