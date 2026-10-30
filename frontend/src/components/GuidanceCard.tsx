import type { IntentGuidance } from '../api'

// 주의 결과 화면의 AI 2차 검증 결과: 서버가 검증한 공식 사이트만 이동 버튼으로 노출한다 (API-AC-05·06)
export function GuidanceCard({ guidance }: { guidance: IntentGuidance }) {
  // 방어적으로 verified 재확인
  const suggestions =
    guidance.guidanceStatus === 'MATCHED' ? guidance.suggestions.filter((s) => s.verified).slice(0, 3) : []

  if (suggestions.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded-[36px] bg-white p-6">
        <p className="text-2xl font-semibold tracking-[-1px] text-[#101112]">공식 사이트를 찾지 못했어요</p>
        <p className="text-[17px] leading-[1.45] text-[#62656a]">
          원래 링크는 계속 차단돼요. QR을 붙여 둔 곳이나 서비스 고객센터에 직접 확인해 주세요.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5 rounded-[36px] bg-white p-6">
      <div className="flex flex-col gap-1">
        <p className="text-sm text-[#62656a]">AI가 확인한 목적</p>
        <p className="text-2xl font-semibold tracking-[-1px] text-[#101112]">
          {guidance.serviceName ? `${guidance.serviceName} 공식 사이트` : '검증된 공식 사이트'}
        </p>
      </div>

      <ul className="flex flex-col gap-4">
        {suggestions.map((s) => (
          <li key={s.url} className="flex flex-col gap-2 rounded-[22px] bg-[#f4f4f4] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[19px] font-semibold text-[#101112]">{s.name}</span>
              <span className="rounded-full bg-[#3b82f6]/15 px-2 py-0.5 text-xs font-medium text-[#2563eb]">✔ 검증된 공식 사이트</span>
            </div>
            <p className="font-mono text-sm break-all text-[#62656a]">{s.domain}</p>
            <p className="text-[15px] leading-[1.45] text-[#62656a]">{s.reason}</p>
            {/* 사용자가 명시적으로 선택했을 때만 이동 */}
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 flex h-[52px] items-center justify-center rounded-full bg-[#101112] px-5 text-[17px] font-semibold text-white transition active:scale-[0.98]"
            >
              {s.domain}로 이동
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
