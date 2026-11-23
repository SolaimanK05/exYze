import { Component, Suspense, lazy, useState } from 'react'
import type { ReactNode } from 'react'
import { Plan2D } from '../editor2d/Plan2D'
import type { Geometry } from '../model/geometry'

const Viewer3D = lazy(() => import('../viewer3d/Viewer3D'))

class ViewerBoundary extends Component<{ children: ReactNode }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed
      ? <p className="floor__view-loading" role="status">Could not open the 3D view. You can switch back to 2D.</p>
      : this.props.children
  }
}

export function PlanViewport({ geometry }: { geometry: Geometry }) {
  const [view, setView] = useState<'2D' | '3D'>('2D')

  return (
    <div className="floor__viewport">
      <div className="floor__view-controls" role="group" aria-label="Plan view">
        <button type="button" aria-pressed={view === '2D'} onClick={() => setView('2D')}>2D</button>
        <button type="button" aria-pressed={view === '3D'} onClick={() => setView('3D')}>3D</button>
      </div>
      <div className="floor__view">
        {view === '2D' ? <Plan2D geometry={geometry} /> : (
          <ViewerBoundary>
            <Suspense fallback={<p className="floor__view-loading">Loading 3D view…</p>}>
              <Viewer3D geometry={geometry} />
            </Suspense>
          </ViewerBoundary>
        )}
      </div>
    </div>
  )
}
