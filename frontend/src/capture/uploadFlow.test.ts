import { describe, expect, it } from 'vitest'
import { describeStatus } from './statusText'
import type { CaptureApi, UploadState, UploadStatus } from './uploadApi'
import { followUpload, isSettled, reduceFlow, startingFlow } from './uploadFlow'
import type { Flow } from './uploadFlow'

const photo = new File(['x'], 'plan.jpg', { type: 'image/jpeg' })
const state = (status: UploadStatus, error: string | null = null): UploadState => ({ uploadId: 7, status, error })

describe('reduceFlow', () => {
  it('walks from picking a photo to a finished import', () => {
    let flow: Flow = startingFlow
    flow = reduceFlow(flow, { type: 'picked', file: photo })
    expect(flow).toEqual({ phase: 'chosen', file: photo })

    flow = reduceFlow(flow, { type: 'upload-started' })
    flow = reduceFlow(flow, { type: 'progress', fraction: 0.4 })
    expect(flow).toEqual({ phase: 'uploading', file: photo, progress: 0.4 })

    flow = reduceFlow(flow, { type: 'uploaded', upload: state('queued') })
    flow = reduceFlow(flow, { type: 'status', upload: state('done') })
    expect(flow).toEqual({ phase: 'tracking', file: photo, upload: state('done') })
  })

  it('keeps progress between 0 and 1', () => {
    const uploading = reduceFlow(reduceFlow(startingFlow, { type: 'picked', file: photo }), { type: 'upload-started' })
    expect(reduceFlow(uploading, { type: 'progress', fraction: 1.2 })).toMatchObject({ progress: 1 })
    expect(reduceFlow(uploading, { type: 'progress', fraction: -0.1 })).toMatchObject({ progress: 0 })
  })

  it('ignores progress and status events that arrive in the wrong phase', () => {
    const chosen = reduceFlow(startingFlow, { type: 'picked', file: photo })
    expect(reduceFlow(chosen, { type: 'progress', fraction: 0.5 })).toBe(chosen)
    expect(reduceFlow(chosen, { type: 'status', upload: state('done') })).toBe(chosen)
    expect(reduceFlow(startingFlow, { type: 'upload-started' })).toBe(startingFlow)
  })

  it('keeps the photo after a failed upload so it can be sent again', () => {
    const uploading = reduceFlow(reduceFlow(startingFlow, { type: 'picked', file: photo }), { type: 'upload-started' })
    const failed = reduceFlow(uploading, { type: 'failed', message: 'No signal' })
    expect(failed).toEqual({ phase: 'problem', file: photo, message: 'No signal' })
    expect(reduceFlow(failed, { type: 'upload-started' })).toMatchObject({ phase: 'uploading', file: photo })
  })

  it('shows a rejected file as a problem without a photo to upload', () => {
    const flow = reduceFlow(startingFlow, { type: 'rejected', message: 'Not a photo' })
    expect(flow).toEqual({ phase: 'problem', file: null, message: 'Not a photo' })
    expect(reduceFlow(flow, { type: 'upload-started' })).toBe(flow)
  })

  it('goes back to the start on reset', () => {
    const chosen = reduceFlow(startingFlow, { type: 'picked', file: photo })
    expect(reduceFlow(chosen, { type: 'reset' })).toBe(startingFlow)
  })
})

describe('isSettled', () => {
  it('stops following on done, failed and waiting_user only', () => {
    expect(['queued', 'processing'].map((s) => isSettled(s as UploadStatus))).toEqual([false, false])
    expect(['done', 'failed', 'waiting_user'].map((s) => isSettled(s as UploadStatus))).toEqual([true, true, true])
  })
})

describe('followUpload', () => {
  function apiReturning(answers: (UploadState | Error)[]): { api: CaptureApi; calls: () => number } {
    let calls = 0
    const api: CaptureApi = {
      upload: () => Promise.reject(new Error('not used')),
      status: async () => {
        const next = answers[Math.min(calls++, answers.length - 1)]
        if (next instanceof Error) throw next
        return next
      },
    }
    return { api, calls: () => calls }
  }

  it('reports each status until the upload is done', async () => {
    const { api } = apiReturning([state('processing'), state('done')])
    const seen: UploadStatus[] = []

    const last = await followUpload(api, state('queued'), (u) => seen.push(u.status), new AbortController().signal, 0)

    expect(seen).toEqual(['processing', 'done'])
    expect(last.status).toBe('done')
  })

  it('stops when the upload needs the user, without asking again', async () => {
    const { api, calls } = apiReturning([state('waiting_user')])
    await followUpload(api, state('processing'), () => {}, new AbortController().signal, 0)
    expect(calls()).toBe(1)
  })

  it('does not ask at all when the first answer is already final', async () => {
    const { api, calls } = apiReturning([state('done')])
    await followUpload(api, state('failed', 'bad file'), () => {}, new AbortController().signal, 0)
    expect(calls()).toBe(0)
  })

  it('survives two failed requests in a row and carries on', async () => {
    const { api } = apiReturning([new Error('offline'), new Error('offline'), state('done')])
    const last = await followUpload(api, state('queued'), () => {}, new AbortController().signal, 0)
    expect(last.status).toBe('done')
  })

  it('gives up after three failed requests in a row', async () => {
    const { api, calls } = apiReturning([new Error('offline')])
    await expect(followUpload(api, state('queued'), () => {}, new AbortController().signal, 0)).rejects.toThrow('offline')
    expect(calls()).toBe(3)
  })

  it('stops quietly when aborted', async () => {
    const { api, calls } = apiReturning([state('processing')])
    const controller = new AbortController()
    const running = followUpload(api, state('queued'), () => {}, controller.signal, 50)
    controller.abort()
    await expect(running).rejects.toBeDefined()
    expect(calls()).toBe(0)
  })
})

describe('describeStatus', () => {
  it('has a plain message for every status', () => {
    const statuses: UploadStatus[] = ['queued', 'processing', 'waiting_user', 'done', 'failed']
    for (const status of statuses) expect(describeStatus(state(status)).text.length).toBeGreaterThan(10)
  })

  it('includes the server error when the import failed', () => {
    expect(describeStatus(state('failed', 'No walls found.'))).toEqual({
      text: 'The import failed. No walls found.',
      tone: 'error',
    })
  })

  it('does not leave a trailing space when the failure has no message', () => {
    expect(describeStatus(state('failed')).text).toBe('The import failed.')
  })
})
