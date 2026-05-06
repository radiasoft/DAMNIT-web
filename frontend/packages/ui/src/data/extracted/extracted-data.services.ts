import { pykernApiService } from '../../services/pykern-api'
import { type ExtractedDataOptions } from './extracted-data.types'

function pngToDataUrl(bytes: Uint8Array): string {
  const blob = new Blob([bytes], { type: 'image/png' })
  return URL.createObjectURL(blob)
}

async function getExtractedValue({ proposal, run, variable }: ExtractedDataOptions) {
  return new Promise<Record<string, unknown>>((resolve, reject) => {
    pykernApiService.call(
      'image',
      { proposal, run: Number(run), variable },
      (r) => {
        const result = r as Record<string, unknown>
        if (result.dtype === 'png' && result.data instanceof Uint8Array) {
          resolve({ ...result, data: pngToDataUrl(result.data) })
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
