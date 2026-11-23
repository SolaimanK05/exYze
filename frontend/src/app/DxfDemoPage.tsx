import { Link } from 'react-router'
import type { Geometry } from '../model/geometry'
import parsedPlan from '../model/demo/plan01.json'
import { PlanViewport } from './PlanViewport'

const geometry = parsedPlan as Geometry

export default function DxfDemoPage() {
  return (
    <div className="floor">
      <div className="floor__head">
        <h1>plan01.dxf</h1>
        <Link to="/projects/1/floors/1">Open sample floor</Link>
      </div>
      <div className="floor__body">
        <div className="floor__canvas">
          <PlanViewport geometry={geometry} />
        </div>
        <aside className="floor__panel" aria-label="DXF details">
          <section>
            <h2>Parsed plan</h2>
            <dl className="facts">
              <dt>Provisional walls</dt>
              <dd>{geometry.walls.length}</dd>
              <dt>Room labels</dt>
              <dd>{geometry.labels.length}</dd>
            </dl>
          </section>
          <section>
            <h2>Needs review</h2>
            <ul className="flags">
              {geometry.flags.map((flag) => (
                <li key={flag.element_ref}>{flag.reason}</li>
              ))}
              <li>Open the sample floor to see room floors and door and window openings.</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  )
}
