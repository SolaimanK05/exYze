import { Link } from 'react-router'

export function NotFound({ what = 'page' }: { what?: string }) {
  return (
    <div className="page">
      <h1>This {what} does not exist</h1>
      <p className="muted">It may have been removed, or the link is wrong.</p>
      <p>
        <Link to="/">Back to projects</Link>
      </p>
    </div>
  )
}
