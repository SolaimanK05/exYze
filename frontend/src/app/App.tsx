import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router'
import { Layout } from './Layout'
import { NotFound } from './NotFound'
import { ProjectPage } from './ProjectPage'
import { ProjectsPage } from './ProjectsPage'
import './app.css'

// The floor page pulls in the canvas library, so it loads only when someone opens a plan.
const FloorPage = lazy(() => import('./FloorPage').then((m) => ({ default: m.FloorPage })))
const DxfDemoPage = lazy(() => import('./DxfDemoPage'))
const UploadPage = lazy(() => import('../upload/UploadPage'))

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ProjectsPage />} />
          <Route path="projects/:projectId" element={<ProjectPage />} />
          <Route
            path="projects/:projectId/floors/:floorId"
            element={
              <Suspense fallback={<div className="page muted">Loading plan…</div>}>
                <FloorPage />
              </Suspense>
            }
          />
          <Route
            path="demo/dxf"
            element={
              <Suspense fallback={<div className="page muted">Loading plan…</div>}>
                <DxfDemoPage />
              </Suspense>
            }
          />
          <Route
            path="upload"
            element={
              <Suspense fallback={<div className="page muted">Loading…</div>}>
                <UploadPage />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
