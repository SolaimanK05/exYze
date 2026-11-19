import { useCallback } from 'react'
import { Link, useParams } from 'react-router'
import { getProject } from './api'
import { formatDate } from './format'
import { NotFound } from './NotFound'
import { StatusPill } from './StatusPill'
import { useAsync } from './useAsync'

export function ProjectPage() {
  const projectId = Number(useParams().projectId)
  const loadProject = useCallback(() => getProject(projectId), [projectId])
  const project = useAsync(loadProject)

  if (project.status === 'loading') return <div className="page muted">Loading project…</div>
  if (project.status === 'error') {
    return (
      <div className="page" role="alert">
        <p className="error">The project could not be loaded. {project.message}</p>
      </div>
    )
  }
  if (!project.data) return <NotFound what="project" />

  const { name, siteAddress, floors } = project.data

  return (
    <div className="page">
      <nav aria-label="Breadcrumb" className="crumbs">
        <Link to="/">Projects</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{name}</span>
      </nav>
      <h1>{name}</h1>
      {siteAddress && <p className="muted">{siteAddress}</p>}

      <h2>Floors</h2>
      {floors.length === 0 ? (
        <p className="muted">This project has no floors yet. Add a floor to bring in a plan.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Floor</th>
              <th scope="col" className="num">
                Revision
              </th>
              <th scope="col">Status</th>
              <th scope="col">Last changed</th>
            </tr>
          </thead>
          <tbody>
            {floors.map((floor) => (
              <tr key={floor.id}>
                <td>
                  <Link to={`/projects/${project.data!.id}/floors/${floor.id}`} className="table__link">
                    {floor.name}
                  </Link>
                </td>
                <td className="num">{floor.latestRevision ? floor.latestRevision.revNo : '–'}</td>
                <td>{floor.latestRevision ? <StatusPill state={floor.latestRevision.state} /> : 'No plan yet'}</td>
                <td>{floor.latestRevision ? formatDate(floor.latestRevision.updatedAt) : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
