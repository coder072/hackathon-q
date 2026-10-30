import QrScanner from 'qr-scanner'
import { useEffect, useRef, useState } from 'react'

export type ScannerError = 'PERMISSION_DENIED' | 'NO_CAMERA' | 'NOT_DETECTED' | 'UNKNOWN'

interface Options {
  onDecode: (text: string) => void
  enabled?: boolean
  // 값이 바뀌면 카메라를 다시 시작한다 (다시 시도)
  restartKey?: number
  // 이 시간 안에 QR 을 찾지 못하면 NOT_DETECTED
  detectTimeoutMs?: number
}

// QR-001 권한 요청, QR-002 후면 카메라 우선, QR-003 실시간 인식, QR-004 중복 인식 방지
export function useQrScanner({ onDecode, enabled = true, restartKey = 0, detectTimeoutMs = 20_000 }: Options) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const onDecodeRef = useRef(onDecode)
  // 다시 시도하면 이전 시도의 오류가 보이지 않도록 어느 시도의 오류인지 함께 둔다
  const [failure, setFailure] = useState<{ key: number; error: ScannerError } | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    onDecodeRef.current = onDecode
  })

  useEffect(() => {
    const video = videoRef.current
    if (!enabled || !video) return

    let scanner: QrScanner | null = null
    let detectTimer: ReturnType<typeof setTimeout> | undefined
    // 스캐너 생성을 한 틱 미룬다. StrictMode(개발 모드)는 effect 를 생성→정리→생성으로 두 번 실행하는데,
    // qr-scanner 의 destroy 는 300ms 뒤에 <video> 의 스트림을 끄므로 같은 <video> 에 붙은 새 스트림까지
    // 꺼 버린다(권한이 이미 허용된 두 번째 스캔부터 카메라가 안 켜짐, #24). 첫 실행은 생성 전에 취소된다.
    const timer = setTimeout(() => {
      let handled = false
      const instance = new QrScanner(
        video,
        ({ data }) => {
          if (handled || !data) return
          handled = true
          clearTimeout(detectTimer)
          instance.stop()
          onDecodeRef.current(data)
        },
        // 스캔 영역 표시는 화면의 Figma 프레임이 맡는다
        { preferredCamera: 'environment', highlightScanRegion: false, highlightCodeOutline: false, maxScansPerSecond: 10 },
      )
      scanner = instance

      instance
        .start()
        .then(() => {
          setReady(true)
          detectTimer = setTimeout(() => {
            if (handled) return
            handled = true
            instance.stop()
            setFailure({ key: restartKey, error: 'NOT_DETECTED' })
          }, detectTimeoutMs)
        })
        .catch((err: unknown) => {
          const name = err instanceof DOMException ? err.name : String(err)
          const error: ScannerError =
            name === 'NotAllowedError' || name === 'SecurityError'
              ? 'PERMISSION_DENIED'
              : name === 'NotFoundError' || /camera not found/i.test(name)
                ? 'NO_CAMERA'
                : 'UNKNOWN'
          setFailure({ key: restartKey, error })
        })
    }, 0)

    return () => {
      clearTimeout(timer)
      clearTimeout(detectTimer)
      scanner?.destroy()
      setReady(false)
    }
  }, [enabled, restartKey, detectTimeoutMs])

  const error = failure?.key === restartKey ? failure.error : null
  return { videoRef, error, ready }
}
