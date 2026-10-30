import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [
      react(),
      tailwindcss(),
      // PWA-001 홈 화면 설치, PWA-002 앱 셸 캐시
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'icon.svg', 'apple-touch-icon-180x180.png'],
        manifest: {
          name: 'QR 안심스캔',
          short_name: '안심스캔',
          description: 'QR 코드 속 링크를 열기 전에 피싱 여부를 확인합니다.',
          lang: 'ko',
          start_url: '/',
          display: 'standalone',
          orientation: 'portrait',
          background_color: '#0f172a',
          theme_color: '#0f172a',
          icons: [
            { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
            { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
            { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
            { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
          navigateFallback: '/index.html',
          // 분석 API 응답은 캐시하지 않는다 (오프라인에서 안전 판정 금지, PWA-004)
          navigateFallbackDenylist: [/^\/api\//],
        },
      }),
    ],
    server: {
      proxy: {
        '/api': {
          target: env.VITE_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
