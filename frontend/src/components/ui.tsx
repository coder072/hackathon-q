import type { ButtonHTMLAttributes, ReactNode } from 'react'
import alertTriangle from '../assets/analysis/alert-triangle.svg'

type Variant = 'primary' | 'secondary'

// Figma "살핌 · 분석 실패" 53:2018 의 주요/보조 행동 버튼
const variants: Record<Variant, string> = {
  primary: 'h-[60px] bg-[#e8c840] text-[17px] font-bold text-[#111112]',
  secondary: 'h-14 border border-[#2a2a2e] bg-[#1c1c1e] text-[17px] font-medium text-[#8a8d92]',
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`flex w-full items-center justify-center rounded-full px-[18px] transition active:scale-[0.98] disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

export function Spinner({ className = 'size-12 border-4' }: { className?: string }) {
  return <div aria-hidden className={`animate-spin rounded-full border-[#2c2d2f] border-t-[#f5c842] ${className}`} />
}

export function LoadingView({ title, message, children }: { title: string; message?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 py-8 text-center">
      <Spinner />
      <div role="status">
        <p className="text-lg font-semibold text-white">{title}</p>
        {message && <p className="mt-1 text-sm text-[#6a6d72]">{message}</p>}
      </div>
      {children}
    </div>
  )
}

// 오류 헤더 (Figma "살핌 · 분석 실패" 의 아이콘 배지 + 제목 묶음)
export function ErrorHeader({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex size-[52px] items-center justify-center rounded-2xl border border-[#2e2e2e] bg-[#242424]">
        <img src={alertTriangle} alt="" width={24} height={24} />
      </div>
      <div className="flex flex-col gap-1">
        <h1 className="text-[38px] leading-[1.15] font-bold tracking-[-1.8px] whitespace-pre-line text-white">{title}</h1>
        <p className="text-[15px] leading-[1.55] text-[#6b6e72]">{message}</p>
      </div>
    </div>
  )
}

export function ErrorView({ title, message, children }: { title: string; message: string; children?: ReactNode }) {
  return (
    <div role="alert" className="flex flex-1 flex-col justify-between gap-8 px-2 pt-[max(4rem,env(safe-area-inset-top))] pb-6">
      <ErrorHeader title={title} message={message} />
      <div className="flex flex-col gap-2.5">{children}</div>
    </div>
  )
}
