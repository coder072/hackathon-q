import { useEffect, useState } from 'react'
import { api } from '../api'

export type ServerHealth = 'CHECKING' | 'UP' | 'DEGRADED' | 'DOWN'

const INTERVAL_MS = 60_000

// GET /health 로 분석 서버 상태를 주기적으로 확인한다 (온라인일 때만)
export function useServerHealth(online: boolean): ServerHealth {
  const [health, setHealth] = useState<ServerHealth>('CHECKING')

  useEffect(() => {
    if (!online) return
    const controller = new AbortController()
    const check = () =>
      api
        .health(controller.signal)
        .then(({ status }) => setHealth(status))
        .catch(() => {
          if (!controller.signal.aborted) setHealth('DOWN')
        })

    check()
    const timer = setInterval(check, INTERVAL_MS)
    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [online])

  return health
}
