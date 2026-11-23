// Checks a chosen file before it is uploaded. Pure functions, so they are easy to test.
// The server checks the same rules again (backend/app/api/convert.py); this is only so the
// person finds out straight away instead of after a 20 MB upload.

export type FileKind = 'dxf' | 'photo'

export type FileCheck = { ok: true; kind: FileKind } | { ok: false; message: string }

const MB = 1024 * 1024

/** The largest file the convert API accepts, in bytes. */
export const SIZE_LIMIT: Record<FileKind, number> = {
  dxf: 20 * MB,
  photo: 10 * MB,
}

export const KIND_LABEL: Record<FileKind, string> = {
  dxf: 'DXF drawing',
  photo: 'Photo',
}

/** What the file pickers offer. DXF files often have no MIME type, so the extension is listed too. */
export const ACCEPT = '.dxf,.jpg,.jpeg,.png,image/jpeg,image/png'

/** The extension in lower case with its dot, for example ".dxf". An empty string if there is none. */
export function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot <= 0 ? '' : name.slice(dot).toLowerCase()
}

/** 34 MB, 1.2 MB, 820 KB or 12 bytes. */
export function formatSize(bytes: number): string {
  if (bytes >= 10 * MB) return `${Math.round(bytes / MB)} MB`
  if (bytes >= MB) return `${(bytes / MB).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} bytes`
}

/**
 * Decides whether a file can be uploaded, judged by its name and size in bytes.
 * Returns the kind of file, or a plain sentence saying what is wrong and what to do.
 */
export function checkFile(name: string, size: number): FileCheck {
  const ext = extensionOf(name)
  // Type first: for a 50 MB PDF, "wrong type" is the useful answer, since a smaller PDF won't help.
  if (ext === '.heic' || ext === '.heif') {
    return { ok: false, message: "iPhone HEIC photos aren't supported yet. Share the photo as JPEG and try again." }
  }
  const kind: FileKind | null = ext === '.dxf' ? 'dxf' : PHOTO_EXTENSIONS.has(ext) ? 'photo' : null
  if (!kind) {
    return { ok: false, message: "This file type isn't supported. Choose a .dxf file or a JPG or PNG photo." }
  }
  if (size === 0) return { ok: false, message: 'This file is empty. Choose another file.' }
  if (size > SIZE_LIMIT[kind]) {
    return { ok: false, message: `This file is ${formatSize(size)}. The limit is 20 MB for DXF and 10 MB for photos.` }
  }
  return { ok: true, kind }
}

const PHOTO_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png'])
