import { encode, decode } from '@msgpack/msgpack'
import { PYKERN_WS_URL } from '../constants'

const AUTH_API_NAME = 'authenticate_connection'
const AUTH_API_VERSION = 658584001

const MSG_KIND_BASE = 777500
const MSG_KIND_CALL = 1 + MSG_KIND_BASE
const MSG_KIND_REPLY = 2 + MSG_KIND_BASE
const MSG_KIND_SUBSCRIBE = 3 + MSG_KIND_BASE
const MSG_KIND_UNSUBSCRIBE = 4 + MSG_KIND_BASE

type ResultHandler = (result: unknown) => void
type ErrorHandler = (error: string) => void
export type ConnectionListener = (connected: boolean) => void

class Call {
  destroyed = false
  isSubscription: boolean
  call_id: number
  api_name: string

  #apiService: APIService
  #api_args: unknown
  #resultHandler: ResultHandler
  #apiErrorHandler?: ErrorHandler

  constructor(
    apiService: APIService,
    isSubscription: boolean,
    call_id: number,
    api_name: string,
    api_args: unknown,
    resultHandler: ResultHandler,
    apiErrorHandler?: ErrorHandler,
  ) {
    this.#apiService = apiService
    this.isSubscription = isSubscription
    this.call_id = call_id
    this.api_name = api_name
    this.#api_args = api_args
    this.#resultHandler = resultHandler
    this.#apiErrorHandler = apiErrorHandler
  }

  destroy() {
    if (this.destroyed) return
    this.destroyed = true
    this.#apiService.callDestroy(this.call_id)
  }

  handleError(api_error: string) {
    if (this.#apiErrorHandler) {
      this.#apiErrorHandler(api_error)
    } else {
      console.error('pykern-api call error', api_error, this)
    }
    this.destroy()
  }

  handleResult(api_result: unknown) {
    this.#resultHandler(api_result)
    if (api_result == null || !this.isSubscription) {
      this.destroy()
    }
  }

  msg(): Uint8Array {
    const a = this.#api_args
    this.#api_args = null
    return encode({
      api_args: a,
      api_name: this.api_name,
      call_id: this.call_id,
      msg_kind: this.isSubscription ? MSG_KIND_SUBSCRIBE : MSG_KIND_CALL,
    })
  }

  unsubscribe() {
    if (this.destroyed) return
    if (!this.isSubscription)
      throw new Error(`call to api_name=${this.api_name} is not a subscription`)
    this.#apiService.sendUnsubscribe(
      encode({ call_id: this.call_id, msg_kind: MSG_KIND_UNSUBSCRIBE }),
    )
    this.destroy()
  }
}

class APIService {
  #authOK = false
  #call_id = 0
  #connectionListeners: Set<ConnectionListener> = new Set()
  #pendingCalls = new Map<number, Call>()
  #socket: WebSocket | null = null
  #socketRetryBackoff = 0
  #timeout: ReturnType<typeof setTimeout> | null = null
  #unsentMsgs: Uint8Array[] = []

  constructor() {
    this.#socketOpen()
  }

  addConnectionListener(fn: ConnectionListener): () => void {
    this.#connectionListeners.add(fn)
    return () => this.#connectionListeners.delete(fn)
  }

  call(
    api_name: string,
    api_args: unknown,
    resultHandler: ResultHandler,
    apiErrorHandler?: ErrorHandler,
  ): Call {
    return this.#sendCall(
      new Call(this, false, ++this.#call_id, api_name, api_args, resultHandler, apiErrorHandler),
    )
  }

  callDestroy(call_id: number) {
    this.#pendingCalls.delete(call_id)
  }

  onDestroy() {
    if (this.#socket) {
      this.#socket.close()
      this.#socket = null
      this.#notifyConnected(false)
    }
    this.#clearCalls()
  }

  sendUnsubscribe(msg: Uint8Array) {
    this.#unsentMsgs.push(msg)
    this.#send()
  }

