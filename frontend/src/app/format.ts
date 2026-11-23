import type { RevisionState } from './api'

const dateFormat = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

/** 2026-11-17 becomes 17 Nov 2026. */
export function formatDate(isoDate: string): string {
  return dateFormat.format(new Date(`${isoDate}T00:00:00`))
}

export const revisionStateLabel: Record<RevisionState, string> = {
  draft: 'Draft',
  in_review: 'In review',
  approved: 'Approved',
}
