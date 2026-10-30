import { useLayoutEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'
import type { AnalysisResult, CheckCode } from '../api'
import type { RiskTier } from '../lib/verdict'
import { AlertCircleIcon, ArrowLeftIcon, LinkIcon, XIcon } from './icons'

const CHECK_TITLES: Partial<Record<CheckCode, string>> = {
  HTTPS_NOT_USED: '암호화되지 않은 연결',
  LOOKALIKE_DOMAIN: '유사 도메인 의심',
  SUSPICIOUS_URL_STRUCTURE: '수상한 주소 구조',
  DIRECT_IP_ACCESS: 'IP 주소 직접 접속',
  EXCESSIVE_REDIRECTS: '과도한 리디렉션',
  BLOCKLIST_MATCH: '피싱 차단 목록',
  ALLOWLIST_MATCH: '검증된 공식 도메인',
}

interface VariantConfig {
  headline: [string, string]
  scoreLabel: string
  scoreCaption: string
  accentColor: string
  glow: string
  evidenceTitle: string
  advice: string
  adviceNote: string
  primaryLabel: string
  primaryIcon?: boolean
  primaryTone: 'accent' | 'dark'
  secondaryLabel: string
}

const VARIANTS: Record<RiskTier, VariantConfig> = {
  SAFE: {
    headline: ['안전한', '링크예요'],
    scoreLabel: '안전 · 낮은 위험 신호',
    scoreCaption: '4점 이상부터 주의가 필요해요',
    accentColor: '#3b82f6',
    glow: 'radial-gradient(closest-side, rgba(224,242,255,0.95) 0%, rgba(96,165,250,0.85) 26%, rgba(37,99,235,0.7) 52%, rgba(30,27,75,0.45) 72%, rgba(10,10,20,0) 88%)',
    evidenceTitle: '확인한 점',
    advice: '낮은 점수가 안전을 보장하진 않아요.\n정보를 입력하기 전 출처를 확인하세요.',
    adviceNote: '주소 문자열을 분석한 결과예요.\n실제 페이지나 운영자를 확인한 것은 아니에요.',
    primaryLabel: '이동하기',
    primaryTone: 'accent',
    secondaryLabel: '처음으로',
  },
  AMBIGUOUS: {
    headline: ['주의가 필요한', '링크예요.'],
    scoreLabel: '위험 신호 점수',
    scoreCaption: '원래 링크는 열지 않도록 막았어요',
    accentColor: '#f5c842',
    glow: 'radial-gradient(closest-side, rgba(255,246,214,0.95) 0%, rgba(250,204,21,0.85) 24%, rgba(234,88,12,0.7) 50%, rgba(124,45,18,0.5) 72%, rgba(10,10,20,0) 88%)',
    evidenceTitle: '살펴볼 신호',
    advice: '원래 링크 대신\n검증된 공식 사이트로만 이동하세요.',
    adviceNote: '주소에서 확인한 신호의 결과이며\n실제 페이지의 요청을 확인한 것은 아니에요.',
    primaryLabel: '열지 않고 종료',
    primaryIcon: true,
    primaryTone: 'dark',
    secondaryLabel: '목적 다시 입력하기',
  },
  HIGH: {
    headline: ['링크 열기가', '차단됐어요.'],
    scoreLabel: '차단 판정',
    scoreCaption: '위험 신호가 높아 자동으로 차단됐어요',
    accentColor: '#ff5a1f',
    glow: 'radial-gradient(closest-side, rgba(255,241,168,0.95) 0%, rgba(255,138,30,0.88) 22%, rgba(220,38,38,0.75) 48%, rgba(127,29,29,0.55) 70%, rgba(10,10,20,0) 88%)',
    evidenceTitle: '살펴볼 신호',
    advice: '로그인·카드 정보를 요구할 수 있어요.\n입력 전 출처를 따로 확인하세요.',
    adviceNote: '주소에서 확인한 신호의 결과이며\n실제 페이지의 요청을 확인한 것은 아니에요.',
    primaryLabel: '처음으로',
    primaryIcon: true,
    primaryTone: 'dark',
    secondaryLabel: '신고 방법 보기',
  },
}

const COLLAPSED_RATIO = 0.42 // 카드가 기본(collapsed) 상태에서 화면 아래쪽부터 덮는 비율. 나머지 위쪽엔 배경 그라데이션만 보임
const MAX_RADIUS = 40

// 카드를 드래그로 올리고(expanded) 내리는(collapsed) 바텀시트 동작
function useDragSheet() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [collapsedTop, setCollapsedTop] = useState(0)
  const [topPx, setTopPx] = useState(0)
  const [expanded, setExpanded] = useState(false)
  const [dragging, setDragging] = useState(false)
  const drag = useRef<{ startY: number; startTop: number } | null>(null)

  useLayoutEffect(() => {
    const measure = () => {
      const h = containerRef.current?.clientHeight ?? 0
      const top = h * (1 - COLLAPSED_RATIO)
      setCollapsedTop(top)
      setTopPx(expanded ? 0 : top)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [expanded])

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    drag.current = { startY: e.clientY, startTop: topPx }
    setDragging(true)
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!drag.current) return
    const next = drag.current.startTop + (e.clientY - drag.current.startY)
    setTopPx(Math.min(Math.max(next, 0), collapsedTop))
  }
  const onPointerUp = () => {
    if (!drag.current) return
    const next = topPx < collapsedTop / 2
    setExpanded(next)
    setTopPx(next ? 0 : collapsedTop)
    drag.current = null
    setDragging(false)
  }

  const progress = collapsedTop > 0 ? 1 - topPx / collapsedTop : 1 // 0=collapsed, 1=expanded

  return {
    containerRef,
    topPx,
    dragging,
    radius: MAX_RADIUS * (1 - progress),
    handlers: { onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp },
  }
}

