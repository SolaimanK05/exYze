import { describe, expect, it } from 'vitest'
import { SIZE_LIMIT, checkFile, extensionOf, formatSize } from './fileCheck'

const MB = 1024 * 1024

describe('extensionOf', () => {
  it('gives the last extension in lower case', () => {
    expect(extensionOf('plan01.dxf')).toBe('.dxf')
    expect(extensionOf('Ground Floor.v2.DXF')).toBe('.dxf')
  })

  it('gives nothing for a name with no extension or a dot file', () => {
    expect(extensionOf('plan')).toBe('')
    expect(extensionOf('.dxf')).toBe('')
  })
})

describe('formatSize', () => {
  it('rounds to a readable size', () => {
    expect(formatSize(34 * MB)).toBe('34 MB')
    expect(formatSize(1.24 * MB)).toBe('1.2 MB')
    expect(formatSize(820 * 1024)).toBe('820 KB')
    expect(formatSize(12)).toBe('12 bytes')
  })
})

describe('checkFile', () => {
  it('accepts a DXF', () => {
    expect(checkFile('plan01.dxf', 1 * MB)).toEqual({ ok: true, kind: 'dxf' })
  })

  it('accepts JPG and PNG photos', () => {
    expect(checkFile('IMG_0001.jpg', 2 * MB)).toEqual({ ok: true, kind: 'photo' })
    expect(checkFile('IMG_0001.jpeg', 2 * MB)).toEqual({ ok: true, kind: 'photo' })
    expect(checkFile('scan.png', 2 * MB)).toEqual({ ok: true, kind: 'photo' })
  })

  it('accepts upper-case extensions', () => {
    expect(checkFile('PLAN.DXF', MB)).toEqual({ ok: true, kind: 'dxf' })
    expect(checkFile('IMG_0001.JPG', MB)).toEqual({ ok: true, kind: 'photo' })
  })

  it('refuses HEIC with its own message', () => {
    const result = checkFile('IMG_0001.HEIC', MB)
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.message).toMatch(/HEIC/)
  })

  it('refuses other types', () => {
    for (const name of ['plan.pdf', 'plan.dwg', 'plan']) {
      const result = checkFile(name, MB)
      expect(result.ok).toBe(false)
      if (!result.ok) expect(result.message).toMatch(/isn't supported/)
    }
  })

  it('allows a file exactly at the limit and refuses one byte over', () => {
    expect(checkFile('plan.dxf', SIZE_LIMIT.dxf)).toEqual({ ok: true, kind: 'dxf' })
    expect(checkFile('plan.dxf', SIZE_LIMIT.dxf + 1).ok).toBe(false)
    expect(checkFile('photo.jpg', SIZE_LIMIT.photo)).toEqual({ ok: true, kind: 'photo' })
    expect(checkFile('photo.jpg', SIZE_LIMIT.photo + 1).ok).toBe(false)
  })

  it('says how big the file is and what the limits are', () => {
    const result = checkFile('plan.dxf', 34 * MB)
    expect(result).toEqual({
      ok: false,
      message: 'This file is 34 MB. The limit is 20 MB for DXF and 10 MB for photos.',
    })
  })

  it('refuses an empty file', () => {
    expect(checkFile('plan.dxf', 0).ok).toBe(false)
  })
})
