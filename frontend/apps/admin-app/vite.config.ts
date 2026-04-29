import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import { resolve } from 'path'

const stylesSrc = resolve(__dirname, '../../packages/styles/src')
const uiSrc = resolve(__dirname, '../../packages/ui/src')

export default defineConfig({
  server: {
    host: true,
    port: 5174,
  },
  plugins: [
    tanstackRouter({ routesDirectory: './src/routes', generatedRouteTree: './src/routeTree.gen.ts' }),
    tailwindcss(),
    react(),
  ],
  resolve: {
    alias: [
      { find: '@flowform/ui', replacement: resolve(uiSrc, 'index.tsx') },
      { find: '@flowform/styles/tokens.css', replacement: resolve(stylesSrc, 'tokens.css') },
      { find: '@flowform/styles/components.css', replacement: resolve(stylesSrc, 'components.css') },
      { find: '@flowform/styles', replacement: resolve(stylesSrc, 'index.css') },
      { find: '@', replacement: resolve(__dirname, './src') },
    ],
  },
  optimizeDeps: {
    exclude: ['@flowform/ui'],
  },
})
