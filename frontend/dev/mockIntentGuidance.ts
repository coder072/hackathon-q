import type { IncomingMessage, ServerResponse } from 'node:http'
import type { Plugin } from 'vite'

// 개발 서버 전용 POST /api/v1/intent-guidance 목업.
// 백엔드 구현(#19)이 머지되면 vite.config.ts 에서 이 플러그인을 빼고 실제 API 로 프록시한다.
// 분석 세션 검사는 실제 백엔드의 GET /analyses/{id} 로 하고, 의도 분류만 키워드로 흉내 낸다.

interface Site {
  name: string
  url: string
  domain: string
}

interface Service {
  serviceKey: string
  serviceName: string
  aliases: string[]
  sites: Partial<Record<IntentCode, Site>> & { GENERAL_VISIT: Site }
}

type IntentCode = 'SERVICE_LOGIN' | 'DELIVERY_TRACKING' | 'PAYMENT' | 'GENERAL_VISIT'

const SERVICES: Service[] = [
  {
    serviceKey: 'naver',
    serviceName: '네이버',
    aliases: ['네이버', 'naver'],
    sites: {
      SERVICE_LOGIN: { name: '네이버 로그인', url: 'https://nid.naver.com/nidlogin.login', domain: 'nid.naver.com' },
      PAYMENT: { name: '네이버페이', url: 'https://pay.naver.com', domain: 'pay.naver.com' },
      GENERAL_VISIT: { name: '네이버', url: 'https://www.naver.com', domain: 'www.naver.com' },
    },
  },
  {
    serviceKey: 'kakao',
    serviceName: '카카오',
    aliases: ['카카오', 'kakao', '카톡'],
    sites: {
      SERVICE_LOGIN: { name: '카카오계정', url: 'https://accounts.kakao.com', domain: 'accounts.kakao.com' },
      GENERAL_VISIT: { name: '카카오', url: 'https://www.kakao.com', domain: 'www.kakao.com' },
    },
  },
  {
    serviceKey: 'coupang',
    serviceName: '쿠팡',
    aliases: ['쿠팡', 'coupang'],
    sites: { GENERAL_VISIT: { name: '쿠팡', url: 'https://www.coupang.com', domain: 'www.coupang.com' } },
  },
  {
    serviceKey: 'toss',
    serviceName: '토스',
    aliases: ['토스', 'toss'],
    sites: { GENERAL_VISIT: { name: '토스', url: 'https://toss.im', domain: 'toss.im' } },
  },
  {
    serviceKey: 'epost',
    serviceName: '우체국',
    aliases: ['우체국', 'epost'],
    sites: {
      DELIVERY_TRACKING: {
        name: '우체국 택배 조회',
        url: 'https://service.epost.go.kr/iservice/usr/trace/usrtrc001k01.jsp',
        domain: 'service.epost.go.kr',
      },
      GENERAL_VISIT: { name: '인터넷우체국', url: 'https://www.epost.go.kr', domain: 'www.epost.go.kr' },
    },
  },
  {
    serviceKey: 'cj_logistics',
    serviceName: 'CJ대한통운',
    aliases: ['cj', '대한통운'],
    sites: {
      DELIVERY_TRACKING: {
        name: 'CJ대한통운 배송 조회',
        url: 'https://www.cjlogistics.com/ko/tool/parcel/tracking',
        domain: 'www.cjlogistics.com',
      },
      GENERAL_VISIT: { name: 'CJ대한통운', url: 'https://www.cjlogistics.com', domain: 'www.cjlogistics.com' },
    },
  },
]

const INTENT_KEYWORDS: [IntentCode, RegExp][] = [
  ['SERVICE_LOGIN', /로그인|계정|login/i],
  ['DELIVERY_TRACKING', /택배|배송|운송장/],
  ['PAYMENT', /결제|송금|이체|카드|pay/i],
]

const FOLLOW_UP: Partial<Record<IntentCode, string>> = {
  SERVICE_LOGIN: '어떤 서비스에 로그인하려고 하셨나요?',
  DELIVERY_TRACKING: '어느 택배사(우체국, CJ대한통운 등)의 배송을 조회하려고 하셨나요?',
  PAYMENT: '어떤 서비스에서 결제하려고 하셨나요?',
}

const SENSITIVE_PATTERNS = [
  /(비밀번호|비번|password|pw|인증번호|otp)\s*[:은는이가]?\s*\S{4,}/i,
  /\d{6}\s*-?\s*[1-4]\d{6}/, // 주민등록번호
  /\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}/, // 카드번호
  /\d{2,6}-\d{2,6}-\d{2,8}/, // 계좌번호
]

