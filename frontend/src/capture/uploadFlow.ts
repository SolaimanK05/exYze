import { pause } from './pause'
import type { CaptureApi, UploadState, UploadStatus } from './uploadApi'

export type Flow =
  | { phase: 'empty' }
  | { phase: 'chosen'; file: File }
  | { phase: 'uploading'; file: File; progress: number }
  | { phase: 'tracking'; file: File; upload: UploadState }
  | { phase: 'problem'; file: File | null; message: string }

export type FlowEvent =
  | { type: 'picked'; file: File }
  | { type: 'rejected'; message: string }
  | { type: 'upload-started' }
  | { type: 'progress'; fraction: number }
  | { type: 'uploaded'; upload: UploadState }
  | { type: 'status'; upload: UploadState }
  | { type: 'failed'; message: string }
  | { type: 'reset' }

export const startingFlow: Flow = { phase: 'empty' }

export function reduceFlow(flow: Flow, event: FlowEvent): Flow {
  switch (event.type) {
    case 'picked':
      return { phase: 'chosen', file: event.file }
    case 'rejected':
      return { phase: 'problem', file: null, message: event.message }
    case 'upload-started':
      if (flow.phase === 'chosen') return { phase: 'uploading', file: flow.file, progress: 0 }
      if (flow.phase === 'problem' && flow.file) return { phase: 'uploading', file: flow.file, progress: 0 }
      return flow
    case 'progress':
      return flow.phase === 'uploading' ? { ...flow, progress: Math.min(1, Math.max(0, event.fraction)) } : flow
    case 'uploaded':
      return flow.phase === 'uploading' ? { phase: 'tracking', file: flow.file, upload: event.upload } : flow
    case 'status':
      return flow.phase === 'tracking' ? { ...flow, upload: event.upload } : flow
    case 'failed':
      return 'file' in flow ? { phase: 'problem', file: flow.file, message: event.message } : flow
    case 'reset':
      return startingFlow
  }
}

/** Statuses after which the server will not change the upload without the user doing something. */
export function isSettled(status: UploadStatus): boolean {
  return status === 'done' || status === 'failed' || status === 'waiting_user'
}

const POLL_MS = 2000
const MAX_MISSED_POLLS = 3

/**
 * Asks for the upload's status until it settles, passing each answer to onStatus.
 * A few failed requests in a row are tolerated, because phones lose signal for a moment.
 */
export async function followUpload(
  api: CaptureApi,
  first: UploadState,
  onStatus: (upload: UploadState) => void,
  signal: AbortSignal,
  pollMs = POLL_MS,
): Promise<UploadState> {
  let current = first
  let missed = 0
  while (!isSettled(current.status)) {
    await pause(pollMs, signal)
    try {
      current = await api.status(current.uploadId, signal)
      missed = 0
      onStatus(current)
    } catch (err) {
      if (signal.aborted) throw err
      missed += 1
      if (missed >= MAX_MISSED_POLLS) throw err
    }
  }
  return current
}
