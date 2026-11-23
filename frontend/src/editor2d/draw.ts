// Drawing maths for the 2D view. Every function here is pure and works in plan coordinates
// (metres, origin bottom-left, y up). Only worldToScreen / screenToWorld know about pixels.

import type { Geometry, Item, Opening, Point, Wall } from '../model/geometry'
import { openingRef } from '../model/geometry'

export interface Size {
  width: number
  height: number
}

export interface Bounds {
  minX: number
  minY: number
  maxX: number
  maxY: number
}

/** screenX = offsetX + x * scale, screenY = offsetY - y * scale (the y axis is flipped). */
export interface View {
  scale: number
  offsetX: number
  offsetY: number
}

export const MIN_SCALE = 5 // pixels per metre
export const MAX_SCALE = 400

const DEG = Math.PI / 180

// ---- Walls -------------------------------------------------------------------------------

export function wallLength(w: Wall): number {
  return Math.hypot(w.x2 - w.x1, w.y2 - w.y1)
}

/** The unit vector from (x1, y1) to (x2, y2). */
export function wallDirection(w: Wall): Point {
  const len = wallLength(w)
  return [(w.x2 - w.x1) / len, (w.y2 - w.y1) / len]
}

/** The unit vector on the left of the wall when you walk from (x1, y1) to (x2, y2). */
export function wallLeftNormal(w: Wall): Point {
  const [dx, dy] = wallDirection(w)
  return [-dy, dx]
}

/**
 * The four corners of the wall as a rectangle, in order around the outline.
 * Each end is pushed out by half the thickness, so walls that meet at right angles close their
 * corners without a notch. Mitred joins for other angles come with the junction data from the DXF parser.
 */
export function wallCorners(w: Wall): [Point, Point, Point, Point] {
  const [dx, dy] = wallDirection(w)
  const [nx, ny] = wallLeftNormal(w)
  const half = w.thickness / 2
  const sx = w.x1 - dx * half
  const sy = w.y1 - dy * half
  const ex = w.x2 + dx * half
  const ey = w.y2 + dy * half
  return [
    [sx + nx * half, sy + ny * half],
    [ex + nx * half, ey + ny * half],
    [ex - nx * half, ey - ny * half],
    [sx - nx * half, sy - ny * half],
  ]
}

// ---- Openings ----------------------------------------------------------------------------

/** The point on the wall's centre line at a distance along the wall from (x1, y1). */
export function pointAlongWall(w: Wall, distance: number): Point {
  const [dx, dy] = wallDirection(w)
  return [w.x1 + dx * distance, w.y1 + dy * distance]
}

/**
 * The solid parts of a wall as rectangles: the wall with its openings cut out, so the room
 * shows through a doorway. Only the two ends of the wall are pushed out by half the thickness.
 */
export function wallSolidQuads(w: Wall, openings: readonly Opening[]): [Point, Point, Point, Point][] {
  const len = wallLength(w)
  const half = w.thickness / 2
  const [nx, ny] = wallLeftNormal(w)

  const spans: [number, number][] = []
  let cursor = 0
  for (const o of [...openings].sort((a, b) => a.offset - b.offset)) {
    const start = Math.max(o.offset, 0)
    const end = Math.min(o.offset + o.width, len)
    if (end <= start) continue
    if (start > cursor) spans.push([cursor, start])
    cursor = Math.max(cursor, end)
  }
  if (cursor < len) spans.push([cursor, len])

  return spans.map(([from, to]) => {
    const a = pointAlongWall(w, from <= 0 ? -half : from)
    const b = pointAlongWall(w, to >= len ? len + half : to)
    return [
      [a[0] + nx * half, a[1] + ny * half],
      [b[0] + nx * half, b[1] + ny * half],
      [b[0] - nx * half, b[1] - ny * half],
      [a[0] - nx * half, a[1] - ny * half],
    ]
  })
}

/** The opening's cut through the wall, as a rectangle as thick as the wall. */
export function openingRect(w: Wall, o: Opening): [Point, Point, Point, Point] {
  const [nx, ny] = wallLeftNormal(w)
  const half = w.thickness / 2
  const [ax, ay] = pointAlongWall(w, o.offset)
  const [bx, by] = pointAlongWall(w, o.offset + o.width)
  return [
    [ax + nx * half, ay + ny * half],
    [bx + nx * half, by + ny * half],
    [bx - nx * half, by - ny * half],
    [ax - nx * half, ay - ny * half],
  ]
}

export function openingCentre(w: Wall, o: Opening): Point {
  return pointAlongWall(w, o.offset + o.width / 2)
}

export interface DoorSymbol {
  /** The hinge, at the near edge of the opening. */
  hinge: Point
  /** The far edge of the opening, where the closed door ends. */
  closedEnd: Point
  /** The end of the door leaf when it is open 90 degrees. */
  leafEnd: Point
  radius: number
}

/**
 * A door is drawn hinged at the near edge, open 90 degrees to the left of the wall's direction.
 * The geometry format has no swing information yet, so this is a symbol, not data.
 */
