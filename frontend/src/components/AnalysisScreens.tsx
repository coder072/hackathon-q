import { useEffect, useState, type ReactNode } from 'react'
import backIcon from '../assets/analysis/back.svg'
import closeIcon from '../assets/analysis/close.svg'
import linkMutedIcon from '../assets/analysis/link-muted.svg'
import linkIcon from '../assets/analysis/link.svg'
import statusDot from '../assets/analysis/status-dot.svg'
import stepProgress from '../assets/analysis/step-progress.svg'
import { ErrorHeader } from './ui'

function hostOf(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

function AnalysisNav({ title, titleClassName, onBack, onClose }: { title: string; titleClassName: string; onBack: () => void; onClose: () => void }) {
  return (
    <nav className="-mx-4 flex h-[76px] shrink-0 items-center justify-between px-5">
      <button type="button" onClick={onBack} aria-label="뒤로가기" className="flex size-11 items-center">
        <img src={backIcon} alt="" width={24} height={24} />
      </button>
      <p className={`text-[14px] ${titleClassName}`}>{title}</p>
      <button type="button" onClick={onClose} aria-label="닫기" className="flex size-11 items-center justify-end">
        <img src={closeIcon} alt="" width={24} height={24} />
      </button>
    </nav>
  )
}

// 연결될 주소 패널: 링크로 만들지 않고 텍스트로만 보여 준다 (RST-003)
function UrlPanel({ url, variant }: { url: string; variant: 'analyzing' | 'failed' }) {
  const failed = variant === 'failed'
  return (
    <div
      className={`flex w-full flex-col border ${
        failed ? 'gap-2 rounded-[20px] border-[#2a2a2e] bg-[#1c1c1e] px-5 py-[18px]' : 'gap-3 rounded-[24px] border-[#2c2d2f] bg-[#1a1b1c] p-5'
      }`}
    >
      <div className="flex items-center justify-between">
        <p className={failed ? 'text-[12px] tracking-[0.2px] text-[#4a4d52]' : 'text-[13px] text-[#5a5d62]'}>연결될 주소</p>
        {failed ? <img src={linkMutedIcon} alt="" width={18} height={18} /> : <img src={linkIcon} alt="" width={20} height={20} />}
      </div>
      <p className="text-[20px] font-bold tracking-[-0.6px] break-all text-white">{hostOf(url)}</p>
      <p className={`text-[13px] break-all ${failed ? 'leading-normal text-[#4a4d52]' : 'leading-[1.55] text-[#5a5d62]'}`}>{url}</p>
    </div>
  )
}

const STEPS = ['주소 형식·경로 추출', '위험 패턴 확인', '신호 점수 계산']
// 서버 진행률이 아니라 기다리는 동안 보여 주는 단계 안내 (응답이 오면 바로 다음 화면으로 넘어간다)
const STEP_DELAYS_MS = [500, 1500]

function useStepProgress() {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const timers = STEP_DELAYS_MS.map((ms, i) => setTimeout(() => setStep(i + 1), ms))
    return () => timers.forEach(clearTimeout)
  }, [])
  return step
}

