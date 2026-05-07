/// <reference types="vite/client" />
import { formatUrl } from './utils/helpers'

export const CONTACT_EMAIL = 'da@xfel.eu'

export const BASE_URL = formatUrl(import.meta.env.VITE_BASE_URL)
export const HTTP_URL = window.location.origin + BASE_URL

const wsProtocol = window.location.origin.startsWith('https') ? 'wss' : 'ws'
export const WS_URL = `${wsProtocol}://${window.location.host}${BASE_URL}`

export const PYKERN_WS_URL =
  import.meta.env.VITE_PYKERN_WS ??
  `${wsProtocol}://${window.location.host}/api-v1`

export const EMPTY_VALUE = 'None'
export const VARIABLES = {
  proposal: 'proposal',
  run: 'run',
}
export const DTYPES = {
  image: 'image',
  array: 'array',
  string: 'string',
  number: 'number',
  timestamp: 'timestamp',
}

export const USE_PYKERN_API = import.meta.env.VITE_PYKERN_API === 'true'
export const PAGINATED = import.meta.env.VITE_TABLE_ALL !== undefined && import.meta.env.VITE_TABLE_ALL !== 'undefined'
  ? import.meta.env.VITE_TABLE_ALL !== 'true'
  : !USE_PYKERN_API
export const GLIDE_HACK = import.meta.env.VITE_GLIDE_HACK !== undefined && import.meta.env.VITE_GLIDE_HACK !== 'undefined'
  ? import.meta.env.VITE_GLIDE_HACK === 'true'
  : USE_PYKERN_API

export const EXCLUDED_VARIABLES = ['proposal', 'added_at']

export const VISIBILITY_EXCLUDED_VARIABLES = [...EXCLUDED_VARIABLES, 'run']
