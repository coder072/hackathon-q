import { useState, type FormEvent } from 'react'
import { isHttpUrl } from '../lib/verdict'

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
    </form>
  )
}
