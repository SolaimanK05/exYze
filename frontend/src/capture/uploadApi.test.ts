import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, httpApi } from './uploadApi'

class FakeXhr {
  static last: FakeXhr
  method = ''
  url = ''
  status = 0
  responseText = ''
  body: unknown = null
  aborted = false
  upload: { onprogress: ((e: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = {
    onprogress: null,
  }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  onabort: (() => void) | null = null

  constructor() {
    FakeXhr.last = this
  }
  open(method: string, url: string) {
    this.method = method
    this.url = url
  }
  send(body: unknown) {
    this.body = body
  }
  abort() {
    this.aborted = true
    this.onabort?.()
  }
  reply(status: number, text: string) {
    this.status = status
    this.responseText = text
    this.onload?.()
  }
}

const photo = new File(['pixels'], 'plan.jpg', { type: 'image/jpeg' })

afterEach(() => vi.unstubAllGlobals())

describe('httpApi.upload', () => {
  it('posts the photo as multipart form data to the floor', () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    void httpApi.upload(12, photo, () => {}, new AbortController().signal)

    const xhr = FakeXhr.last
    expect(xhr.method).toBe('POST')
    expect(xhr.url).toBe('/api/floors/12/uploads')
    const form = xhr.body as FormData
    expect((form.get('file') as File).name).toBe('plan.jpg')
    expect(form.get('source')).toBe('photo')
  })

  it('reports progress as a fraction', () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const seen: number[] = []
    void httpApi.upload(1, photo, (f) => seen.push(f), new AbortController().signal)

    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 25, total: 100 })
    FakeXhr.last.upload.onprogress?.({ lengthComputable: false, loaded: 50, total: 0 })
    FakeXhr.last.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 })

    expect(seen).toEqual([0.25, 1])
  })

  it('returns the new upload from a successful answer', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const result = httpApi.upload(1, photo, () => {}, new AbortController().signal)
    FakeXhr.last.reply(201, '{"upload_id": 9, "status": "queued"}')
    await expect(result).resolves.toEqual({ uploadId: 9, status: 'queued', error: null })
  })

  it('turns a named server error into an ApiError', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const result = httpApi.upload(1, photo, () => {}, new AbortController().signal)
    FakeXhr.last.reply(422, '{"error": "UPLOAD_NOT_READY", "message": "The floor is locked."}')
    await expect(result).rejects.toMatchObject({ code: 'UPLOAD_NOT_READY', message: 'The floor is locked.' })
  })

  it('falls back to a generic message when the error is not JSON', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const result = httpApi.upload(1, photo, () => {}, new AbortController().signal)
    FakeXhr.last.reply(502, '<html>Bad gateway</html>')
    await expect(result).rejects.toMatchObject({ code: 'HTTP_502', message: expect.stringContaining('502') })
  })

  it('rejects an answer that is not an upload', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const result = httpApi.upload(1, photo, () => {}, new AbortController().signal)
    FakeXhr.last.reply(200, '{"upload_id": 9, "status": "teleporting"}')
    await expect(result).rejects.toMatchObject({ code: 'BAD_RESPONSE' })
  })

  it('reports a network failure in plain words', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const result = httpApi.upload(1, photo, () => {}, new AbortController().signal)
    FakeXhr.last.onerror?.()
    await expect(result).rejects.toMatchObject({ code: 'NETWORK' })
  })

  it('cancels the request when the signal aborts', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    const controller = new AbortController()
    const result = httpApi.upload(1, photo, () => {}, controller.signal)
    controller.abort()
    expect(FakeXhr.last.aborted).toBe(true)
    await expect(result).rejects.toBeDefined()
  })
})

describe('httpApi.status', () => {
  it('reads the status and error of an upload', async () => {
    const fetchMock = vi.fn(async (_url: string) => new Response('{"upload_id": 9, "status": "failed", "error": "No walls found."}'))
    vi.stubGlobal('fetch', fetchMock)

    const result = await httpApi.status(9, new AbortController().signal)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/uploads/9')
    expect(result).toEqual({ uploadId: 9, status: 'failed', error: 'No walls found.' })
  })

  it('throws the server error for a missing upload', async () => {
    vi.stubGlobal('fetch', async () => new Response('{"error": "NOT_FOUND", "message": "No such upload."}', { status: 404 }))
    await expect(httpApi.status(404, new AbortController().signal)).rejects.toBeInstanceOf(ApiError)
  })

  it('reports a network failure in plain words', async () => {
    vi.stubGlobal('fetch', async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(httpApi.status(1, new AbortController().signal)).rejects.toMatchObject({ code: 'NETWORK' })
  })
})
