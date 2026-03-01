/**
 * Client-side image resize utility
 * Resizes images to max 1200px long side before upload (JPEG 85%)
 * Reduces server bandwidth and storage costs
 */

const MAX_DIMENSION = 1200
const JPEG_QUALITY = 0.85

/**
 * Resize an image file to max 1200px long side.
 * Returns a new File with JPEG compression.
 * Non-image files are returned as-is.
 */
export async function resizeImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/')) return file

  const bitmap = await createImageBitmap(file)
  const { width, height } = bitmap

  // Skip if already small enough
  if (width <= MAX_DIMENSION && height <= MAX_DIMENSION) {
    bitmap.close()
    return file
  }

  const scale = MAX_DIMENSION / Math.max(width, height)
  const newW = Math.round(width * scale)
  const newH = Math.round(height * scale)

  const canvas = new OffscreenCanvas(newW, newH)
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    bitmap.close()
    return file
  }

  ctx.drawImage(bitmap, 0, 0, newW, newH)
  bitmap.close()

  const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: JPEG_QUALITY })
  const name = file.name.replace(/\.[^.]+$/, '.jpg')
  return new File([blob], name, { type: 'image/jpeg' })
}
