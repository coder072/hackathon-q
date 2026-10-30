import { useSyncExternalStore } from 'react'

export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

let deferredPrompt: BeforeInstallPromptEvent | null = null
const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((listener) => listener())
}

// PWA-001: 라우트 진입 전에 발생할 수 있는 설치 이벤트를 앱 시작 시점부터 보관한다.
window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault()
  deferredPrompt = event as BeforeInstallPromptEvent
  emit()
})

window.addEventListener('appinstalled', () => {
  deferredPrompt = null
  emit()
})

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return deferredPrompt
}

export function useInstallPrompt() {
  const promptEvent = useSyncExternalStore(subscribe, getSnapshot, () => null)

  const promptInstall = async () => {
    if (!promptEvent) return 'unavailable' as const
    await promptEvent.prompt()
    const { outcome } = await promptEvent.userChoice
    deferredPrompt = null
    emit()
    return outcome
  }

  return { promptEvent, promptInstall }
}
