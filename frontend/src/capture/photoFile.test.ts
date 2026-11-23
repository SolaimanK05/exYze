import { describe, expect, it } from 'vitest'
import { MAX_PHOTO_BYTES, formatBytes, photoProblem } from './photoFile'

function fakeFile(type: string, size: number): File {
  const file = new File(['x'], 'plan.jpg', { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

describe('photoProblem', () => {
  it('accepts an ordinary phone photo', () => {
    expect(photoProblem(fakeFile('image/jpeg', 4_000_000))).toBeNull()
  })

  it('accepts a photo of exactly the largest allowed size', () => {
    expect(photoProblem(fakeFile('image/png', MAX_PHOTO_BYTES))).toBeNull()
  })

  it('rejects a file that is not an image', () => {
    expect(photoProblem(fakeFile('application/pdf', 1000))).toMatch(/not a photo/)
  })

  it('rejects an empty file', () => {
    expect(photoProblem(fakeFile('image/jpeg', 0))).toMatch(/empty/)
  })

  it('rejects a photo over the limit and says how big it was', () => {
    expect(photoProblem(fakeFile('image/jpeg', MAX_PHOTO_BYTES + 1))).toMatch(/30\.0 MB limit/)
  })
})

describe('formatBytes', () => {
  it('uses KB below one megabyte and never shows 0 KB', () => {
    expect(formatBytes(1)).toBe('1 KB')
    expect(formatBytes(512 * 1024)).toBe('512 KB')
  })

  it('uses MB with one decimal from one megabyte', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
    expect(formatBytes(5.25 * 1024 * 1024)).toBe('5.3 MB')
  })
})
