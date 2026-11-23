import { describe, expect, it } from 'vitest'
import { Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three'
import type { Geometry, Opening } from '../model/geometry'
import { buildScene, toWorld, wallSections } from './geometry'

const door: Opening = { wall: 'w1', no: 1, kind: 'door', offset: 1, width: 1, height: 2, sill: 0 }
const window: Opening = { wall: 7, no: 2, kind: 'window', offset: 2.5, width: 1, height: 1, sill: 1 }
const plan: Geometry = {
  version: 1,
  units: 'm',
  source: 'dxf',
  walls: [{ id: 7, key: 'w1', x1: 4, y1: 2, x2: 0, y2: 2, thickness: 0.25, height: 3 }],
  openings: [door, window],
  rooms: [],
  labels: [],
  items: [],
  flags: [],
  scale: null,
}

describe('3D floor geometry', () => {
  it('uses metres and maps plan y to negative world z', () => {
    expect(toWorld([4, 2], 3)).toEqual([4, 3, -2])
  })

  it('keeps the wall below and above windows and above doors', () => {
    expect(wallSections(4, 3, [window, door])).toEqual([
      { start: 0, end: 1, bottom: 0, top: 3 },
      { start: 1, end: 2, bottom: 2, top: 3 },
      { start: 2, end: 2.5, bottom: 0, top: 3 },
      { start: 2.5, end: 3.5, bottom: 0, top: 1 },
      { start: 2.5, end: 3.5, bottom: 2, top: 3 },
      { start: 3.5, end: 4, bottom: 0, top: 3 },
    ])
  })

  it('subtracts overlapping openings as a single union and clips to the wall', () => {
    const overlapping = { ...window, offset: -1, width: 4, sill: 1, height: 4 }
    expect(wallSections(4, 3, [door, overlapping])).toEqual([
      { start: 0, end: 1, bottom: 0, top: 1 },
      { start: 2, end: 3, bottom: 0, top: 1 },
      { start: 3, end: 4, bottom: 0, top: 3 },
    ])
  })

  it('leaves gaps in the actual merged mesh for key and ID references on a reversed wall', () => {
    const { walls } = buildScene(plan)
    expect(walls).not.toBeNull()
    if (!walls) return

    const mesh = new Mesh(walls, new MeshBasicMaterial())
    const hits = (x: number, height: number) =>
      new Raycaster(new Vector3(x, height, 0), new Vector3(0, 0, -1)).intersectObject(mesh).length
    expect(hits(2.5, 0.5)).toBe(0)
    expect(hits(2.5, 2.5)).toBeGreaterThan(0)
    expect(hits(1, 1.5)).toBe(0)
    expect(hits(1, 0.5)).toBeGreaterThan(0)
    expect(hits(1, 2.5)).toBeGreaterThan(0)
    walls.dispose()
    mesh.material.dispose()
  })

  it('triangulates a concave floor facing up at height zero', () => {
    const room: Geometry['rooms'][number] = {
      key: 'r1', name: 'Living', type: 'living', floor_finish: 2,
      polygon: [[0, 0], [0, 3], [1, 3], [1, 1], [3, 1], [3, 0], [0, 0]],
    }
    const { floors, framing } = buildScene({ ...plan, walls: [], openings: [], rooms: [room] })
    expect(floors).toHaveLength(1)
    expect(floors[0].finish).toBe(2)
    const surface = floors[0].surface
    const mesh = new Mesh(surface, new MeshBasicMaterial())
    const ray = (x: number, y: number) =>
      new Raycaster(new Vector3(x, 1, -y), new Vector3(0, -1, 0)).intersectObject(mesh)
    expect(ray(0.5, 2)[0].point.y).toBeCloseTo(0)
    expect(ray(2, 2)).toHaveLength(0)
    expect(framing.center.toArray()).toEqual([1.5, expect.closeTo(0), -1.5])
    surface.dispose()
    mesh.material.dispose()
  })

  it('accepts empty geometry and ignores a zero-length wall', () => {
    const { walls, floors } = buildScene({
      ...plan, walls: [{ ...plan.walls[0], x2: 4 }],
    })
    expect(walls).toBeNull()
    expect(floors).toHaveLength(0)
  })
})
