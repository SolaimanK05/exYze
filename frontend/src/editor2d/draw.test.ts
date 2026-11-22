import { describe, expect, it } from 'vitest'
import type { Item, Opening, Point, Wall } from '../model/geometry'
import { findWall, openingRef } from '../model/geometry'
import { sampleGeometry } from '../model/sampleGeometry'
import {
  MAX_SCALE,
  doorSymbol,
  fitView,
  flaggedRefs,
  geometryBounds,
  itemCorners,
  openingCentre,
  openingRect,
  pointAlongWall,
  polygonArea,
  polygonCentroid,
  scaleBar,
  screenToWorld,
  wallCorners,
  wallDirection,
  wallLeftNormal,
  wallLength,
  wallSolidQuads,
  worldToScreen,
  zoomAt,
} from './draw'
import { placeholderCatalog } from './placeholderCatalog'

function expectPoint(actual: Point, expected: Point) {
  expect(actual[0]).toBeCloseTo(expected[0], 6)
  expect(actual[1]).toBeCloseTo(expected[1], 6)
}

function expectPoints(actual: readonly Point[], expected: readonly Point[]) {
  expect(actual).toHaveLength(expected.length)
  actual.forEach((p, i) => expectPoint(p, expected[i]))
}

const southWall: Wall = { key: 'w1', x1: 0, y1: 0, x2: 9, y2: 0, thickness: 0.25, height: 3 }
const westWall: Wall = { key: 'w4', x1: 0, y1: 7, x2: 0, y2: 0, thickness: 0.25, height: 3 }
const northWall: Wall = { key: 'w3', x1: 9, y1: 7, x2: 0, y2: 7, thickness: 0.25, height: 3 }

describe('walls', () => {
  it('measures length and direction', () => {
    expect(wallLength(southWall)).toBe(9)
    expectPoint(wallDirection(westWall), [0, -1])
  })

  it('puts the left normal on the left of the walking direction', () => {
    expectPoint(wallLeftNormal(southWall), [0, 1]) // walking east, left is north
    expectPoint(wallLeftNormal(westWall), [1, 0]) // walking south, left is east
    expectPoint(wallLeftNormal(northWall), [0, -1]) // walking west, left is south
  })

  it('draws a wall as a rectangle whose ends are pushed out by half the thickness', () => {
    expectPoints(wallCorners(southWall), [
      [-0.125, 0.125],
      [9.125, 0.125],
      [9.125, -0.125],
      [-0.125, -0.125],
    ])
  })

  it('closes the corner where two walls of the same thickness meet', () => {
    // Both walls cover the square around (0, 0), so its outer corner (-0.125, -0.125) is on both.
    const hasOuterCorner = (corners: Point[]) =>
      corners.some((p) => Math.abs(p[0] + 0.125) < 1e-9 && Math.abs(p[1] + 0.125) < 1e-9)
    expect(hasOuterCorner(wallCorners(southWall))).toBe(true)
    expect(hasOuterCorner(wallCorners(westWall))).toBe(true)
  })

  it('leaves a wall whole when it has no openings', () => {
    expect(wallSolidQuads(southWall, [])).toEqual([wallCorners(southWall)])
  })

  it('cuts an opening out of a wall, leaving a solid piece on each side', () => {
    const window: Opening = { wall: 'w1', no: 1, kind: 'window', offset: 1.2, width: 1.8, height: 1.2, sill: 0.9 }
    const quads = wallSolidQuads(southWall, [window])
    expect(quads).toHaveLength(2)
    expectPoints(quads[0], [
      [-0.125, 0.125],
      [1.2, 0.125],
      [1.2, -0.125],
      [-0.125, -0.125],
    ])
    expectPoints(quads[1], [
      [3.0, 0.125],
      [9.125, 0.125],
      [9.125, -0.125],
      [3.0, -0.125],
    ])
  })

  it('draws one solid piece when the opening starts at the end of the wall', () => {
    const door: Opening = { wall: 'w1', no: 1, kind: 'door', offset: 0, width: 1, height: 2.1, sill: 0 }
    const quads = wallSolidQuads(southWall, [door])
    expect(quads).toHaveLength(1)
    expectPoint(quads[0][0], [1, 0.125])
  })

  it('does not care about the order of the openings', () => {
    const a: Opening = { wall: 'w1', no: 1, kind: 'window', offset: 5, width: 1, height: 1, sill: 1 }
    const b: Opening = { wall: 'w1', no: 2, kind: 'window', offset: 1, width: 1, height: 1, sill: 1 }
    expect(wallSolidQuads(southWall, [a, b])).toEqual(wallSolidQuads(southWall, [b, a]))
    expect(wallSolidQuads(southWall, [a, b])).toHaveLength(3)
  })
})

