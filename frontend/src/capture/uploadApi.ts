// What the capture page needs from the backend. The endpoints are the ones in
// 01 Architecture and Contracts: POST /api/floors/{id}/uploads and GET /api/uploads/{id}.

export type UploadStatus = 'queued' | 'processing' | 'waiting_user' | 'done' | 'failed'

export interface UploadState {
  uploadId: number
  status: UploadStatus
  /** Set when status is 'failed'. */
  error: string | null
}

export interface CaptureApi {
  /** Sends the photo as multipart form data and reports how much has gone out, from 0 to 1. */
  upload(floorId: number, file: File, onProgress: (fraction: number) => void, signal: AbortSignal): Promise<UploadState>
  status(uploadId: number, signal: AbortSignal): Promise<UploadState>
}

/** An error the server answered with: { "error": "NAME", "message": "..." }, or a network failure. */
export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

const statuses: readonly string[] = ['queued', 'processing', 'waiting_user', 'done', 'failed']

function parseUpload(text: string): UploadState {
  let body: unknown
  try {
    body = JSON.parse(text)
  } catch {
    throw new ApiError('BAD_RESPONSE', 'The server sent something unexpected.')
  }
  const data = body as { upload_id?: unknown; status?: unknown; error?: unknown }
  if (typeof data?.upload_id !== 'number' || typeof data.status !== 'string' || !statuses.includes(data.status)) {
    throw new ApiError('BAD_RESPONSE', 'The server sent something unexpected.')
  }
  return {
    uploadId: data.upload_id,
    status: data.status as UploadStatus,
    error: typeof data.error === 'string' ? data.error : null,
  }
}

function failure(httpStatus: number, text: string): ApiError {
  try {
    const body = JSON.parse(text) as { error?: unknown; message?: unknown }
    if (typeof body.error === 'string' && typeof body.message === 'string') {
      return new ApiError(body.error, body.message)
    }
  } catch {
    // not JSON, fall through to the generic message
  }
  return new ApiError('HTTP_' + httpStatus, `The server answered with an error (${httpStatus}).`)
}

const networkError = () => new ApiError('NETWORK', 'Could not reach the server. Check your connection and try again.')

export const httpApi: CaptureApi = {
  // fetch() cannot report upload progress, so the photo goes out through XMLHttpRequest.
  upload(floorId, file, onProgress, signal) {
    return new Promise<UploadState>((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `/api/floors/${floorId}/uploads`)
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(event.loaded / event.total)
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(parseUpload(xhr.responseText))
          } catch (err) {
            reject(err)
          }
        } else {
          reject(failure(xhr.status, xhr.responseText))
        }
      }
      xhr.onerror = () => reject(networkError())
      xhr.onabort = () => reject(signal.reason ?? new DOMException('Upload cancelled', 'AbortError'))
      signal.addEventListener('abort', () => xhr.abort(), { once: true })

      const form = new FormData()
      form.append('file', file)
      form.append('source', 'photo')
      xhr.send(form)
    })
  },

  async status(uploadId, signal) {
    let response: Response
    try {
      response = await fetch(`/api/uploads/${uploadId}`, { signal })
    } catch (err) {
      if (signal.aborted) throw err
      throw networkError()
    }
    const text = await response.text()
    if (!response.ok) throw failure(response.status, text)
    return parseUpload(text)
  },
}