interface ResultScreenProps {
  analysis: AnalysisResult
  tier: RiskTier
  onBack: () => void
  onClose: () => void
  onPrimaryAction: () => void
  onSecondaryAction: () => void
  secondaryLabel?: string
  scoreCaption?: string
  children?: ReactNode
}

// SCR-003/004 결과 화면: 안전·주의·차단 공통 레이아웃 (Figma node 67:608 / 62:491 / 67:708 / 70:808)
// 카드는 드래그로 올리고 내릴 수 있는 바텀시트: 내리면(collapsed) 뒤 그라데이션이 보이고, 올리면(expanded) 전체를 덮는다.
export function ResultScreen({ analysis, tier, onBack, onClose, onPrimaryAction, onSecondaryAction, secondaryLabel, scoreCaption, children }: ResultScreenProps) {
  const v = VARIANTS[tier]
  // 점수가 붙은 신호를 먼저 보여 준다. 안전 결과는 1~3점이어도 감점 근거가 보이도록 통과한 항목을 뒤에 붙인다
  const scoredChecks = analysis.checks.filter((c) => c.detected && c.score > 0)
  const evidenceChecks =
    tier === 'SAFE' ? [...scoredChecks, ...analysis.checks.filter((c) => !scoredChecks.includes(c))] : scoredChecks
  const { containerRef, topPx, dragging, radius, handlers } = useDragSheet()

  return (
    <div ref={containerRef} className="-mx-4 relative flex-1 overflow-hidden bg-[#1b1c1d]">
      <div aria-hidden className="result-glow-wrap">
        <div className="result-glow" style={{ background: v.glow }} />
      </div>

      <nav className="absolute inset-x-0 top-0 z-20 flex h-11 items-center justify-between px-6 pt-3">
        <button type="button" onClick={onBack} aria-label="뒤로가기" className="-ml-2 flex size-11 items-center justify-center">
          <ArrowLeftIcon className="size-6 text-white" />
        </button>
        <p className="text-sm text-white">분석결과</p>
        <button type="button" onClick={onClose} aria-label="닫기" className="-mr-2 flex size-11 items-center justify-center">
          <XIcon className="size-6 text-white" />
        </button>
      </nav>

      <div
        className="absolute inset-x-0 bottom-0 z-10 flex flex-col overflow-y-auto overscroll-contain bg-[#1b1c1d]"
        style={{
          top: topPx,
          borderTopLeftRadius: radius,
          borderTopRightRadius: radius,
          transition: dragging ? 'none' : 'top 0.35s cubic-bezier(0.16,1,0.3,1), border-radius 0.35s ease',
        }}
      >
        <div
          className="flex shrink-0 touch-none flex-col gap-[18px] px-6 pt-5 pb-[26px] select-none"
          style={{ touchAction: 'none' }}
          onPointerDown={handlers.onPointerDown}
          onPointerMove={handlers.onPointerMove}
          onPointerUp={handlers.onPointerUp}
          onPointerCancel={handlers.onPointerCancel}
        >
          <div className="mx-auto h-1 w-10 shrink-0 rounded-full bg-white/25" />
          <h1 className="text-[44px] leading-[1.12] font-semibold tracking-[-2.2px] text-white">
            <span className="block">{v.headline[0]}</span>
            <span className="block">{v.headline[1]}</span>
          </h1>
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-1">
              <p className="text-[17px] text-white">{v.scoreLabel}</p>
              <p className="text-[13px] text-[#a9acae]">{scoreCaption ?? v.scoreCaption}</p>
            </div>
            {tier === 'HIGH' ? (
              <p className="text-[43px] font-medium tracking-[-2px]" style={{ color: v.accentColor }}>
                차단
              </p>
            ) : (
              <p className="tracking-[-2px]">
                <span className="text-[43px] font-medium" style={{ color: v.accentColor }}>
                  {analysis.score}
                </span>
                <span className="text-[18px] text-[#a9acae]"> / 10</span>
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-4 px-5 pb-8">
          <div className="rounded-[36px] bg-white p-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-[#62656a]">연결될 주소</p>
              <LinkIcon className="size-5 text-[#62656a]" />
            </div>
            <p className="mt-[10px] w-full text-2xl font-semibold break-all tracking-[-0.9px] text-[#101112]">{analysis.displayDomain}</p>
            <p className="mt-2 w-full text-[15px] leading-[1.5] break-all text-[#62656a]">{analysis.originalUrl}</p>
            {analysis.redirectCount > 0 && (
              <p className="mt-2 w-full text-xs break-all text-[#62656a]">
                리디렉션 {analysis.redirectCount}회 → {analysis.finalUrl}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-[23px] rounded-[36px] bg-white p-6">
            <div className="flex flex-col gap-5">
              <div className="flex items-center justify-between">
                <p className="text-2xl font-semibold tracking-[-1px] text-[#101112]">{v.evidenceTitle}</p>
                <p className="text-sm text-[#62656a]">{evidenceChecks.length}개</p>
              </div>
              {evidenceChecks.map((check) => (
                <div key={check.code} className="flex items-start gap-3">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-[14px] bg-[#101112]">
                    <AlertCircleIcon className="size-4 text-white" />
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-[6px]">
                    <p className="text-[19px] font-semibold text-[#101112]">{CHECK_TITLES[check.code] ?? check.code}</p>
                    <p className="text-[17px] leading-[1.45] text-[#62656a]">{check.message}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2 rounded-[22px] bg-[#f4f4f4] p-4">
              <div className="text-[17px] leading-[1.45] font-medium text-[#101112]">
                {v.advice.split('\n').map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
              <div className="text-[14px] leading-[1.45] text-[#62656a]">
                {v.adviceNote.split('\n').map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-[10px]">
              <button
                type="button"
                onClick={onPrimaryAction}
                style={v.primaryTone === 'accent' ? { backgroundColor: v.accentColor } : undefined}
                className={`flex h-[60px] w-full items-center justify-center gap-3 rounded-full px-[22px] text-[18px] font-semibold text-white transition active:scale-[0.98] ${
                  v.primaryTone === 'dark' ? 'border border-[#101112] bg-[#101112]' : ''
                }`}
              >
                {v.primaryIcon && <XIcon className="size-6" />}
                {v.primaryLabel}
              </button>
              <button
                type="button"
                onClick={onSecondaryAction}
                className="flex h-[60px] w-full items-center justify-center rounded-full border border-[#e0e1e2] bg-white px-[22px] text-[18px] font-semibold text-[#101112] transition active:scale-[0.98]"
              >
                {secondaryLabel ?? v.secondaryLabel}
              </button>
            </div>
          </div>

          {children}
        </div>
      </div>
    </div>
  )
}
