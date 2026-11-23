import type { UploadState } from './uploadApi'

export type Tone = 'info' | 'good' | 'warn' | 'error'

export function describeStatus(upload: UploadState): { text: string; tone: Tone } {
  switch (upload.status) {
    case 'queued':
      return { text: 'Uploaded. Waiting for its turn.', tone: 'info' }
    case 'processing':
      return { text: 'Reading the plan. This can take a minute.', tone: 'info' }
    case 'waiting_user':
      return {
        text: 'We could not find the corners of the paper on our own. Adjusting them by hand is coming next.',
        tone: 'warn',
      }
    case 'done':
      return { text: 'Done. The plan has been imported.', tone: 'good' }
    case 'failed':
      return { text: `The import failed. ${upload.error ?? ''}`.trim(), tone: 'error' }
  }
}