  subscribe(
    api_name: string,
    api_args: unknown,
    resultHandler: ResultHandler,
    apiErrorHandler?: ErrorHandler,
  ): Call {
    return this.#sendCall(
      new Call(this, true, ++this.#call_id, api_name, api_args, resultHandler, apiErrorHandler),
    )
  }

  #authError(error: unknown) {
    if (this.#socket) this.#socket.close()
    this.#socketOnError(error)
  }

  #authResult(_api_result: unknown) {
    this.#authOK = true
    this.#socketRetryBackoff = 0
    this.#send()
  }

  #clearCalls() {
    const calls = [...this.#pendingCalls.values()]
    this.#pendingCalls = new Map()
    this.#unsentMsgs = []
    for (const c of calls) c.destroy()
  }

  #findCall(call_id: number): Call | null {
    const rv = this.#pendingCalls.get(call_id)
    if (!rv) return null
    if (rv.destroyed) {
      this.#pendingCalls.delete(call_id)
      return null
    }
    return rv
  }

  #notifyConnected(connected: boolean) {
    for (const fn of this.#connectionListeners) fn(connected)
  }

  #send() {
    if (!this.#socket || this.#unsentMsgs.length <= 0 || !this.#authOK) return
    let m: Uint8Array | undefined
    while ((m = this.#unsentMsgs.shift())) this.#sendOne(m)
  }

  #sendCall(call: Call): Call {
    this.#pendingCalls.set(call.call_id, call)
    this.#unsentMsgs.push(call.msg())
    this.#send()
    return call
  }

  #sendOne(msg: Uint8Array) {
    if (!this.#socket) return
    this.#socket.send(msg)
  }

  #socketOnError(event: unknown) {
    if (this.#timeout) return
    this.#socket = null
    this.#notifyConnected(false)
    if (this.#socketRetryBackoff <= 0) {
      this.#socketRetryBackoff = 1
      console.error('pykern-api WebSocket failed', event)
      this.#clearCalls()
    }
    if (this.#socketRetryBackoff < 60) this.#socketRetryBackoff *= 2
    this.#timeout = setTimeout(() => {
      this.#timeout = null
      this.#socketOpen()
    }, this.#socketRetryBackoff * 1000)
  }

  #socketOnMessage(buffer: ArrayBuffer) {
    const m = decode(buffer) as {
      call_id: number
      msg_kind: number
      api_error?: string
      api_result?: unknown
    }
    const c = this.#findCall(m.call_id)
    if (!c) return
    if (m.msg_kind === MSG_KIND_REPLY) {
      if (m.api_error) c.handleError(m.api_error)
      else c.handleResult(m.api_result)
    } else if (m.msg_kind === MSG_KIND_UNSUBSCRIBE) {
      if (c.isSubscription) c.handleResult(null)
      else c.handleError('unsubscribe of non-subscription')
    } else {
      c.handleError(`protocol error: invalid msg_kind=${m.msg_kind}`)
    }
  }

  #socketOnOpen() {
    this.call(
      AUTH_API_NAME,
      { token: null, version: AUTH_API_VERSION },
      this.#authResult.bind(this),
      this.#authError.bind(this),
    )
    const m = this.#unsentMsgs.pop()!
    this.#sendOne(m)
    this.#notifyConnected(true)
  }

  #socketOpen() {
    try {
      const s = new WebSocket(PYKERN_WS_URL)
      s.onclose = this.#socketOnError.bind(this)
      s.onerror = this.#socketOnError.bind(this)
      s.onmessage = (event) => {
        event.data.arrayBuffer().then(
          this.#socketOnMessage.bind(this),
          (error: unknown) => {
            console.error('pykern-api arrayBuffer decode error', error, event.data)
            this.#socketOnError(event)
          },
        )
      }
      s.onopen = this.#socketOnOpen.bind(this)
      this.#authOK = false
      this.#socket = s
    } catch (err) {
      this.#socketOnError(err)
    }
  }
}

export const pykernApiService = new APIService()

window.addEventListener('beforeunload', () => {
  pykernApiService.onDestroy()
})