describe('openings', () => {
  const window: Opening = { wall: 'w3', no: 1, kind: 'window', offset: 0.6, width: 1.4, height: 1.2, sill: 0.9 }

  it('measures the offset along the wall from its first end, also for a wall that runs west', () => {
    expectPoint(pointAlongWall(northWall, 0.6), [8.4, 7])
    expectPoint(openingCentre(northWall, window), [7.7, 7])
  })

  it('cuts through the whole thickness of the wall', () => {
    expectPoints(openingRect(northWall, window), [
      [8.4, 6.875],
      [7.0, 6.875],
      [7.0, 7.125],
      [8.4, 7.125],
    ])
  })

  it('hinges a door at the near edge and opens it to the left of the wall', () => {
    const wall: Wall = { key: 'w5', x1: 0, y1: 3.5, x2: 9, y2: 3.5, thickness: 0.125, height: 3 }
    const door: Opening = { wall: 'w5', no: 1, kind: 'door', offset: 2, width: 0.9, height: 2.1, sill: 0 }
    const symbol = doorSymbol(wall, door)
    expectPoint(symbol.hinge, [2, 3.5])
    expectPoint(symbol.closedEnd, [2.9, 3.5])
    expectPoint(symbol.leafEnd, [2, 4.4])
    expect(symbol.radius).toBe(0.9)
  })

  it('names an opening as "<wall key>/<number>", the way review flags refer to it', () => {
    expect(openingRef(northWall, window)).toBe('w3/1')
  })
})

describe('furniture and rooms', () => {
  it('turns a piece of furniture counter-clockwise by its rotation', () => {
    const bed: Item = { key: 'i6', catalog: 'bed_double', x: 1.15, y: 6, rotation: 90 }
    expectPoints(itemCorners(bed, { width: 1.6, depth: 2 }), [
      [2.15, 5.2],
      [2.15, 6.8],
      [0.15, 6.8],
      [0.15, 5.2],
    ])
  })

  it('finds the area and centre of a room', () => {
    const room: Point[] = [
      [0, 0],
      [5.5, 0],
      [5.5, 3.5],
      [0, 3.5],
    ]
    expect(polygonArea(room)).toBeCloseTo(19.25, 6)
    expectPoint(polygonCentroid(room), [2.75, 1.75])
  })
})

