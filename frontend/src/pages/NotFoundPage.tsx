import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <p className="text-slate-400">페이지를 찾을 수 없어요.</p>
      <Link to="/" className="font-semibold text-emerald-400">
        스캔 화면으로
      </Link>
    </div>
  )
}
