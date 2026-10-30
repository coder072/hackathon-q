import { useState, type FormEvent } from 'react'
import arrowUpward from '../assets/caution/arrow-upward.svg'

const MAX_LENGTH = 300

interface CautionSummaryModalProps {
  score: number
  submitting: boolean
  // 추가 질문(NEEDS_CLARIFICATION) 또는 오류 안내
  notice: { tone: 'question' | 'error'; text: string } | null
  onSubmit: (message: string) => Promise<boolean>
  onSkip: () => void
}

// 4~6점 분석 직후 로딩 화면 위에 뜨는 요약 모달 (Figma "Caution summary" 79:12)
export function CautionSummaryModal({ score, submitting, notice, onSubmit, onSkip }: CautionSummaryModalProps) {
  const [message, setMessage] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const value = message.trim()
    if (!value || submitting) return
    // 다시 입력이 필요한 경우(추가 질문·민감정보)에는 입력을 비운다
    if (await onSubmit(value)) setMessage('')
  }

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center">
      <div aria-hidden className="absolute inset-0 bg-black/60" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="caution-summary-title"
        className="relative mx-2 mb-[max(0.5rem,env(safe-area-inset-bottom))] flex w-full max-w-md flex-col gap-[18px] rounded-[40px] bg-[#1b1c1d] px-6 py-10"
      >
        <h2 id="caution-summary-title" className="text-[32px] leading-[1.12] font-semibold tracking-[-2.2px] text-white">
          <span className="block">주의가 필요한</span>
          <span className="block">링크예요.</span>
        </h2>

        <div className="flex items-center justify-between gap-4 whitespace-nowrap">
          <div className="flex flex-col gap-1">
            <p className="text-[17px] text-white">위험 신호 점수</p>
            <p className="text-[13px] text-[#a9acae]">4점 이상은 주의가 필요해요</p>
          </div>
          <p className="tracking-[-2px]">
            <span className="text-[43px] font-medium text-[#f5c842]">{score}</span>
            <span className="text-[18px] text-[#a9acae]"> / 10</span>
          </p>
        </div>

        <form onSubmit={submit} className="flex h-[60px] w-full items-center rounded-full bg-white pr-[18px] pl-6">
          <input
            aria-label="방문 목적"
            className="min-w-0 flex-1 bg-transparent text-[16px] leading-[1.12] font-semibold tracking-[-1px] text-[#101112] outline-none placeholder:text-[#62656a] disabled:opacity-60"
            placeholder="어떤 목적으로 이 사이트를 방문하나요?"
            maxLength={MAX_LENGTH}
            value={message}
            disabled={submitting}
            onChange={(e) => setMessage(e.target.value)}
            autoFocus
          />
          <button
            type="submit"
            aria-label="목적 보내기"
            disabled={submitting || !message.trim()}
            className="flex size-10 shrink-0 items-center justify-center disabled:opacity-40"
          >
            {submitting ? (
              <span aria-hidden className="size-5 animate-spin rounded-full border-2 border-[#d4d5d7] border-t-[#62656a]" />
            ) : (
              <img src={arrowUpward} alt="" width={24} height={24} />
            )}
          </button>
        </form>

        <div role="status" className="flex flex-col gap-2 text-[13px] leading-[1.5]">
          {submitting ? (
            <p className="text-[#a9acae]">AI가 목적과 링크를 비교하고 있어요…</p>
          ) : notice ? (
            <p className={notice.tone === 'error' ? 'text-[#ff8a65]' : 'text-[#f5c842]'}>{notice.text}</p>
          ) : (
            <p className="text-[#a9acae]">비밀번호·인증번호·계좌번호 같은 민감한 정보는 입력하지 마세요.</p>
          )}
          <button type="button" onClick={onSkip} className="self-start text-[#a9acae] underline underline-offset-4">
            목적 입력 없이 결과 보기
          </button>
        </div>
      </div>
    </div>
  )
}
