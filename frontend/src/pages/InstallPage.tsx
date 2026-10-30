import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '../components/ui'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent)
const isStandalone = window.matchMedia('(display-mode: standalone)').matches

// SCR-008 설치 안내 (PWA-001)
export function InstallPage() {
  const navigate = useNavigate()
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault()
      setPromptEvent(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  return (
    <div className="flex flex-1 flex-col gap-4 py-6">
      <h1 className="text-xl font-bold">홈 화면에 설치하기</h1>
      {isStandalone ? (
        <p className="text-slate-300">✅ 이미 앱으로 실행 중이에요.</p>
      ) : promptEvent ? (
        <Button onClick={() => promptEvent.prompt()}>앱 설치</Button>
      ) : isIos ? (
        <ol className="list-decimal space-y-2 pl-5 text-slate-300">
          <li>Safari 하단의 공유 버튼(⬆️)을 누르세요.</li>
          <li>“홈 화면에 추가”를 선택하세요.</li>
        </ol>
      ) : (
        <p className="text-slate-300">브라우저 메뉴에서 “앱 설치” 또는 “홈 화면에 추가”를 선택하세요.</p>
      )}
      <div className="mt-auto">
        <Button variant="secondary" onClick={() => navigate(-1)}>
          닫기
        </Button>
      </div>
    </div>
  )
}
