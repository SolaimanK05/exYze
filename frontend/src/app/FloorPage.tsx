import { useCallback } from 'react'
import { Link, useParams } from 'react-router'
import { Plan2D } from '../editor2d/Plan2D'
import { footprintFor } from '../editor2d/placeholderCatalog'
import type { Geometry } from '../model/geometry'
import { getFloorWithGeometry } from './api'
import { formatDate } from './format'
import { NotFound } from './NotFound'
import { StatusPill } from './StatusPill'
import { useAsync } from './useAsync'

function PlanSummary({ geometry }: { geometry: Geometry }) {
  const doors = geometry.openings.filter((o) => o.kind === 'door').length
  const windows = geometry.openings.length - doors
  return (
    <section aria-labelledby="summary-title">
      <h2 id="summary-title">Plan</h2>
      <dl className="facts">
        <dt>Rooms</dt>
        <dd>{geometry.rooms.length}</dd>
        <dt>Walls</dt>
        <dd>{geometry.walls.length}</dd>
        <dt>Doors</dt>
        <dd>{doors}</dd>
        <dt>Windows</dt>
        <dd>{windows}</dd>
        <dt>Furniture</dt>
        <dd>{geometry.items.length}</dd>
      </dl>
    </section>
  )
}

function ReviewList({ geometry }: { geometry: Geometry }) {
  return (
    <section aria-labelledby="review-title">
      <h2 id="review-title">Needs review</h2>
      {geometry.flags.length === 0 ? (
        <p className="muted">Nothing to review.</p>
      ) : (
        <ul className="flags">
          {geometry.flags.map((flag) => {
            const item = flag.element_kind === 'item' ? geometry.items.find((i) => i.key === flag.element_ref) : undefined
            const subject =
              flag.element_kind === 'opening'
                ? `Opening ${flag.element_ref}`
                : item
                  ? footprintFor(item.catalog).name
                  : flag.element_ref
            return (
              <li key={`${flag.element_kind}:${flag.element_ref}`}>
                <span className="flags__subject">{subject}</span>
                <span className="muted">{flag.reason}</span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export function FloorPage() {
  const params = useParams()
  const projectId = Number(params.projectId)
  const floorId = Number(params.floorId)
  const loadFloor = useCallback(() => getFloorWithGeometry(projectId, floorId), [projectId, floorId])
  const loaded = useAsync(loadFloor)

  if (loaded.status === 'loading') return <div className="page muted">Loading plan…</div>
  if (loaded.status === 'error') {
    return (
      <div className="page" role="alert">
        <p className="error">The plan could not be loaded. {loaded.message}</p>
      </div>
    )
  }
  if (!loaded.data) return <NotFound what="floor" />

  const { project, floor, geometry } = loaded.data

  return (
    <div className="floor">
      <div className="floor__head">
        <nav aria-label="Breadcrumb" className="crumbs">
          <Link to="/">Projects</Link>
          <span aria-hidden="true">/</span>
          <Link to={`/projects/${project.id}`}>{project.name}</Link>
          <span aria-hidden="true">/</span>
          <span aria-current="page">{floor.name}</span>
        </nav>
        {floor.latestRevision && (
          <p className="floor__revision">
            Revision {floor.latestRevision.revNo} <StatusPill state={floor.latestRevision.state} />
            <span className="muted">Changed {formatDate(floor.latestRevision.updatedAt)}</span>
          </p>
        )}
      </div>

      <div className="floor__body">
        <div className="floor__canvas">
          <Plan2D geometry={geometry} />
        </div>
        <aside className="floor__panel" aria-label="Plan details">
          <PlanSummary geometry={geometry} />
          <ReviewList geometry={geometry} />
          <p className="muted floor__note">This is a sample plan. The page shows the real revision once the API is connected.</p>
        </aside>
      </div>
    </div>
  )
}
