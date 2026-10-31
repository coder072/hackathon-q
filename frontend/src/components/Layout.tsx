import { Outlet } from 'react-router'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { useServerHealth } from '../hooks/useServerHealth'

export function Layout() {
  const online = useOnlineStatus()
  const health = useServerHealth(online)

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col bg-[#111213] text-white">
      {!online && (
        <div role="alert" className="bg-[#e8c840] px-4 py-2 text-sm font-medium text-[#111112]">
          ⚠️ 오프라인 상태예요. 연결되기 전까지 링크 안전 여부를 확인할 수 없어요.
        </div>
      )}
      {online && (health === 'DOWN' || health === 'DEGRADED') && (
        <div role="alert" className="bg-[#e8c840] px-4 py-2 text-sm font-medium text-[#111112]">
          {health === 'DOWN'
            ? '⚠️ 분석 서버에 연결할 수 없어요. 지금은 링크 안전 여부를 확인할 수 없어요.'
            : '⚠️ 분석 서버가 불안정해요. 분석이 느리거나 실패할 수 있어요.'}
        </div>
      )}
      <main className="flex flex-1 flex-col px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Outlet />
      </main>
    </div>
  )
}