function StepRow({ index, label, state }: { index: number; label: string; state: 'done' | 'active' | 'waiting' }) {
  return (
    <div className="flex items-center gap-3.5 py-3.5">
      {state === 'done' ? (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-[14px] border border-[#2e4a1a] bg-[#1e2a14] text-[13px] font-bold text-[#7ec845]">
          ✓
        </div>
      ) : state === 'active' ? (
        <img src={stepProgress} alt="" width={28} height={28} className="shrink-0 animate-pulse" />
      ) : (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-[14px] border border-[#2c2d2f] bg-[#1a1b1c] text-[13px] text-white">
          —
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="text-[11px] text-white">{String(index + 1).padStart(2, '0')}</p>
        <p className={`text-[15px] ${state === 'done' ? 'text-[#7a7d82]' : state === 'active' ? 'font-bold text-white' : 'text-white'}`}>{label}</p>
      </div>
      <p
        className={`shrink-0 text-[12px] ${state === 'done' ? 'text-[#7ec845]' : state === 'active' ? 'font-semibold text-[#f5c842]' : 'text-white'}`}
      >
        {state === 'done' ? '완료' : state === 'active' ? '분석 중' : '대기'}
      </p>
    </div>
  )
}

// SCR-002 분석 중 (Figma "살핌 · 분석 중" 53:1857)
export function AnalyzingView({ url, onBack, onClose }: { url: string; onBack: () => void; onClose: () => void }) {
  const step = useStepProgress()
  const stateOf = (i: number) => (i < step ? 'done' : i === step ? 'active' : 'waiting')

  return (
    <div className="-mx-4 flex flex-1 flex-col bg-[#111213] px-4 pb-10">
      <AnalysisNav title="주소 분석" titleClassName="text-white" onBack={onBack} onClose={onClose} />

      <div className="flex flex-col gap-2.5 px-2 pt-2 pb-7">
        <div className="flex w-fit items-center gap-2 rounded-[20px] border border-[#f5c842] bg-[#1e2010] px-3 py-1.5">
          <img src={statusDot} alt="" width={7} height={7} className="animate-pulse" />
          <p className="text-[13px] font-medium text-[#f5c842]">분석 진행 중</p>
        </div>
        <h1 role="status" className="text-[32px] leading-[1.18] font-bold tracking-[-1.2px] text-white">
          주소의 신호를
          <br />
          살펴보고 있어요.
        </h1>
        <p className="text-[15px] leading-normal text-[#6a6d72]">아직 분석 결과가 나오지 않았어요.</p>
      </div>

      <div className="flex flex-col gap-3">
        <UrlPanel url={url} variant="analyzing" />

        <div className="flex flex-col gap-5 rounded-[24px] border border-[#2c2d2f] bg-[#1a1b1c] p-5">
          <div className="flex items-center justify-between">
            <p className="text-[18px] font-bold tracking-[-0.5px] text-white">주소를 분석하는 중</p>
            <p className="flex gap-1 text-[13px]">
              <span className="font-semibold text-[#f5c842]">{step + 1}</span>
              <span className="text-[#3a3d42]">/</span>
              <span className="text-white">{STEPS.length}</span>
            </p>
          </div>

          <div className="flex flex-col divide-y divide-[#222326]">
            {STEPS.map((label, i) => (
              <StepRow key={label} index={i} label={label} state={stateOf(i)} />
            ))}
          </div>

          <div className="flex gap-[5px]">
            {STEPS.map((label, i) => (
              <div
                key={label}
                className={`h-[3px] flex-1 rounded-[2px] transition-colors duration-300 ${
                  i < step ? 'bg-[#f5c842]' : i === step ? 'bg-[#f5c842]/35' : 'bg-[#2c2d2f]'
                }`}
              />
            ))}
          </div>

          <div className="flex flex-col gap-[5px] rounded-2xl border border-[#222326] bg-[#141516] px-4 py-3.5">
            <p className="text-[14px] leading-[1.45] font-semibold text-white">사이트를 열지 않고 확인해요.</p>
            <p className="text-[13px] leading-normal text-[#5a5d62]">링크는 이 기기에서 열리지 않아요. 주소와 이동 경로만 살펴봐요.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// SCR-002 분석 실패 (Figma "살핌 · 분석 실패" 53:2018)
export function AnalysisFailedView({
  url,
  causeTitle,
  causeMessage,
  onBack,
  onClose,
  children,
}: {
  url: string
  causeTitle: string
  causeMessage: string
  onBack: () => void
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div role="alert" className="-mx-4 flex flex-1 flex-col bg-[#111112] px-4">
      <AnalysisNav title="분석 실패" titleClassName="text-[#6b6e72]" onBack={onBack} onClose={onClose} />

      <div className="flex flex-1 flex-col gap-5 px-2 pt-7 pb-9">
        <ErrorHeader title={'분석을\n마칠 수 없어요'} message="주소는 읽었지만 위험 신호를 평가하지 못했어요." />

        <UrlPanel url={url} variant="failed" />

        <div className="relative flex gap-3 rounded-[20px] border border-[#2a2a2e] bg-[#1c1c1e] py-4 pr-[18px] pl-7">
          <span aria-hidden className="absolute top-[23px] left-[17px] size-[3px] rounded-[2px] bg-[#6b6e72]" />
          <div className="flex flex-col gap-1.5">
            <p className="text-[15px] font-semibold tracking-[-0.3px] text-white">{causeTitle}</p>
            <p className="text-[14px] leading-[1.55] text-[#6b6e72]">{causeMessage}</p>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-2xl bg-[#1c1c1e] py-4 pr-[18px] pl-7">
          <span aria-hidden className="absolute top-0 left-0 h-[52px] w-[3px] rounded-[2px] bg-[#e8c840]" />
          <p className="text-[14px] leading-[1.45] font-semibold text-[#e8c840]">분석 실패는 낮은 위험이 아니에요.</p>
          <p className="mt-1 text-[13px] leading-normal text-[#6b6e72]">점수와 판정을 제공할 수 없어요. 확인되지 않은 링크는 열지 않는 편이 좋아요.</p>
        </div>
      </div>

      <div className="flex flex-col gap-2.5 px-2 pt-2 pb-6">{children}</div>
    </div>
  )
}
