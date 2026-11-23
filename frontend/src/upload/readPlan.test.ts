import { describe, expect, it } from 'vitest'
import { sampleGeometry } from '../model/sampleGeometry'
import { NOT_A_PLAN, UNREACHABLE, errorMessage, isPlan } from './readPlan'

describe('isPlan', () => {
  it('accepts a geometry v1 plan', () => {
    expect(isPlan(sampleGeometry)).toBe(true)
    expect(isPlan({ ...sampleGeometry, source: 'photo', scale: { m_per_px: 0.01, method: 'manual', confirmed: false } })).toBe(true)
  })

  it('refuses things that are not plans', () => {
    expect(isPlan(null)).toBe(false)
    expect(isPlan([])).toBe(false)
    expect(isPlan('plan')).toBe(false)
    expect(isPlan({ error: 'CANNOT_READ_FILE', message: 'No.' })).toBe(false)
  })

  it('refuses the wrong version, units or source', () => {
    expect(isPlan({ ...sampleGeometry, version: 2 })).toBe(false)
    expect(isPlan({ ...sampleGeometry, units: 'mm' })).toBe(false)
    expect(isPlan({ ...sampleGeometry, source: 'pdf' })).toBe(false)
  })

  it('refuses a plan with a missing array', () => {
    const { walls: _walls, ...noWalls } = sampleGeometry
    expect(isPlan(noWalls)).toBe(false)
    expect(isPlan({ ...sampleGeometry, flags: null })).toBe(false)
  })
})

describe('errorMessage', () => {
  it("uses the server's message", () => {
    const body = { error: 'FILE_TOO_LARGE', message: 'This file is too big.' }
    expect(errorMessage(413, body)).toBe('This file is too big.')
  })

  it('says the server is unreachable when there was no answer', () => {
    expect(errorMessage(0, null)).toBe(UNREACHABLE)
    expect(errorMessage(502, '')).toBe(UNREACHABLE)
    expect(errorMessage(500, { message: '' })).toBe(UNREACHABLE)
  })

  it('falls back to the status for other errors', () => {
    expect(errorMessage(404, 'Not Found')).toBe('The upload failed (error 404). Try again.')
  })

  it('has a message for an answer that is not a plan', () => {
    expect(NOT_A_PLAN).toMatch(/isn't a plan/)
  })
})
