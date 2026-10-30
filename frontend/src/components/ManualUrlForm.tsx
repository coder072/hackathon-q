import { useState, type FormEvent } from 'react'
import { isHttpUrl } from '../lib/verdict'

// 개발 서버에서만 보이는 점수 구간별 테스트 주소 (실제 백엔드 규칙 기준)
const DEV_SAMPLES = [
  { label: '안전 0점', url: 'https://www.naver.com' },
  { label: '의심 4점', url: 'https://naver-login.github.io' },
  { label: '의심 6점', url: 'http://naver-login.github.io/account/verify' },
  { label: '차단 10점', url: 'http://naver-login-security.com' },
]

// QR 없이(카메라가 없거나 테스트할 때) 주소를 직접 입력해 분석한다
export function ManualUrlForm({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState('')
  const [invalid, setInvalid] = useState(false)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const value = url.trim()
    if (!isHttpUrl(value)) {
      setInvalid(true)
      return
    }
    onSubmit(value)
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 rounded-[22px] bg-[#424149]/90 p-4 backdrop-blur">
      <label htmlFor="manual-url" className="text-[13px] font-medium text-[#e3e2e8]">
        QR이 없나요? 주소를 직접 입력해 보세요
      </label>
      <div className="flex gap-2">
        <input
          id="manual-url"
          type="url"
          inputMode="url"
          autoComplete="off"
          placeholder="https://example.com"
          className="h-[43px] min-w-0 flex-1 rounded-[10px] border border-white/40 bg-transparent px-3 font-mono text-sm text-[#f7f8f6] outline-none placeholder:text-[#e3e2e8]/50 focus:border-white"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value)
            setInvalid(false)
          }}
        />
        <button
          type="submit"
          disabled={!url.trim()}
          className="h-[43px] shrink-0 rounded-[10px] bg-white px-4 text-[14px] font-bold text-[#090a0d] transition active:scale-[0.98] disabled:opacity-50"
        >
          분석
        </button>
      </div>
      {invalid && <p className="text-sm text-red-300">http:// 또는 https:// 로 시작하는 주소를 입력해 주세요.</p>}
      {import.meta.env.DEV && (
        <div className="flex flex-wrap gap-2 pt-1">
          {DEV_SAMPLES.map((s) => (
            <button
              key={s.url}
              type="button"
              className="rounded-full border border-white/40 px-3 py-1 text-xs text-[#f7f8f6]"
              onClick={() => onSubmit(s.url)}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}
    </form>
  )
}
