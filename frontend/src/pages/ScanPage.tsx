import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import closeIcon from '../assets/scan/close.svg'
import scanCorners from '../assets/scan/scan-corners.svg'
import { ManualUrlForm } from '../components/ManualUrlForm'
import { useQrScanner, type ScannerError } from '../hooks/useQrScanner'
import { isHttpUrl } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// QR 을 찾은 뒤 프레임이 줄어드는 애니메이션을 보여 주는 시간
const LOCK_ANIMATION_MS = 450

const FAILURE_BODY: Record<ScannerError, string> = {
  PERMISSION_DENIED: '브라우저 설정에서 카메라 권한을 허용하고\n다시 시도해 주세요.',
  NO_CAMERA: '카메라를 찾지 못했거나\n다른 앱이 사용 중이에요.',
  NOT_DETECTED: '카메라 권한과 주변 밝기를 확인하고\nQR 코드에 다시 맞춰주세요.',
  UNKNOWN: '카메라 권한과 주변 밝기를 확인하고\nQR 코드에 다시 맞춰주세요.',
}

// 스캔 프레임 안에 뜨는 안내 카드 (Figma "인식 실패 안내" 94:127)
function ScanCard({
  title,
  children,
  primaryLabel,
  onPrimary,
  onClose,
}: {
  title: string
  children: ReactNode
  primaryLabel: string
  onPrimary: () => void
  onClose: () => void
}) {
  return (
    <div
      role="alertdialog"
      aria-label={title.replace('\n', ' ')}
      className="relative flex min-h-[269px] w-[269px] flex-col items-center justify-center gap-[13px] rounded-[22px] bg-[#424149] px-[18px] py-5 text-center"
    >
      <p className="w-full text-[20px] leading-[1.4] font-bold whitespace-pre-line text-[#f7f8f6]">{title}</p>
      {children}
      <div className="flex w-full gap-2">
        <button
          type="button"
          onClick={onPrimary}
          className="flex h-[43px] flex-1 items-center justify-center rounded-[10px] bg-white text-[14px] font-bold text-[#090a0d] transition active:scale-[0.98]"
        >
          {primaryLabel}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex h-[43px] w-[79px] shrink-0 items-center justify-center rounded-[10px] border border-white/40 text-[14px] font-medium text-[#f7f8f6] transition active:scale-[0.98]"
        >
          닫기
        </button>
      </div>
    </div>
  )
}

// SCR-001 시작/스캔 화면 (Figma "QR 스캔 · 정상" 94:104 / "QR 스캔 · 인식 실패" 94:126)
export function ScanPage() {
  const navigate = useNavigate()
  const { setScannedUrl } = useScanFlow()
  const [nonUrlText, setNonUrlText] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  // 닫기로 안내 카드를 내린 시도 (다시 시도하면 새 시도라 다시 보인다)
  const [dismissedAttempt, setDismissedAttempt] = useState<number | null>(null)
  // QR 을 찾은 순간: 프레임이 줄어드는 애니메이션을 보여 준 뒤 다음 단계로 넘어간다
  const [locked, setLocked] = useState(false)
  const lockTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => () => clearTimeout(lockTimer.current), [])

  const analyze = (url: string) => {
    setScannedUrl(url)
    navigate('/analyzing')
  }

  const restart = () => {
    clearTimeout(lockTimer.current)
    setLocked(false)
    setNonUrlText(null)
    setDismissedAttempt(null)
    setAttempt((n) => n + 1)
  }

  const { videoRef, error, ready } = useQrScanner({
    enabled: nonUrlText === null,
    restartKey: attempt,
    onDecode: (text) => {
      setLocked(true)
      lockTimer.current = setTimeout(() => {
        setLocked(false)
        // QR-006: URL 이 아니면 분석하지 않고 내용만 표시
        if (!isHttpUrl(text)) setNonUrlText(text)
        else analyze(text.trim())
      }, LOCK_ANIMATION_MS)
    },
  })

  const cardOpen = dismissedAttempt !== attempt && (error !== null || nonUrlText !== null)
  const failed = error !== null || nonUrlText !== null

  return (
    <div className="relative -mx-4 flex flex-1 flex-col overflow-hidden bg-[#63646b] text-[#f7f8f6]">
      <video key={attempt} ref={videoRef} className="absolute inset-0 size-full object-cover" muted playsInline />
      {!ready && <div aria-hidden className="absolute inset-0 bg-gradient-to-b from-[#696772] to-[#56555d]" />}
      {cardOpen && <div aria-hidden className="absolute inset-0 bg-[rgba(34,33,40,0.5)]" />}

      <header className="relative z-10 flex h-10 items-center justify-between pr-[10.5px] pl-[20.5px] mt-[max(65px,calc(env(safe-area-inset-top)+16px))]">
        <h1 className="text-[15.412px] leading-[1.3] font-bold">QR 스캔</h1>
        <button type="button" onClick={restart} aria-label="다시 스캔" className="size-10">
          <img src={closeIcon} alt="" width={40} height={40} />
        </button>
      </header>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center gap-2.5 py-6">
        <p className="text-center text-[13.699px] font-medium" role="status">
          {failed
            ? '카메라와 QR 코드를 확인해주세요.'
            : locked
              ? 'QR 코드를 찾았어요.'
              : ready
                ? 'QR 코드에 카메라를 맞춰주세요.'
                : '카메라를 준비하고 있어요.'}
        </p>
        <div className="relative flex size-[298px] items-center justify-center">
          {/* 카메라가 켜지면 커지고, QR 을 찾으면 살짝 줄어들며 잡히는 느낌을 준다 */}
          <img
            src={scanCorners}
            alt=""
            className={`pointer-events-none absolute top-1/2 left-1/2 -translate-1/2 transition-[scale] motion-reduce:transition-none ${
              locked
                ? 'scale-95 duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]'
                : ready && !failed
                  ? 'scale-[1.04] duration-500 ease-out'
                  : 'scale-100 duration-300 ease-out'
            }`}
          />
          {cardOpen && error !== null && (
            <ScanCard title={'QR 코드를\n인식하지 못했어요'} primaryLabel="다시 시도" onPrimary={restart} onClose={() => setDismissedAttempt(attempt)}>
              <p className="w-full text-[13px] leading-[1.6] whitespace-pre-line text-[#f7f8f6]">{FAILURE_BODY[error]}</p>
              <p className="w-full text-[11px] leading-normal text-[#e3e2e8]">아직 주소를 인식하거나 분석하지 않았어요.</p>
            </ScanCard>
          )}
          {cardOpen && nonUrlText !== null && (
            <ScanCard title={'링크가 아닌\nQR 코드예요'} primaryLabel="다시 스캔" onPrimary={restart} onClose={() => setDismissedAttempt(attempt)}>
              <p className="w-full text-[13px] leading-[1.6] text-[#f7f8f6]">웹 주소가 아니어서 분석하지 않았어요.</p>
              <pre className="max-h-20 w-full overflow-auto rounded-[10px] bg-black/20 p-2 text-left text-[11px] break-all whitespace-pre-wrap text-[#e3e2e8]">
                {nonUrlText}
              </pre>
            </ScanCard>
          )}
        </div>
      </div>

      <div className="relative z-10 flex flex-col gap-3 px-4 pb-2">
        <ManualUrlForm onSubmit={analyze} />
        <p className="text-center text-[12px] text-[#f7f8f6]">
          링크는 자동으로 열리지 않아요 · 카메라 영상은 서버로 전송되지 않아요
        </p>
      </div>
    </div>
  )
}
