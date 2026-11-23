// The app's view of the backend. Every function here returns placeholder data for now.
// Replace each body with a fetch() to the endpoint named above it once Package D's API is ready
// (see "API endpoints" in 01 Architecture and Contracts). The pages already treat these as async.

import type { Geometry } from '../model/geometry'
import { sampleGeometry } from '../model/sampleGeometry'

export type RevisionState = 'draft' | 'in_review' | 'approved'

export interface RevisionSummary {
  revNo: number
  state: RevisionState
  /** An ISO date, for example 2026-11-17. */
  updatedAt: string
}

export interface FloorSummary {
  id: number
  levelNo: number
  name: string
  latestRevision: RevisionSummary | null
}

export interface ProjectSummary {
  id: number
  name: string
  siteAddress: string | null
  floors: FloorSummary[]
}

const projects: ProjectSummary[] = [
  {
    id: 1,
    name: 'Dhanmondi Flat',
    siteAddress: 'Road 27, Dhanmondi, Dhaka',
    floors: [{ id: 1, levelNo: 1, name: 'Floor 1', latestRevision: { revNo: 3, state: 'draft', updatedAt: '2026-11-17' } }],
  },
  {
    id: 2,
    name: 'Bashundhara Duplex',
    siteAddress: 'Block D, Bashundhara R/A, Dhaka',
    floors: [
      { id: 2, levelNo: 1, name: 'Ground floor', latestRevision: { revNo: 5, state: 'approved', updatedAt: '2026-11-12' } },
      { id: 3, levelNo: 2, name: 'First floor', latestRevision: { revNo: 2, state: 'in_review', updatedAt: '2026-11-15' } },
    ],
  },
]

/** GET /api/projects */
export async function listProjects(): Promise<ProjectSummary[]> {
  return projects
}

/** GET /api/projects/{id} */
export async function getProject(projectId: number): Promise<ProjectSummary | null> {
  return projects.find((p) => p.id === projectId) ?? null
}

/** GET /api/floors/{id}, then GET /api/revisions/{id} for the latest revision's geometry. */
export async function getFloorWithGeometry(
  projectId: number,
  floorId: number,
): Promise<{ project: ProjectSummary; floor: FloorSummary; geometry: Geometry } | null> {
  const project = projects.find((p) => p.id === projectId)
  const floor = project?.floors.find((f) => f.id === floorId)
  if (!project || !floor) return null
  return { project, floor, geometry: sampleGeometry }
}
