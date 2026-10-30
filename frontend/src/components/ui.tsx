import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger'

const variants: Record<Variant, string> = {
  primary: 'bg-emerald-500 text-slate-950 hover:bg-emerald-400',
  secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700',
  danger: 'bg-red-500 text-white hover:bg-red-400',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`w-full rounded-xl px-4 py-3 font-semibold transition disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

// NFR-005: 색상만으로 구분하지 않도록 아이콘 + 텍스트를 함께 표시
export function StatusBadge({ tone, icon, children }: { tone: 'safe' | 'danger' | 'warn'; icon: string; children: ReactNode }) {
  const tones = {
    safe: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40',
    danger: 'bg-red-500/15 text-red-300 ring-red-500/40',
    warn: 'bg-amber-500/15 text-amber-300 ring-amber-500/40',
  }
  return (
    <div className={`flex items-center gap-3 rounded-2xl p-4 ring-1 ${tones[tone]}`}>
      <span aria-hidden className="text-3xl">
        {icon}
      </span>
      <div className="text-xl font-bold">{children}</div>
    </div>
  )
}

export function LoadingView({ title, message, children }: { title: string; message?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 py-8 text-center">
      <div className="size-12 animate-spin rounded-full border-4 border-slate-700 border-t-emerald-400" aria-hidden />
      <div role="status">
        <p className="text-lg font-semibold">{title}</p>
        {message && <p className="mt-1 text-sm text-slate-400">{message}</p>}
      </div>
      {children}
    </div>
  )
}

export function ErrorView({ title, message, children }: { title: string; message: string; children?: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col justify-center gap-6 py-8">
      <StatusBadge tone="warn" icon="⚠️">
        {title}
      </StatusBadge>
      <p className="text-slate-300">{message}</p>
      <div className="flex flex-col gap-2">{children}</div>
    </div>
  )
}
