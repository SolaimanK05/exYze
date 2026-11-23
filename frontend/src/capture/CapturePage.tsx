import { useEffect, useReducer, useRef, useState } from 'react'
import { createDemoApi } from './demoApi'
import { formatBytes, photoProblem } from './photoFile'
import { describeStatus } from './statusText'
import { httpApi } from './uploadApi'
import type { CaptureApi, UploadStatus } from './uploadApi'
import { followUpload, isSettled, reduceFlow, startingFlow } from './uploadFlow'
import './capture.css'

interface Props {
  floorId: number
  /** Only passed by tests and the demo. The page talks to the real backend by default. */
  api?: CaptureApi
}

// Opening the page with ?demo uses a fake backend, so it can be shown before the upload endpoint exists.
function pickApi(): CaptureApi {
  if (!import.meta.env.DEV) return httpApi
  const demo = new URLSearchParams(window.location.search).get('demo')
  if (demo === null) return httpApi
  const ending: UploadStatus = demo === 'corners' ? 'waiting_user' : demo === 'fail' ? 'failed' : 'done'
  return createDemoApi(ending)
}

const tips = [
  'Lay the plan flat on a table.',
  'Fill the frame with the whole sheet, edges included.',
  'Avoid shadows and glare across the paper.',
  'Hold the phone straight above it, parallel to the paper.',
]

export function CapturePage({ floorId, api }: Props) {
  const [flow, dispatch] = useReducer(reduceFlow, startingFlow)
  const [preview, setPreview] = useState<{ file: File; url: string } | null>(null)
  const [source] = useState(() => api ?? pickApi())
  const running = useRef<AbortController | null>(null)

  const file = 'file' in flow ? flow.file : null

  // The preview is an object URL, which has to be created and revoked by hand.
  useEffect(() => {
    if (!file) return
    const url = URL.createObjectURL(file)
    // oxlint-disable-next-line react/set-state-in-effect
    setPreview({ file, url })
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => () => running.current?.abort(), [])

  function choose(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0]
    event.target.value = '' // lets the same photo be chosen again after a retake
    if (!picked) return
    const problem = photoProblem(picked)
    if (problem) dispatch({ type: 'rejected', message: problem })
    else dispatch({ type: 'picked', file: picked })
  }

  async function send() {
    if (!file) return
    const controller = new AbortController()
    running.current = controller
    dispatch({ type: 'upload-started' })
    try {
      const upload = await source.upload(
        floorId,
        file,
        (fraction) => dispatch({ type: 'progress', fraction }),
        controller.signal,
      )
      dispatch({ type: 'uploaded', upload })
      await followUpload(source, upload, (next) => dispatch({ type: 'status', upload: next }), controller.signal)
    } catch (err) {
      if (controller.signal.aborted) return
      dispatch({ type: 'failed', message: err instanceof Error ? err.message : 'Something went wrong.' })
    }
  }

  function startOver() {
    running.current?.abort()
    dispatch({ type: 'reset' })
  }

  const uploading = flow.phase === 'uploading'
  const tracking = flow.phase === 'tracking'
  const finished = tracking && isSettled(flow.upload.status)
  const status = tracking ? describeStatus(flow.upload) : null

  return (
    <div className="capture">
      <h1>Add a plan photo</h1>
      <p className="capture__lead">Photograph a printed floor plan. We straighten it and read the printed measurements.</p>

      {flow.phase === 'empty' || flow.phase === 'problem' ? (
        <ul className="capture__tips" aria-label="Tips for a good photo">
          {tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      ) : null}

      {file && preview?.file === file && (
        <figure className="capture__preview">
          <img src={preview.url} alt="The plan photo you chose" />
          <figcaption>
            {file.name} · {formatBytes(file.size)}
          </figcaption>
        </figure>
      )}

      {flow.phase === 'problem' && (
        <p className="capture__message capture__message--error" role="alert">
          {flow.message}
        </p>
      )}

      {uploading && (
        <div className="capture__progress">
          <progress max={1} value={flow.progress} aria-label="Upload progress" />
          <span>{Math.round(flow.progress * 100)}%</span>
        </div>
      )}

      {status && (
        <p className={`capture__message capture__message--${status.tone}`} role="status">
          {status.text}
        </p>
      )}

      <div className="capture__actions">
        {(flow.phase === 'empty' || flow.phase === 'chosen' || flow.phase === 'problem') && (
          <>
            <label className="capture__button capture__button--primary">
              {file ? 'Retake photo' : 'Take photo'}
              <input type="file" accept="image/*" capture="environment" onChange={choose} />
            </label>
            <label className="capture__button">
              Choose from files
              <input type="file" accept="image/*" onChange={choose} />
            </label>
          </>
        )}
        {(flow.phase === 'chosen' || (flow.phase === 'problem' && file)) && (
          <button type="button" className="capture__button capture__button--primary" onClick={send}>
            Upload
          </button>
        )}
        {uploading && (
          <button type="button" className="capture__button" onClick={startOver}>
            Cancel
          </button>
        )}
        {finished && (
          <button type="button" className="capture__button" onClick={startOver}>
            Add another photo
          </button>
        )}
      </div>
    </div>
  )
}
