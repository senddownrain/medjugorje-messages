import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';

// Use /medjugorje-messages/ when hosted as a GitHub Pages project site.
// SITE_BASE can override this for another deployment path.
const base = process.env.SITE_BASE || '/medjugorje-messages/';

export default defineConfig({
  base,
  plugins: [
    vue(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src', filename: 'sw.js',
      registerType: 'prompt',
      injectManifest: { globPatterns: ['index.html', 'assets/index-*.js', 'assets/index-*.css', '**/*.{svg,png,ico,webp}'] },
      includeAssets: ['favicon*.ico', 'favicon*.png', 'apple-touch-icon.png', 'logo-*.webp'],
      manifest: {
        name: 'Послания Царицы Мира',
        short_name: 'Меджугорье',
        description: 'Послания из Меджугорья: RU, BE, UK, HR, EN, SK, LV',
        lang: 'ru',
        start_url: base,
        scope: base,
        display: 'standalone',
        theme_color: '#f7f5f0',
        background_color: '#f7f5f0',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: 'icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
        ]
      },
      devOptions: { enabled: false }
    })
  ]
});
