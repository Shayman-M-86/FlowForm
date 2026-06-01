import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import PinyVite from '@pinegrow/piny-vite'
import { resolve } from 'path'

const stylesSrc = resolve(__dirname, '../../packages/styles/src')
const uiSrc = resolve(__dirname, '../../packages/ui/src')
const builderSrc = resolve(__dirname, '../../packages/builder/src')
const siteShellSrc = resolve(__dirname, '../../packages/site-shell/src')
const schemaSrc = resolve(__dirname, '../../packages/schema/src')

export default defineConfig({
  server: {
    host: true,
    port: 5175,
  },
  appType: 'spa',
  build: {
    rollupOptions: {
      input: resolve(__dirname, 'index-bootstrap-test.html'),
    },
  },
  plugins: [
    tailwindcss(),
    react(),
    PinyVite(),
  ],
  resolve: {
    alias: [
      { find: '@flowform/schema', replacement: resolve(schemaSrc, 'index.ts') },
      { find: '@flowform/site-shell/header.css', replacement: resolve(siteShellSrc, 'SiteHeader.css') },
      { find: '@flowform/site-shell', replacement: resolve(siteShellSrc, 'index.ts') },
      { find: '@flowform/builder', replacement: resolve(builderSrc, 'index.ts') },
      { find: '@flowform/ui', replacement: resolve(uiSrc, 'index.tsx') },
      { find: '@flowform/styles/fonts.css', replacement: resolve(stylesSrc, 'fonts.css') },
      { find: '@flowform/styles/tokens.css', replacement: resolve(stylesSrc, 'tokens.css') },
      { find: '@flowform/styles/components.css', replacement: resolve(stylesSrc, 'components.css') },
      { find: '@flowform/styles', replacement: resolve(stylesSrc, 'index.css') },
      { find: '@', replacement: resolve(__dirname, './src') },
    ],
  },
  optimizeDeps: {
    exclude: ['@flowform/ui', '@flowform/builder', '@flowform/schema'],
  },
})
