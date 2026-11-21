import type { Geometry } from './geometry'

// A small two-bedroom flat in the geometry format, 9 m by 7 m.
// It stands in for a real revision until the API (Package D) and the DXF parser (Package A) are connected.
// Walls run along the centre lines below. The corridor is between w5 and w7.

export const sampleGeometry: Geometry = {
  version: 1,
  units: 'm',
  source: 'dxf',
  walls: [
    { key: 'w1', x1: 0, y1: 0, x2: 9, y2: 0, thickness: 0.25, height: 3, exterior: true, confidence: 1 },
    { key: 'w2', x1: 9, y1: 0, x2: 9, y2: 7, thickness: 0.25, height: 3, exterior: true, confidence: 1 },
    { key: 'w3', x1: 9, y1: 7, x2: 0, y2: 7, thickness: 0.25, height: 3, exterior: true, confidence: 1 },
    { key: 'w4', x1: 0, y1: 7, x2: 0, y2: 0, thickness: 0.25, height: 3, exterior: true, confidence: 1 },
    { key: 'w5', x1: 0, y1: 3.5, x2: 9, y2: 3.5, thickness: 0.125, height: 3, exterior: false, confidence: 1 },
    { key: 'w6', x1: 5.5, y1: 0, x2: 5.5, y2: 3.5, thickness: 0.125, height: 3, exterior: false, confidence: 1 },
    { key: 'w7', x1: 0, y1: 4.7, x2: 9, y2: 4.7, thickness: 0.125, height: 3, exterior: false, confidence: 1 },
    { key: 'w8', x1: 3.5, y1: 4.7, x2: 3.5, y2: 7, thickness: 0.125, height: 3, exterior: false, confidence: 1 },
    { key: 'w9', x1: 5.5, y1: 4.7, x2: 5.5, y2: 7, thickness: 0.125, height: 3, exterior: false, confidence: 1 },
  ],
  openings: [
    // Entrance, from the stairs into the corridor.
    { wall: 'w4', no: 1, kind: 'door', offset: 2.45, width: 0.9, height: 2.1, sill: 0, confidence: 0.98 },
    // Corridor to living room, kitchen and the three rooms on the north side.
    { wall: 'w5', no: 1, kind: 'door', offset: 2.0, width: 0.9, height: 2.1, sill: 0, confidence: 0.95 },
    { wall: 'w5', no: 2, kind: 'door', offset: 6.5, width: 0.9, height: 2.1, sill: 0, confidence: 0.55 },
    { wall: 'w7', no: 1, kind: 'door', offset: 2.4, width: 0.9, height: 2.1, sill: 0, confidence: 0.96 },
    { wall: 'w7', no: 2, kind: 'door', offset: 4.1, width: 0.8, height: 2.1, sill: 0, confidence: 0.94 },
    { wall: 'w7', no: 3, kind: 'door', offset: 7.0, width: 0.9, height: 2.1, sill: 0, confidence: 0.97 },
    // Living room to kitchen.
    { wall: 'w6', no: 1, kind: 'door', offset: 1.2, width: 1.0, height: 2.1, sill: 0, confidence: 0.93 },
    // Windows, south wall.
    { wall: 'w1', no: 1, kind: 'window', offset: 1.2, width: 1.8, height: 1.2, sill: 0.9, confidence: 0.99 },
    { wall: 'w1', no: 2, kind: 'window', offset: 3.6, width: 1.2, height: 1.2, sill: 0.9, confidence: 0.99 },
    { wall: 'w1', no: 3, kind: 'window', offset: 6.6, width: 1.4, height: 1.2, sill: 0.9, confidence: 0.98 },
    // Windows, east wall.
    { wall: 'w2', no: 1, kind: 'window', offset: 1.0, width: 1.2, height: 1.2, sill: 0.9, confidence: 0.97 },
    { wall: 'w2', no: 2, kind: 'window', offset: 5.0, width: 1.5, height: 1.2, sill: 0.9, confidence: 0.98 },
    // Windows, north wall (this wall runs from x = 9 to x = 0, so offsets count from the east).
    { wall: 'w3', no: 1, kind: 'window', offset: 0.6, width: 1.4, height: 1.2, sill: 0.9, confidence: 0.98 },
    { wall: 'w3', no: 2, kind: 'window', offset: 4.0, width: 0.8, height: 0.8, sill: 1.4, confidence: 0.96 },
    { wall: 'w3', no: 3, kind: 'window', offset: 7.1, width: 1.3, height: 1.2, sill: 0.9, confidence: 0.97 },
    // Windows, west wall (this wall runs from y = 7 to y = 0, so offsets count from the north).
    { wall: 'w4', no: 2, kind: 'window', offset: 0.8, width: 1.2, height: 1.2, sill: 0.9, confidence: 0.98 },
    { wall: 'w4', no: 3, kind: 'window', offset: 4.0, width: 1.5, height: 1.2, sill: 0.9, confidence: 0.98 },
  ],
  rooms: [
    { key: 'r1', name: 'Living room', type: 'living', polygon: [[0, 0], [5.5, 0], [5.5, 3.5], [0, 3.5]] },
    { key: 'r2', name: 'Kitchen', type: 'kitchen', polygon: [[5.5, 0], [9, 0], [9, 3.5], [5.5, 3.5]] },
    { key: 'r3', name: 'Corridor', type: 'corridor', polygon: [[0, 3.5], [9, 3.5], [9, 4.7], [0, 4.7]] },
    { key: 'r4', name: 'Bedroom 1', type: 'bedroom', polygon: [[0, 4.7], [3.5, 4.7], [3.5, 7], [0, 7]] },
    { key: 'r5', name: 'Bathroom', type: 'bathroom', polygon: [[3.5, 4.7], [5.5, 4.7], [5.5, 7], [3.5, 7]] },
    { key: 'r6', name: 'Bedroom 2', type: 'bedroom', polygon: [[5.5, 4.7], [9, 4.7], [9, 7], [5.5, 7]] },
  ],
  labels: [
    { text: 'LIVING', x: 2.75, y: 1.75 },
    { text: 'KITCHEN', x: 7.25, y: 1.75 },
    { text: 'BED 1', x: 1.75, y: 5.85 },
    { text: 'BATH', x: 4.5, y: 5.85 },
    { text: 'BED 2', x: 7.25, y: 5.85 },
  ],
  items: [
    { key: 'i1', catalog: 'sofa_3', room: 'r1', x: 2.7, y: 0.8, rotation: 0, confidence: 0.9 },
    { key: 'i2', catalog: 'tv_unit', room: 'r1', x: 2.7, y: 3.2, rotation: 0, confidence: 0.85 },
    { key: 'i3', catalog: 'dining_table_4', room: 'r1', x: 4.4, y: 1.9, rotation: 0, confidence: 0.8 },
    { key: 'i4', catalog: 'kitchen_counter', room: 'r2', x: 7.4, y: 0.5, rotation: 0, confidence: 0.9 },
    { key: 'i5', catalog: 'fridge', room: 'r2', x: 8.45, y: 3.05, rotation: 0, confidence: 0.45 },
    { key: 'i6', catalog: 'bed_double', room: 'r4', x: 1.15, y: 6.0, rotation: 90, confidence: 0.92 },
    { key: 'i7', catalog: 'wardrobe', room: 'r4', x: 2.8, y: 6.55, rotation: 0, confidence: 0.9 },
    { key: 'i8', catalog: 'toilet', room: 'r5', x: 4.0, y: 6.45, rotation: 0, confidence: 0.9 },
    { key: 'i9', catalog: 'basin', room: 'r5', x: 5.0, y: 6.6, rotation: 0, confidence: 0.9 },
    { key: 'i10', catalog: 'shower_tray', room: 'r5', x: 4.9, y: 5.3, rotation: 0, confidence: 0.88 },
    { key: 'i11', catalog: 'bed_double', room: 'r6', x: 7.6, y: 5.85, rotation: 0, confidence: 0.93 },
    { key: 'i12', catalog: 'wardrobe', room: 'r6', x: 6.3, y: 6.55, rotation: 0, confidence: 0.9 },
  ],
  flags: [
    { element_kind: 'opening', element_ref: 'w5/2', reason: 'Door with low confidence' },
    { element_kind: 'item', element_ref: 'i5', reason: 'Furniture type is uncertain' },
  ],
  scale: null,
}