function send(res: ServerResponse, status: number, body: object) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.setHeader('Cache-Control', 'no-store')
  res.setHeader('X-Mock', 'intent-guidance')
  res.end(JSON.stringify({ ...body, requestId: `mock_${Date.now()}` }))
}

function fail(res: ServerResponse, status: number, code: string, message: string) {
  send(res, status, { success: false, error: { code, message, details: [] } })
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = []
  for await (const chunk of req) chunks.push(chunk as Buffer)
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf-8'))
  } catch {
    return {}
  }
}

function classify(message: string) {
  const text = message.toLowerCase()
  const service = SERVICES.find((s) => s.aliases.some((a) => text.includes(a.toLowerCase()))) ?? null
  const intent = INTENT_KEYWORDS.find(([, re]) => re.test(message))?.[0] ?? null
  return { service, intent }
}

export function mockIntentGuidance(backendUrl: string): Plugin {
  return {
    name: 'mock-intent-guidance',
    apply: 'serve',
    configureServer(server) {
      // 내부 미들웨어(프록시)보다 먼저 등록되므로 이 경로만 가로챈다
      server.middlewares.use('/api/v1/intent-guidance', async (req, res, next) => {
        if (req.method !== 'POST') return next()

        const body = await readJson(req)
        const analysisId = typeof body.analysisId === 'string' ? body.analysisId : ''
        const userMessage = typeof body.userMessage === 'string' ? body.userMessage.trim() : ''

        if (!userMessage || userMessage.length > 300) {
          return fail(res, 400, 'INVALID_INTENT_MESSAGE', '접속 목적은 1~300자로 입력해야 합니다.')
        }

        // 실제 백엔드에서 분석 세션을 확인한다
        type Session = { recommendedAction: string; expiresAt: string }
        let analysis: Session | null = null
        try {
          const r = await fetch(`${backendUrl}/api/v1/analyses/${encodeURIComponent(analysisId)}`)
          if (r.ok) analysis = ((await r.json()) as { data: Session }).data
        } catch {
          return fail(res, 503, 'INTENT_SERVICE_UNAVAILABLE', '분석 서버에 연결할 수 없습니다.')
        }
        if (!analysis || new Date(analysis.expiresAt).getTime() < Date.now()) {
          return fail(res, 404, 'ANALYSIS_NOT_FOUND', '분석 세션이 없거나 만료되었습니다.')
        }
        if (analysis.recommendedAction !== 'ASK_INTENT') {
          return fail(res, 409, 'INTENT_GUIDANCE_NOT_ALLOWED', '의도 안내를 사용할 수 없는 분석입니다.')
        }

        if (SENSITIVE_PATTERNS.some((re) => re.test(userMessage))) {
          return fail(res, 422, 'SENSITIVE_DATA_DETECTED', '민감정보가 포함되어 있습니다.')
        }

        // LLM 응답 지연 흉내
        await new Promise((resolve) => setTimeout(resolve, 800))

        const { service, intent } = classify(userMessage)
        const base = { analysisId, followUpQuestion: null, suggestions: [] as object[] }

        if (!service) {
          const followUpQuestion = intent ? FOLLOW_UP[intent] : null
          return send(res, 200, {
            success: true,
            data: {
              ...base,
              guidanceStatus: followUpQuestion ? 'NEEDS_CLARIFICATION' : 'NOT_FOUND',
              intentCode: intent,
              serviceKey: null,
              serviceName: null,
              confidence: followUpQuestion ? 0.4 : 0.1,
              followUpQuestion,
            },
          })
        }

        const intentCode = intent && service.sites[intent] ? intent : 'GENERAL_VISIT'
        const primary = service.sites[intentCode]!
        const sites = [primary, ...(intentCode === 'GENERAL_VISIT' ? [] : [service.sites.GENERAL_VISIT])]
        return send(res, 200, {
          success: true,
          data: {
            ...base,
            guidanceStatus: 'MATCHED',
            intentCode,
            serviceKey: service.serviceKey,
            serviceName: service.serviceName,
            confidence: intent ? 0.92 : 0.7,
            suggestions: sites.map((s, i) => ({
              ...s,
              reason: i === 0 ? `${service.serviceName}의 공식 주소예요.` : `${service.serviceName} 공식 홈페이지예요.`,
              verified: true,
            })),
          },
        })
      })
    },
  }
}
