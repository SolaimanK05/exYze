import { pause } from './pause'
import type { CaptureApi, UploadState, UploadStatus } from './uploadApi'

// A stand-in for the backend, so the capture page can be shown on a phone before the upload
// endpoints exist. Switched on with ?demo in the address (see CapturePage). ?demo=corners ends
// in 'waiting_user' and ?demo=fail ends in 'failed'.

export function createDemoApi(ending: UploadStatus = 'done'): CaptureApi {
  const started = new Map<number, number>()
  let nextId = 1

  return {
    async upload(_floorId, _file, onProgress, signal) {
      for (let step = 1; step <= 10; step++) {
        await pause(120, signal)
        onProgress(step / 10)
      }
      const uploadId = nextId++
      started.set(uploadId, Date.now())
      return { uploadId, status: 'queued', error: null }
    },

    async status(uploadId, signal) {
      await pause(150, signal)
      const age = Date.now() - (started.get(uploadId) ?? 0)
      let status: UploadStatus = 'queued'
      if (age > 2500) status = ending
      else if (age > 1000) status = 'processing'
      const state: UploadState = {
        uploadId,
        status,
        error: status === 'failed' ? 'The plan could not be read.' : null,
      }
      return state
    },
  }
}
