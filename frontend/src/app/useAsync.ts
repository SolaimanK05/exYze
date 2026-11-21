import { useEffect, useState } from 'react'

export type Loadable<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

/**
 * Runs an async loader when the page opens, and again whenever `load` changes.
 * Wrap a loader that depends on route values in useCallback so it only changes when they do.
 */
export function useAsync<T>(load: () => Promise<T>): Loadable<T> {
  const [settled, setSettled] = useState<{ load: () => Promise<T>; result: Loadable<T> } | null>(null)

  useEffect(() => {
    let cancelled = false
    load().then(
      (data) => {
        if (!cancelled) setSettled({ load, result: { status: 'ready', data } })
      },
      (error: unknown) => {
        const message = error instanceof Error ? error.message : String(error)
        if (!cancelled) setSettled({ load, result: { status: 'error', message } })
      },
    )
    return () => {
      cancelled = true
    }
  }, [load])

  // A result that belongs to an earlier loader is stale, so the page shows loading until the new one arrives.
  return settled && settled.load === load ? settled.result : { status: 'loading' }
}
