/** Largest photo the page will try to upload. Phone cameras produce 3 to 12 MB, so this is generous. */
export const MAX_PHOTO_BYTES = 30 * 1024 * 1024

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Returns what is wrong with the chosen file, or null when it is fine to upload. */
export function photoProblem(file: File): string | null {
  if (!file.type.startsWith('image/')) return 'That file is not a photo. Choose a picture of the plan.'
  if (file.size === 0) return 'That photo is empty. Try taking it again.'
  if (file.size > MAX_PHOTO_BYTES) {
    return `That photo is ${formatBytes(file.size)}, over the ${formatBytes(MAX_PHOTO_BYTES)} limit.`
  }
  return null
}
