import QrScanner from 'qr-scanner'
import { useEffect, useRef, useState } from 'react'

export type ScannerError = 'PERMISSION_DENIED' | 'NO_CAMERA' | 'UNKNOWN'

interface Options {
  onDecode: (text: string) => void
  enabled?: boolean
}

// QR-001 권한 요청, QR-002 후면 카메라 우선, QR-003 실시간 인식, QR-004 중복 인식 방지
export function useQrScanner({ onDecode, enabled = true }: Options) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const onDecodeRef = useRef(onDecode)
  const [error, setError] = useState<ScannerError | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    onDecodeRef.current = onDecode
  })

  useEffect(() => {
    const video = videoRef.current
    if (!enabled || !video) return

    let scanner: QrScanner | null = null
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
          instance.stop()
          onDecodeRef.current(data)
        },
        { preferredCamera: 'environment', highlightScanRegion: true, highlightCodeOutline: true, maxScansPerSecond: 10 },
      )
      scanner = instance

      instance
        .start()
        .then(() => setReady(true))
        .catch((err: unknown) => {
          const name = err instanceof DOMException ? err.name : String(err)
          if (name === 'NotAllowedError' || name === 'SecurityError') setError('PERMISSION_DENIED')
          else if (name === 'NotFoundError' || /camera not found/i.test(name)) setError('NO_CAMERA')
          else setError('UNKNOWN')
        })
    }, 0)

    return () => {
      clearTimeout(timer)
      scanner?.destroy()
      setReady(false)
    }
  }, [enabled])

  return { videoRef, error, ready }
}