describe('the view', () => {
  it('finds the box around the sample plan, including the wall thickness', () => {
    expect(geometryBounds(sampleGeometry)).toEqual({ minX: -0.125, minY: -0.125, maxX: 9.125, maxY: 7.125 })
  })

  it('has no bounds for an empty plan', () => {
    expect(geometryBounds({ ...sampleGeometry, walls: [], rooms: [] })).toBeNull()
  })

  it('flips the y axis between plan and screen, and back', () => {
    const view = { scale: 50, offsetX: 100, offsetY: 400 }
    expectPoint(worldToScreen(view, [2, 3]), [200, 250])
    expectPoint(screenToWorld(view, [200, 250]), [2, 3])
  })

  it('fits the plan in the middle of the window', () => {
    const bounds = geometryBounds(sampleGeometry)
    const view = fitView(bounds, { width: 800, height: 600 })
    expectPoint(worldToScreen(view, [4.5, 3.5]), [400, 300])
    // Both sides stay inside the window, with the padding left over.
    const [left, bottom] = worldToScreen(view, [-0.125, -0.125])
    const [right, top] = worldToScreen(view, [9.125, 7.125])
    expect(left).toBeGreaterThanOrEqual(56 - 1e-6)
    expect(right).toBeLessThanOrEqual(800 - 56 + 1e-6)
    expect(top).toBeGreaterThanOrEqual(56 - 1e-6)
    expect(bottom).toBeLessThanOrEqual(600 - 56 + 1e-6)
  })

  it('keeps the point under the cursor where it is when zooming', () => {
    const view = { scale: 50, offsetX: 100, offsetY: 400 }
    const anchor: Point = [300, 200]
    const zoomed = zoomAt(view, anchor, 2)
    expect(zoomed.scale).toBe(100)
    expectPoint(worldToScreen(zoomed, screenToWorld(view, anchor)), anchor)
  })

  it('stops zooming at the limits', () => {
    const view = { scale: 50, offsetX: 0, offsetY: 0 }
    expect(zoomAt(view, [0, 0], 1000).scale).toBe(MAX_SCALE)
    expect(zoomAt(view, [0, 0], 0.0001).scale).toBeGreaterThan(0)
  })

  it('picks a round length for the scale bar', () => {
    expect(scaleBar(50)).toEqual({ metres: 2, px: 100 })
    expect(scaleBar(200)).toEqual({ metres: 0.5, px: 100 })
  })
})

function pointInPolygon([x, y]: Point, poly: readonly Point[]): boolean {
  let inside = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]
    const [xj, yj] = poly[j]
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

// The same rules the database enforces (a door must fit inside its wall, furniture must be inside a room),
// so the sample stays a valid revision.
describe('the sample plan', () => {
  it('has unique wall keys and unique opening numbers within a wall', () => {
    const keys = sampleGeometry.walls.map((w) => w.key)
    expect(new Set(keys).size).toBe(keys.length)
    const refs = sampleGeometry.openings.map((o) => `${o.wall}/${o.no}`)
    expect(new Set(refs).size).toBe(refs.length)
  })

  it('has every opening inside its wall', () => {
    for (const o of sampleGeometry.openings) {
      const wall = findWall(sampleGeometry.walls, o.wall)
      expect(wall, `wall of opening ${o.wall}/${o.no}`).toBeDefined()
      expect(o.offset).toBeGreaterThanOrEqual(0)
      expect(o.offset + o.width, `opening ${o.wall}/${o.no} fits`).toBeLessThanOrEqual(wallLength(wall!) + 1e-9)
    }
  })

  it('has no two openings on one wall that overlap', () => {
    for (const wall of sampleGeometry.walls) {
      const spans = sampleGeometry.openings
        .filter((o) => o.wall === wall.key)
        .map((o) => [o.offset, o.offset + o.width] as const)
        .sort((a, b) => a[0] - b[0])
      for (let i = 1; i < spans.length; i++) {
        expect(spans[i][0], `overlap on ${wall.key}`).toBeGreaterThanOrEqual(spans[i - 1][1])
      }
    }
  })

  it('has every piece of furniture in the catalogue and inside its room', () => {
    for (const item of sampleGeometry.items) {
      expect(placeholderCatalog[item.catalog], `catalogue code ${item.catalog}`).toBeDefined()
      const room = sampleGeometry.rooms.find((r) => r.key === item.room)
      expect(room, `room of ${item.key}`).toBeDefined()
      for (const corner of itemCorners(item, placeholderCatalog[item.catalog])) {
        expect(pointInPolygon(corner, room!.polygon), `${item.key} corner ${corner} in ${room!.key}`).toBe(true)
      }
    }
  })

  it('has flags that point at elements that exist', () => {
    const flagged = flaggedRefs(sampleGeometry)
    expect(flagged.size).toBe(sampleGeometry.flags.length)
    for (const flag of sampleGeometry.flags) {
      if (flag.element_kind === 'opening') {
        const [wallKey, no] = flag.element_ref.split('/')
        expect(sampleGeometry.openings.some((o) => o.wall === wallKey && o.no === Number(no))).toBe(true)
      }
      if (flag.element_kind === 'item') {
        expect(sampleGeometry.items.some((i) => i.key === flag.element_ref)).toBe(true)
      }
    }
  })
})
