// 차단 결과 화면의 신고 안내 (MVP 에는 신고 API 가 없어 외부 신고처만 안내한다)
const CHANNELS = [
  { name: '경찰청 사이버범죄 신고시스템', contact: 'ecrm.police.go.kr' },
  { name: '한국인터넷진흥원 상담센터', contact: '국번 없이 118' },
  { name: '금융 피해가 생겼다면 금융감독원', contact: '국번 없이 1332' },
]

export function ReportGuide() {
  return (
    <div className="flex flex-col gap-4 rounded-[36px] bg-white p-6">
      <p className="text-2xl font-semibold tracking-[-1px] text-[#101112]">이렇게 신고할 수 있어요</p>
      <ul className="flex flex-col gap-3">
        {CHANNELS.map((c) => (
          <li key={c.name} className="flex flex-col gap-1 rounded-[22px] bg-[#f4f4f4] p-4">
            <p className="text-[17px] font-medium text-[#101112]">{c.name}</p>
            <p className="text-[15px] text-[#62656a] select-all">{c.contact}</p>
          </li>
        ))}
      </ul>
      <p className="text-[14px] leading-[1.45] text-[#62656a]">신고할 때는 QR이 붙어 있던 장소와 사진을 함께 남겨 주세요.</p>
    </div>
  )
}
