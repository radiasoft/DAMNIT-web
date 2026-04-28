import { pykernApiService } from '../../services/pykern-api'
import { type ExtractedDataOptions } from './extracted-data.types'

async function getExtractedValue({ proposal, run, variable }: ExtractedDataOptions) {
  return new Promise<Record<string, unknown>>((resolve, reject) => {
    pykernApiService.call(
      'extracted_data',
      { proposal, run: Number(run), variable },
      (r) => resolve(r as Record<string, unknown>),
      reject,
    )
  })
}

const ExtractedDataServices = {
  getExtractedValue,
}

export default ExtractedDataServices
