import type { KonvaEventObject } from 'konva/lib/Node'
import type { Stage as KonvaStage } from 'konva/lib/Stage'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { Circle, Group, Layer, Line, Path, Rect, Stage, Text } from 'react-konva'
import type { Geometry, Point, RoomType } from '../model/geometry'
import { findWall, openingRef } from '../model/geometry'
import {
  MAX_SCALE,
  MIN_SCALE,
  doorSymbol,
  fitView,
  flaggedRefs,
  geometryBounds,
  itemCorners,
  openingCentre,
  openingRect,
  polygonCentroid,
  scaleBar,
  wallSolidQuads,
  zoomAt,
} from './draw'
import type { Bounds, View } from './draw'
import { footprintFor } from './placeholderCatalog'
import './plan2d.css'

// Konva paints on a canvas, so the colours are written out here. They match the tokens in index.css.
const COLOR = {
  wall: '#17212b',
  line: '#17212b',
  lineSoft: '#5b6875',
  grid: '#e6eaee',
  furnitureStroke: '#8593a0',
  furnitureFill: '#ffffff',
  flag: '#b86e00',
  roomName: '#4a5866',
  furnitureName: '#66737f',
}

const ROOM_FILL: Record<RoomType, string> = {
  bedroom: '#e5ebf3',
  living: '#e9f0e6',
  kitchen: '#f3ecdd',
  bathroom: '#e0eef0',
  dining: '#eee8f1',
  corridor: '#f0f0ed',
  balcony: '#e6efe2',
  store: '#ece9e4',
  other: '#eeeeee',
}

const ZOOM_STEP = 1.25
const GRID_MIN_SCALE = 14 // pixels per metre; below this the 1 m grid is too dense to be useful

function flat(points: readonly Point[]): number[] {
  return points.flat()
}

interface Box {
  left: number
  top: number
  right: number
  bottom: number
}

/** A rough box around a line of text centred on (x, y), from the width of one character. */
function textBox(x: number, y: number, text: string, charWidth: number, height: number): Box {
  const half = (text.length * charWidth) / 2 + 4
  return { left: x - half, right: x + half, top: y - height / 2, bottom: y + height / 2 }
}

function boxesOverlap(a: Box, b: Box): boolean {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom
}

function useElementSize(ref: RefObject<HTMLElement | null>) {
  const [size, setSize] = useState({ width: 0, height: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight })
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref])
  return size
}

interface Plan2DProps {
  geometry: Geometry
}

/**
 * The read-only 2D view of a revision's geometry. Pan by dragging, zoom with the wheel,
 * the buttons or a two-finger pinch. Editing tools come in Sprint 3.
 */
