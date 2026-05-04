import { pykernApiService } from '../../services/pykern-api'
import { type ExtractedDataOptions } from './extracted-data.types'

function pngToDataUrl(bytes: Uint8Array): string {
  const blob = new Blob([bytes], { type: 'image/png' })
  return URL.createObjectURL(blob)
}

function rgbaToDataUrl(bytes: Uint8Array, width: number, height: number): string {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!
  ctx.putImageData(new ImageData(new Uint8ClampedArray(bytes), width, height), 0, 0)
  return canvas.toDataURL()
}

async function getExtractedValue({ proposal, run, variable }: ExtractedDataOptions) {
  return new Promise<Record<string, unknown>>((resolve, reject) => {
    pykernApiService.call(
      'extracted_data',
      { proposal, run: Number(run), variable },
      (r) => {
        const result = r as Record<string, unknown>
        if (result.dtype === 'png' && result.data instanceof Uint8Array) {
          resolve({ ...result, data: pngToDataUrl(result.data) })
        } else if (result.dtype === 'rgba' && result.data instanceof Uint8Array) {
          const [height, width] = (result.attrs as { shape: number[] }).shape
          resolve({ ...result, data: rgbaToDataUrl(result.data, width, height) })
        } else {
          resolve(result)
        }
      },
      reject,
    )
  })
}

const ExtractedDataServices = {
  getExtractedValue,
}

export default ExtractedDataServices
