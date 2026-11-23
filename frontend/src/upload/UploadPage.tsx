import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import { ConvertError, convertPlan } from '../app/api'
import { PlanSummary, ReviewList } from '../app/FloorPage'
import { PlanViewport } from '../app/PlanViewport'
import type { Geometry } from '../model/geometry'
import { ACCEPT, KIND_LABEL, checkFile, formatSize } from './fileCheck'
import type { FileKind } from './fileCheck'
import './upload.css'

// idle -> chosen -> uploading -> converting -> done, and any of them can end in error.
type Step =
  | { step: 'idle' }
  | { step: 'chosen'; file: File; kind: FileKind }
  | { step: 'uploading'; file: File; kind: FileKind; progress: number }
  | { step: 'converting'; file: File; kind: FileKind }
  | { step: 'done'; file: File; geometry: Geometry }
  | { step: 'error'; message: string }

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

/** A photo result, or any plan whose scale nobody has confirmed, isn't to scale. */
function isRough(geometry: Geometry): boolean {
  return geometry.source === 'photo' || (geometry.scale !== null && !geometry.scale.confirmed)
}

export default function UploadPage() {
  const [state, setState] = useState<Step>({ step: 'idle' })
  const [dragging, setDragging] = useState(false)
  const controller = useRef<AbortController | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const cameraInput = useRef<HTMLInputElement>(null)

  // Leaving the page cancels an upload that is still running.
  useEffect(() => () => controller.current?.abort(), [])

  function choose(file: File | undefined) {
    if (!file) return
    const check = checkFile(file.name, file.size)
    setState(check.ok ? { step: 'chosen', file, kind: check.kind } : { step: 'error', message: check.message })
  }

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    choose(event.target.files?.[0])
    event.target.value = '' // so choosing the same file again still fires a change
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    choose(event.dataTransfer.files[0])
  }

  async function convert(file: File, kind: FileKind) {
    const ctrl = new AbortController()
    controller.current = ctrl
    setState({ step: 'uploading', file, kind, progress: 0 })
    const onProgress = (progress: number) => {
      if (ctrl.signal.aborted) return
      setState(progress >= 1 ? { step: 'converting', file, kind } : { step: 'uploading', file, kind, progress })
    }
    try {
      const geometry = await convertPlan(file, onProgress, ctrl.signal)
      setState({ step: 'done', file, geometry })
    } catch (error) {
      if (isAbort(error)) {
        if (controller.current === ctrl) setState({ step: 'chosen', file, kind })
        return
      }
      const message = error instanceof ConvertError ? error.message : 'Something went wrong. Try again.'
      setState({ step: 'error', message })
    } finally {
      if (controller.current === ctrl) controller.current = null
    }
  }

  function reset() {
    controller.current?.abort()
    controller.current = null
    setState({ step: 'idle' })
  }

  const pickers = (
    <>
      <input ref={fileInput} type="file" accept={ACCEPT} onChange={onPick} hidden />
      <input ref={cameraInput} type="file" accept="image/jpeg,image/png" capture="environment" onChange={onPick} hidden />
    </>
  )

  if (state.step === 'done') {
    const { file, geometry } = state
    return (
      <div className="floor">
        <div className="floor__head">
          <h1 className="upload__result-title">{file.name}</h1>
          <span className="pill pill--draft">Not saved</span>
        </div>
        <div className="floor__body">
          <div className="floor__canvas">
            <PlanViewport geometry={geometry} />
          </div>
          <aside className="floor__panel" aria-label="Converted plan">
            {isRough(geometry) && (
              <p className="upload__note upload__note--rough" role="note">
                {geometry.source === 'photo'
                  ? 'Rough result from a photo. Sizes are not to scale yet.'
                  : 'The scale is a guess. Check the items below before measuring.'}
              </p>
            )}
            <PlanSummary geometry={geometry} />
            <ReviewList geometry={geometry} />
            <p className="muted upload__note">Not saved: saving to a project comes in Sprint 3.</p>
            <button type="button" className="button" onClick={reset}>
              Upload another
            </button>
          </aside>
        </div>
      </div>
    )
  }

  return (
    <div className="page upload">
      <h1>Upload a plan</h1>
      <p className="muted">Turn a DXF drawing or a photo of a printed plan into a 2D and 3D model.</p>
      {pickers}

      {state.step === 'idle' && (
        <div
          className={`upload__drop${dragging ? ' upload__drop--over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <svg className="upload__icon" viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
            <path d="M12 16V4m0 0-5 5m5-5 5 5M4 20h16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="upload__drop-text">Drop a DXF or a photo here</p>
          <div className="upload__actions">
            <button type="button" className="button button--primary" onClick={() => fileInput.current?.click()}>
              Choose file
            </button>
            <button type="button" className="button" onClick={() => cameraInput.current?.click()}>
              Take a photo
            </button>
          </div>
          <p className="muted upload__limits">DXF up to 20 MB · JPG or PNG up to 10 MB</p>
        </div>
      )}

      {state.step === 'chosen' && (
        <div className="upload__card">
          <FileLine file={state.file} kind={state.kind} />
          <div className="upload__actions">
            <button type="button" className="button button--primary" onClick={() => convert(state.file, state.kind)}>
              Convert
            </button>
            <button type="button" className="button" onClick={() => fileInput.current?.click()}>
              Choose another
            </button>
          </div>
        </div>
      )}

      {state.step === 'uploading' && (
        <div className="upload__card" aria-live="polite">
          <p>Uploading {state.file.name}</p>
          <div className="upload__progress-row">
            <progress className="upload__progress" value={state.progress} max={1} aria-label="Upload progress" />
            <span className="upload__percent">{Math.round(state.progress * 100)}%</span>
          </div>
          <div className="upload__actions">
            <button type="button" className="button" onClick={() => controller.current?.abort()}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {state.step === 'converting' && (
        <div className="upload__card" aria-live="polite">
          <p className="upload__converting">
            <span className="upload__spinner" aria-hidden="true" />
            Converting your plan…
          </p>
          <FileLine file={state.file} kind={state.kind} />
        </div>
      )}

      {state.step === 'error' && (
        <div className="upload__card upload__card--error" role="alert">
          <p className="error">{state.message}</p>
          <div className="upload__actions">
            <button type="button" className="button button--primary" onClick={reset}>
              Try another file
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function FileLine({ file, kind }: { file: File; kind: FileKind }) {
  return (
    <div className="upload__file">
      <span className="upload__file-name">{file.name}</span>
      <span className="muted">
        {KIND_LABEL[kind]} · {formatSize(file.size)}
      </span>
    </div>
  )
}
