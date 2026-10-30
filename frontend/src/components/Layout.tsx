import { Link, Outlet } from 'react-router'
import { useOnlineStatus } from '../hooks/useOnlineStatus'

export function Layout() {
  const online = useOnlineStatus()
  const secure = window.isSecureContext

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between px-4 py-3">
        <Link to="/" className="text-lg font-bold">
          🛡️ QR 안심스캔
        </Link>
        <Link to="/install" className="text-sm text-slate-400">
          앱 설치
        </Link>
      </header>
      {!online && (
        <div role="alert" className="bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950">
          ⚠️ 오프라인 상태예요. 연결되기 전까지 링크 안전 여부를 확인할 수 없어요.
        </div>
      )}
      {!secure && (
        <div role="alert" className="bg-red-500 px-4 py-2 text-sm font-medium text-white">
          🔒 HTTPS 연결이 아니어서 카메라와 앱 설치 기능을 사용할 수 없어요.
        </div>
      )}
      <main className="flex flex-1 flex-col px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Outlet />
      </main>
    </div>
  )
}
