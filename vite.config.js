import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';

// Use /medjugorje-messages/ when hosted as a GitHub Pages project site.
// For local development Vite uses / by default.
const base = process.env.SITE_BASE || '/medjugorje-messages/';

export default defineConfig({
  base,
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Послания Царицы Мира',
        short_name: 'Меджугорье',
        description: 'Послания из Меджугорья на русском, беларускай і українській',
        lang: 'ru',
        start_url: base,
        scope: base,
        display: 'standalone',
        theme_color: '#f7f5f0',
        background_color: '#f7f5f0',
        icons: [
          { src: 'icon-192.svg', sizes: '192x192', type: 'image/svg+xml', purpose: 'any' },
          { src: 'icon-512.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,json}'],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        cleanupOutdatedCaches: true,
        navigateFallback: 'index.html'
      },
      devOptions: { enabled: false }
    })
  ]
});
