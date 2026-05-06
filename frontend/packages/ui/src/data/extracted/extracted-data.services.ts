import { gql } from '@apollo/client'

import { client as apolloClient } from '../../graphql/apollo'
import { USE_PYKERN_API } from '../../constants'
import { pykernApiService } from '../../services/pykern-api'
import { type ExtractedDataOptions } from './extracted-data.types'

const EXTRACTED_DATA_QUERY = gql`
  query ExtractedDataQuery($proposal: String, $run: Int!, $variable: String!) {
    extracted_data(database: { proposal: $proposal }, run: $run, variable: $variable)
  }
`

function pngToDataUrl(bytes: Uint8Array): string {
  const blob = new Blob([bytes], { type: 'image/png' })
  return URL.createObjectURL(blob)
}

function base64ToUint8Array(dataUrl: string): Uint8Array {
  const base64 = dataUrl.split(',')[1]
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

async function getExtractedValueViaGraphQL({
  proposal,
  run,
  variable,
}: ExtractedDataOptions): Promise<Record<string, unknown>> {
  const { data } = await apolloClient.query({
    query: EXTRACTED_DATA_QUERY,
    variables: { proposal, run: Number(run), variable },
  })
  const result = data.extracted_data as Record<string, unknown>
  if (result.dtype === 'rgba' && typeof result.data === 'string') {
    const attrs = result.attrs as Record<string, unknown> | undefined
    return {
      ...result,
      data: base64ToUint8Array(result.data),
      shape: attrs?.shape,
    }
  }
  return result
}

async function getExtractedValue(options: ExtractedDataOptions) {
  if (!USE_PYKERN_API) {
    return getExtractedValueViaGraphQL(options)
  }
  return new Promise<Record<string, unknown>>((resolve, reject) => {
    pykernApiService.call(
      'image',
      { proposal: options.proposal, run: Number(options.run), variable: options.variable },
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