export function Plan2D({ geometry }: Plan2DProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<KonvaStage>(null)
  const size = useElementSize(containerRef)
  const hasSize = size.width > 0 && size.height > 0

  const bounds = useMemo(() => geometryBounds(geometry), [geometry])
  const flagged = useMemo(() => flaggedRefs(geometry), [geometry])
  const [view, setView] = useState<View>({ scale: 40, offsetX: 0, offsetY: 0 })

  // The whole plan stays fitted to the window until the person pans or zooms, so a window that is still
  // settling its size does not leave the plan off-centre. A different plan always starts fitted.
  const interacted = useRef(false)
  const fittedFor = useRef<Bounds | null | undefined>(undefined)
  useEffect(() => {
    if (!hasSize) return
    if (interacted.current && fittedFor.current === bounds) return
    fittedFor.current = bounds
    interacted.current = false
    setView(fitView(bounds, size))
  }, [bounds, hasSize, size])

  const fit = useCallback(() => {
    interacted.current = false
    setView(fitView(bounds, size))
  }, [bounds, size])
  const zoomFromCentre = useCallback(
    (factor: number) => {
      interacted.current = true
      setView((v) => zoomAt(v, [size.width / 2, size.height / 2], factor))
    },
    [size.width, size.height],
  )

  const onWheel = useCallback((e: KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault()
    const pointer = e.target.getStage()?.getPointerPosition()
    if (!pointer) return
    interacted.current = true
    const factor = Math.exp(-e.evt.deltaY * 0.0015)
    setView((v) => zoomAt(v, [pointer.x, pointer.y], factor))
  }, [])

  const onDragEnd = useCallback((e: KonvaEventObject<DragEvent>) => {
    if (e.target !== e.target.getStage()) return
    interacted.current = true
    const { x, y } = e.target.position()
    setView((v) => ({ ...v, offsetX: x, offsetY: y }))
  }, [])

  // Two-finger pinch: zoom around the middle of the two fingers and follow it as it moves.
  const pinch = useRef<{ distance: number; centre: Point } | null>(null)
  const onTouchMove = useCallback((e: KonvaEventObject<TouchEvent>) => {
    const touches = e.evt.touches
    const box = containerRef.current?.getBoundingClientRect()
    if (touches.length !== 2 || !box) return
    e.evt.preventDefault()
    interacted.current = true
    stageRef.current?.stopDrag()
    const a: Point = [touches[0].clientX - box.left, touches[0].clientY - box.top]
    const b: Point = [touches[1].clientX - box.left, touches[1].clientY - box.top]
    const centre: Point = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]
    const distance = Math.hypot(a[0] - b[0], a[1] - b[1])
    const last = pinch.current
    pinch.current = { distance, centre }
    if (!last || last.distance === 0) return
    setView((v) => {
      const zoomed = zoomAt(v, centre, distance / last.distance)
      return {
        ...zoomed,
        offsetX: zoomed.offsetX + (centre[0] - last.centre[0]),
        offsetY: zoomed.offsetY + (centre[1] - last.centre[1]),
      }
    })
  }, [])
  const onTouchEnd = useCallback(() => {
    pinch.current = null
  }, [])

  const { scale } = view
  const bar = scaleBar(scale)

  // Positions on the text layer are in pixels, relative to the stage, with y pointing down.
  const toPixels = ([x, y]: Point): Point => [x * scale, -y * scale]

  const gridLines = useMemo(() => {
    if (!bounds || scale < GRID_MIN_SCALE) return []
    const lines: number[][] = []
    const x0 = Math.floor(bounds.minX) - 1
    const x1 = Math.ceil(bounds.maxX) + 1
    const y0 = Math.floor(bounds.minY) - 1
    const y1 = Math.ceil(bounds.maxY) + 1
    for (let x = x0; x <= x1; x++) lines.push([x, y0, x, y1])
    for (let y = y0; y <= y1; y++) lines.push([x0, y, x1, y])
    return lines
  }, [bounds, scale])

  // Names are drawn only where they fit, and a furniture name steps aside for a room name it would touch.
  const roomLabels = geometry.rooms.flatMap((room) => {
    const xs = room.polygon.map((p) => p[0])
    const ys = room.polygon.map((p) => p[1])
    const pixelsWide = (Math.max(...xs) - Math.min(...xs)) * scale
    const pixelsHigh = (Math.max(...ys) - Math.min(...ys)) * scale
    if (Math.min(pixelsWide, pixelsHigh) < 44 || pixelsWide < 70) return []
    const [x, y] = toPixels(polygonCentroid(room.polygon))
    return [{ key: room.key, text: room.name, x, y, box: textBox(x, y, room.name, 7.6, 18) }]
  })
  const itemLabels = geometry.items.flatMap((item) => {
    const footprint = footprintFor(item.catalog)
    const corners = itemCorners(item, footprint).map(toPixels)
    const xs = corners.map((c) => c[0])
    const ys = corners.map((c) => c[1])
    const pixelsWide = Math.max(...xs) - Math.min(...xs)
    const pixelsHigh = Math.max(...ys) - Math.min(...ys)
    if (pixelsWide < 64 || pixelsHigh < 26) return []
    const x = (Math.min(...xs) + Math.max(...xs)) / 2
    const y = (Math.min(...ys) + Math.max(...ys)) / 2
    const box = textBox(x, y, footprint.name, 6.2, 14)
    if (roomLabels.some((r) => boxesOverlap(r.box, box))) return []
    return [{ key: item.key, text: footprint.name, x, y }]
  })

  const description = `Floor plan with ${geometry.rooms.length} rooms, ${geometry.walls.length} walls and ${geometry.openings.length} doors and windows`

  return (
    <div className="plan2d" ref={containerRef} role="img" aria-label={description}>
      {hasSize && (
        <Stage
          ref={stageRef}
          width={size.width}
          height={size.height}
          x={view.offsetX}
          y={view.offsetY}
          draggable
          onWheel={onWheel}
          onDragEnd={onDragEnd}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          {/* Plan layer: plan coordinates in metres, with the y axis flipped so that y points up. */}
          <Layer listening={false}>
            <Group scaleX={scale} scaleY={-scale}>
              {gridLines.map((points, i) => (
                <Line key={i} points={points} stroke={COLOR.grid} strokeWidth={1} strokeScaleEnabled={false} />
              ))}

              {geometry.rooms.map((room) => (
                <Line key={room.key} points={flat(room.polygon)} closed fill={ROOM_FILL[room.type] ?? ROOM_FILL.other} />
              ))}

              {geometry.items.map((item) => {
                const footprint = footprintFor(item.catalog)
                const isFlagged = flagged.has(`item:${item.key}`)
                return (
                  <Rect
                    key={item.key}
                    x={item.x}
                    y={item.y}
                    width={footprint.width}
                    height={footprint.depth}
                    offsetX={footprint.width / 2}
                    offsetY={footprint.depth / 2}
                    rotation={item.rotation}
                    fill={COLOR.furnitureFill}
                    opacity={0.85}
                    stroke={isFlagged ? COLOR.flag : COLOR.furnitureStroke}
                    strokeWidth={isFlagged ? 2 : 1}
                    strokeScaleEnabled={false}
                  />
                )
              })}

              {geometry.walls.map((wall) => {
                const openings = geometry.openings.filter((o) => findWall([wall], o.wall))
                return wallSolidQuads(wall, openings).map((quad, i) => (
                  <Line
                    key={`${wall.key}-${i}`}
                    points={flat(quad)}
                    closed
                    fill={COLOR.wall}
                    stroke={COLOR.wall}
                    strokeWidth={0.5}
                    strokeScaleEnabled={false}
                  />
                ))
              })}

              {geometry.openings.map((opening) => {
                const wall = findWall(geometry.walls, opening.wall)
                if (!wall) return null
                const key = `${wall.key}-${opening.no}`
                const isFlagged = flagged.has(`opening:${openingRef(wall, opening)}`)
                const centre = openingCentre(wall, opening)
                const marker = isFlagged ? (
                  <Circle
                    x={centre[0]}
                    y={centre[1]}
                    radius={Math.max(opening.width * 0.75, 0.45)}
                    stroke={COLOR.flag}
                    strokeWidth={2}
                    strokeScaleEnabled={false}
                  />
                ) : null

                if (opening.kind === 'window') {
                  const [c0, c1, c2, c3] = openingRect(wall, opening)
                  const mid0: Point = [(c0[0] + c3[0]) / 2, (c0[1] + c3[1]) / 2]
                  const mid1: Point = [(c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2]
                  return (
                    <Group key={key}>
                      <Line points={flat([c0, c1])} stroke={COLOR.line} strokeWidth={1} strokeScaleEnabled={false} />
                      <Line points={flat([mid0, mid1])} stroke={COLOR.line} strokeWidth={1} strokeScaleEnabled={false} />
                      <Line points={flat([c3, c2])} stroke={COLOR.line} strokeWidth={1} strokeScaleEnabled={false} />
                      {marker}
                    </Group>
                  )
                }

                const door = doorSymbol(wall, opening)
                const arc = `M ${door.closedEnd[0]} ${door.closedEnd[1]} A ${door.radius} ${door.radius} 0 0 1 ${door.leafEnd[0]} ${door.leafEnd[1]}`
                return (
                  <Group key={key}>
                    <Line
                      points={flat([door.hinge, door.leafEnd])}
                      stroke={COLOR.line}
                      strokeWidth={1.5}
                      strokeScaleEnabled={false}
                    />
                    <Path data={arc} stroke={COLOR.lineSoft} strokeWidth={1} strokeScaleEnabled={false} />
                    {marker}
                  </Group>
                )
              })}
            </Group>
          </Layer>

          {/* Text layer: upright text at pixel positions, so it is not flipped by the plan's y axis. */}
          <Layer listening={false}>
            {roomLabels.map((label) => (
              <Text
                key={label.key}
                text={label.text}
                x={label.x - 90}
                y={label.y - 8}
                width={180}
                align="center"
                fontFamily="IBM Plex Sans, system-ui, sans-serif"
                fontSize={13}
                fontStyle="500"
                fill={COLOR.roomName}
              />
            ))}
            {itemLabels.map((label) => (
              <Text
                key={label.key}
                text={label.text}
                x={label.x - 60}
                y={label.y - 6}
                width={120}
                align="center"
                fontFamily="IBM Plex Sans, system-ui, sans-serif"
                fontSize={11}
                fill={COLOR.furnitureName}
              />
            ))}
          </Layer>
        </Stage>
      )}

      <div className="plan2d__controls" role="group" aria-label="View controls">
        <button type="button" onClick={() => zoomFromCentre(ZOOM_STEP)} disabled={scale >= MAX_SCALE} aria-label="Zoom in">
          +
        </button>
        <button type="button" onClick={() => zoomFromCentre(1 / ZOOM_STEP)} disabled={scale <= MIN_SCALE} aria-label="Zoom out">
          −
        </button>
        <button type="button" onClick={fit} className="plan2d__fit">
          Fit to screen
        </button>
      </div>

      <div className="plan2d__scalebar" aria-hidden="true">
        <div className="plan2d__scalebar-line" style={{ width: bar.px }} />
        <span>{bar.metres} m</span>
      </div>
    </div>
  )
}
