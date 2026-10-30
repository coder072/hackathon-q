import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button, ErrorView } from '../components/ui'
import { useQrScanner } from '../hooks/useQrScanner'
import { isHttpUrl } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// SCR-001 시작/스캔 화면
export function ScanPage() {
  const navigate = useNavigate()
  const { setScannedUrl } = useScanFlow()
  const [nonUrlText, setNonUrlText] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  const { videoRef, error, ready } = useQrScanner({
    enabled: nonUrlText === null,
    onDecode: (text) => {
      // QR-006: URL 이 아니면 분석하지 않고 내용만 표시
      if (!isHttpUrl(text)) {
        setNonUrlText(text)
        return
      }
      setScannedUrl(text.trim())
      navigate('/analyzing')
    },
  })

  if (error) {
    return (
      <ErrorView
        title={error === 'PERMISSION_DENIED' ? '카메라 권한이 필요해요' : '카메라를 사용할 수 없어요'}
        message={
          error === 'PERMISSION_DENIED'
            ? '브라우저 설정에서 이 사이트의 카메라 권한을 허용한 뒤 다시 시도해 주세요.'
            : '카메라를 찾지 못했거나 다른 앱이 사용 중이에요.'
        }
      >
        <Button onClick={() => window.location.reload()}>다시 시도</Button>
      </ErrorView>
    )
  }

  if (nonUrlText !== null) {
    return (
      <div className="flex flex-1 flex-col gap-4 py-6">
        <h1 className="text-xl font-bold">ℹ️ 링크가 아닌 QR 코드예요</h1>
        <p className="text-sm text-slate-400">웹 주소가 아니어서 피싱 분석을 하지 않았어요. 내용을 직접 확인해 주세요.</p>
        <pre className="max-h-60 overflow-auto rounded-xl bg-slate-900 p-4 text-sm break-all whitespace-pre-wrap">{nonUrlText}</pre>
        <Button
          onClick={() => {
            setNonUrlText(null)
            setAttempt((n) => n + 1)
          }}
        >
          다시 스캔
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-4 py-4">
      <div className="relative aspect-square overflow-hidden rounded-2xl bg-black">
        <video key={attempt} ref={videoRef} className="h-full w-full object-cover" muted playsInline />
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-400">카메라 준비 중…</div>
        )}
      </div>
      <p className="text-center text-slate-300">QR 코드를 사각형 안에 맞춰 주세요</p>
      <p className="text-center text-xs text-slate-500">
        링크는 자동으로 열리지 않아요. 먼저 안전한지 확인한 뒤 알려드릴게요.
        <br />
        카메라 영상은 서버로 전송되지 않습니다.
      </p>
    </div>
  )
}
