import QrScanner from 'qr-scanner'
import { useEffect, useRef, useState } from 'react'

export type ScannerError = 'INSECURE_CONTEXT' | 'PERMISSION_DENIED' | 'NO_CAMERA' | 'UNKNOWN'

interface Options {
  onDecode: (text: string) => void
  enabled?: boolean
}

// QR-001 권한 요청, QR-002 후면 카메라 우선, QR-003 실시간 인식, QR-004 중복 인식 방지
export function useQrScanner({ onDecode, enabled = true }: Options) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const onDecodeRef = useRef(onDecode)
  const [error, setError] = useState<ScannerError | null>(() =>
    window.isSecureContext ? null : 'INSECURE_CONTEXT',
  )
  const [ready, setReady] = useState(false)

  useEffect(() => {
    onDecodeRef.current = onDecode
  })

  useEffect(() => {
    const video = videoRef.current
    if (!enabled || !video) return

    // PWA-003: 카메라는 HTTPS(또는 브라우저가 신뢰하는 localhost)에서만 시작한다.
    if (!window.isSecureContext) return

    let handled = false
    const scanner = new QrScanner(
      video,
      ({ data }) => {
        if (handled || !data) return
        handled = true
        scanner.stop()
        onDecodeRef.current(data)
      },
      { preferredCamera: 'environment', highlightScanRegion: true, highlightCodeOutline: true, maxScansPerSecond: 10 },
    )

    scanner
      .start()
      .then(() => setReady(true))
      .catch((err: unknown) => {
        const name = err instanceof DOMException ? err.name : String(err)
        if (name === 'NotAllowedError' || name === 'SecurityError') setError('PERMISSION_DENIED')
        else if (name === 'NotFoundError' || /camera not found/i.test(name)) setError('NO_CAMERA')
        else setError('UNKNOWN')
      })

    return () => {
      scanner.destroy()
      setReady(false)
    }
  }, [enabled])

  return { videoRef, error, ready }
}
