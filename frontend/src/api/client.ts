import type { ApiErrorBody, ApiSuccess, ErrorCode } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  readonly code: ErrorCode
  readonly status: number
  readonly requestId: string | null

  constructor(code: ErrorCode, message: string, status = 0, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.requestId = requestId
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

export async function request<T>(path: string, { method = 'GET', body, signal }: RequestOptions = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': crypto.randomUUID(),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    // PWA-004: 네트워크 오류는 절대 안전 판정으로 이어지지 않도록 별도 코드로 던진다
    throw new ApiError('NETWORK_ERROR', '분석 서버에 연결할 수 없습니다.')
  }

  let json: ApiSuccess<T> | ApiErrorBody
  try {
    json = await res.json()
  } catch {
    throw new ApiError('UNKNOWN_ERROR', '서버 응답을 해석할 수 없습니다.', res.status)
  }

  if (!res.ok || !json.success) {
    const { error, requestId } = json as ApiErrorBody
    throw new ApiError(error?.code ?? 'UNKNOWN_ERROR', error?.message ?? '알 수 없는 오류입니다.', res.status, requestId)
  }

  return json.data
}
