import type { RevisionState } from './api'
import { revisionStateLabel } from './format'

export function StatusPill({ state }: { state: RevisionState }) {
  return <span className={`pill pill--${state}`}>{revisionStateLabel[state]}</span>
}
