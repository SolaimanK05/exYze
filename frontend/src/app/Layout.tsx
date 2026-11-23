import { Link, Outlet } from 'react-router'

export function Layout() {
  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="shell__bar">
        <Link to="/" className="shell__brand" aria-label="exYze, all projects">
          <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="currentColor" />
            <path d="M7 24V8h18M7 16h11M7 24h18" fill="none" stroke="#17212b" strokeWidth="3" strokeLinecap="square" />
          </svg>
          <span>exYze</span>
        </Link>
      </header>
      <main id="main" className="shell__main">
        <Outlet />
      </main>
    </div>
  )
}