export function doorSymbol(w: Wall, o: Opening): DoorSymbol {
  const [nx, ny] = wallLeftNormal(w)
  const hinge = pointAlongWall(w, o.offset)
  const closedEnd = pointAlongWall(w, o.offset + o.width)
  return {
    hinge,
    closedEnd,
    leafEnd: [hinge[0] + nx * o.width, hinge[1] + ny * o.width],
    radius: o.width,
  }
}

// ---- Furniture and rooms -----------------------------------------------------------------

/** The four corners of a piece of furniture turned by its rotation (degrees, counter-clockwise). */
export function itemCorners(item: Item, size: { width: number; depth: number }): [Point, Point, Point, Point] {
  const cos = Math.cos(item.rotation * DEG)
  const sin = Math.sin(item.rotation * DEG)
  const hw = size.width / 2
  const hd = size.depth / 2
  const local: Point[] = [
    [-hw, -hd],
    [hw, -hd],
    [hw, hd],
    [-hw, hd],
  ]
  const [a, b, c, d] = local.map(([x, y]): Point => [item.x + x * cos - y * sin, item.y + x * sin + y * cos])
  return [a, b, c, d]
}

export function polygonArea(poly: readonly Point[]): number {
  let twice = 0
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i]
    const [x2, y2] = poly[(i + 1) % poly.length]
    twice += x1 * y2 - x2 * y1
  }
  return twice / 2
}

/** The centre of mass of a polygon, used to place the room's name. */
export function polygonCentroid(poly: readonly Point[]): Point {
  const area = polygonArea(poly)
  if (Math.abs(area) < 1e-9) {
    const n = poly.length || 1
    return [poly.reduce((s, p) => s + p[0], 0) / n, poly.reduce((s, p) => s + p[1], 0) / n]
  }
  let cx = 0
  let cy = 0
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i]
    const [x2, y2] = poly[(i + 1) % poly.length]
    const cross = x1 * y2 - x2 * y1
    cx += (x1 + x2) * cross
    cy += (y1 + y2) * cross
  }
  return [cx / (6 * area), cy / (6 * area)]
}

// ---- Whole plan --------------------------------------------------------------------------

/** The box around everything that is drawn, or null for an empty plan. */
export function geometryBounds(g: Geometry): Bounds | null {
  const points: Point[] = []
  for (const w of g.walls) points.push(...wallCorners(w))
  for (const r of g.rooms) points.push(...r.polygon)
  if (points.length === 0) return null
  const xs = points.map((p) => p[0])
  const ys = points.map((p) => p[1])
  return { minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys) }
}

/** The elements that have an open review flag, as "kind:ref" strings. */
export function flaggedRefs(g: Geometry): Set<string> {
  return new Set(g.flags.map((f) => `${f.element_kind}:${f.element_ref}`))
}

export function isOpeningFlagged(flagged: ReadonlySet<string>, wall: Wall, opening: Opening): boolean {
  return flagged.has(`opening:${openingRef(wall, opening)}`)
}

// ---- View: pan, zoom and fit -------------------------------------------------------------

export function worldToScreen(view: View, [x, y]: Point): Point {
  return [view.offsetX + x * view.scale, view.offsetY - y * view.scale]
}

export function screenToWorld(view: View, [sx, sy]: Point): Point {
  return [(sx - view.offsetX) / view.scale, (view.offsetY - sy) / view.scale]
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** A view that shows the whole plan, centred, with some padding in pixels around it. */
export function fitView(bounds: Bounds | null, size: Size, padding = 56): View {
  const b = bounds ?? { minX: 0, minY: 0, maxX: 10, maxY: 10 }
  const width = Math.max(b.maxX - b.minX, 0.5)
  const height = Math.max(b.maxY - b.minY, 0.5)
  const availW = Math.max(size.width - padding * 2, 1)
  const availH = Math.max(size.height - padding * 2, 1)
  const scale = clamp(Math.min(availW / width, availH / height), MIN_SCALE, MAX_SCALE)
  const cx = (b.minX + b.maxX) / 2
  const cy = (b.minY + b.maxY) / 2
  return { scale, offsetX: size.width / 2 - cx * scale, offsetY: size.height / 2 + cy * scale }
}

/** Zooms by a factor and keeps the plan point under the anchor (a screen point) where it is. */
export function zoomAt(view: View, anchor: Point, factor: number): View {
  const scale = clamp(view.scale * factor, MIN_SCALE, MAX_SCALE)
  const [wx, wy] = screenToWorld(view, anchor)
  return { scale, offsetX: anchor[0] - wx * scale, offsetY: anchor[1] + wy * scale }
}

const SCALE_BAR_LENGTHS_M = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100]

/** The longest round length in metres that fits in maxPx, with its width in pixels. */
export function scaleBar(scale: number, maxPx = 120): { metres: number; px: number } {
  let metres = SCALE_BAR_LENGTHS_M[0]
  for (const m of SCALE_BAR_LENGTHS_M) {
    if (m * scale <= maxPx) metres = m
  }
  return { metres, px: metres * scale }
}
