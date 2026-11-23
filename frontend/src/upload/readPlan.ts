// Reads what the convert API sends back. Pure functions, so they are easy to test.

import type { Geometry } from '../model/geometry'

const PLAN_ARRAYS = ['walls', 'openings', 'rooms', 'labels', 'items', 'flags'] as const

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * True when the JSON has the shape of a geometry v1 plan: version 1, units "m", a known source
 * and all six arrays. It checks the outline only; the server already validated the details.
 */
export function isPlan(json: unknown): json is Geometry {
  if (!isObject(json)) return false
  if (json.version !== 1 || json.units !== 'm') return false
  if (json.source !== 'dxf' && json.source !== 'photo') return false
  if (!PLAN_ARRAYS.every((key) => Array.isArray(json[key]))) return false
  return json.scale === null || isObject(json.scale)
}

export const UNREACHABLE = "Can't reach the server. Check that the API is running on port 8000."
export const NOT_A_PLAN = "The server sent something that isn't a plan. Tell Yusuf."

/**
 * The sentence to show for a failed request. The server's own message comes first, since it
 * says what went wrong with this file. Status 0 means the request never got an answer.
 * A 5xx with no message is the dev server's proxy saying the API isn't running.
 */
export function errorMessage(status: number, body: unknown): string {
  if (isObject(body) && typeof body.message === 'string' && body.message.trim()) {
    return body.message
  }
  if (status === 0 || status >= 500) return UNREACHABLE
  return `The upload failed (error ${status}). Try again.`
}
