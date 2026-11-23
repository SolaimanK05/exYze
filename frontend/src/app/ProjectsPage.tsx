import { Link } from 'react-router'
import { listProjects } from './api'
import { formatDate } from './format'
import { useAsync } from './useAsync'

export function ProjectsPage() {
  const projects = useAsync(listProjects)

  return (
    <div className="page">
      <div className="page__head">
        <h1>Projects</h1>
        <Link to="/upload" className="button button--primary">
          Upload a plan
        </Link>
      </div>

      {projects.status === 'loading' && <p className="muted">Loading projects…</p>}
      {projects.status === 'error' && (
        <p role="alert" className="error">
          Projects could not be loaded. {projects.message}
        </p>
      )}
      {projects.status === 'ready' && projects.data.length === 0 && (
        <p className="muted">No projects yet. Create one to bring in a plan.</p>
      )}
      {projects.status === 'ready' && projects.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Project</th>
              <th scope="col">Site</th>
              <th scope="col" className="num">
                Floors
              </th>
              <th scope="col">Last changed</th>
            </tr>
          </thead>
          <tbody>
            {projects.data.map((project) => {
              const changed = project.floors
                .map((f) => f.latestRevision?.updatedAt)
                .filter((d): d is string => Boolean(d))
                .sort()
                .at(-1)
              return (
                <tr key={project.id}>
                  <td>
                    <Link to={`/projects/${project.id}`} className="table__link">
                      {project.name}
                    </Link>
                  </td>
                  <td>{project.siteAddress ?? '–'}</td>
                  <td className="num">{project.floors.length}</td>
                  <td>{changed ? formatDate(changed) : '–'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
