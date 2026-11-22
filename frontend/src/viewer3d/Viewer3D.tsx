import { useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei/core/OrbitControls.js'
import { PerspectiveCamera, Vector3 } from 'three'
import type { Sphere } from 'three'
import type { Geometry } from '../model/geometry'
import { buildScene } from './geometry'
import './viewer3d.css'

// Geometry v1 sends finish IDs. Use a consistent color for each ID until finish styles are supplied.
const finishColors = ['#c7d9c6', '#d8bead', '#c8c6df', '#bbd3da', '#e3d3a6']

function CameraControls({ framing, reset }: { framing: Sphere; reset: number }) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const { get, size, invalidate } = useThree()
  const radius = Math.max(1, framing.radius)

  useEffect(() => {
    const { camera } = get()
    if (!(camera instanceof PerspectiveCamera) || !controls.current || !size.height || !size.width) return

    const verticalHalfFov = camera.getEffectiveFOV() * Math.PI / 360
    const horizontalHalfFov = Math.atan(Math.tan(verticalHalfFov) * size.width / size.height)
    const distance = radius / Math.sin(Math.min(verticalHalfFov, horizontalHalfFov)) * 1.08
    const direction = new Vector3(1, 1, 1.2).normalize()
    camera.position.copy(framing.center).addScaledVector(direction, distance)
    camera.near = Math.max(0.005, radius / 1_000)
    camera.far = Math.max(100, distance * 3, radius * 40)
    camera.updateProjectionMatrix()

    controls.current.target.copy(framing.center)
    controls.current.maxDistance = Math.max(distance * 1.5, radius * 12)
    controls.current.update()
    invalidate()
  }, [framing, get, invalidate, radius, reset, size.height, size.width])

  return (
    <OrbitControls
      ref={controls}
      enableDamping={false}
      minDistance={radius * 0.04}
      maxPolarAngle={Math.PI / 2 - 0.02}
      makeDefault
    />
  )
}

export default function Viewer3D({ geometry }: { geometry: Geometry }) {
  const { walls, floors, framing } = useMemo(() => buildScene(geometry), [geometry])
  const [reset, setReset] = useState(0)
  const groundSize = Math.max(8, framing.radius * 4)

  useEffect(() => () => {
    walls?.dispose()
    for (const { surface } of floors) surface.dispose()
  }, [walls, floors])

  if (!walls && !floors.length) return <p className="viewer3d__status">This plan has no walls or room floors to display.</p>

  return (
    <div className="viewer3d">
      <Canvas
        aria-label="3D floor plan"
        camera={{ fov: 42 }}
        dpr={[1, 1.5]}
        frameloop="demand"
        fallback={<p className="viewer3d__status">WebGL is unavailable. Open the 2D plan to see this floor.</p>}
      >
        <color attach="background" args={['#e7edf2']} />
        <hemisphereLight args={['#f5f8ff', '#9f9b91', 2]} />
        <directionalLight position={[4, 9, 6]} intensity={2} />

        <mesh position={[framing.center.x, -0.015, framing.center.z]} rotation-x={-Math.PI / 2}>
          <planeGeometry args={[groundSize, groundSize]} />
          <meshStandardMaterial color="#adbcc8" />
        </mesh>
        {floors.map(({ finish, surface }) => (
          <mesh key={finish ?? 'default'} geometry={surface}>
            <meshStandardMaterial color={finish === null ? '#dbcaad' : finishColors[Math.abs(finish) % finishColors.length]} />
          </mesh>
        ))}
        {walls && (
          <mesh geometry={walls}>
            <meshStandardMaterial color="#7892aa" />
          </mesh>
        )}
        <CameraControls framing={framing} reset={reset} />
      </Canvas>
      <button className="viewer3d__reset" type="button" onClick={() => setReset((value) => value + 1)}>
        Reset view
      </button>
    </div>
  )
}
