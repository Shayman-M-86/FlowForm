import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import PinyAstro from '@pinegrow/piny-astro';
import path from 'path';
import { fileURLToPath } from 'url';
import sitemap from '@astrojs/sitemap';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const stylesSrc = path.resolve(__dirname, '../../packages/styles/src');
const uiSrc = path.resolve(__dirname, '../../packages/ui/src');
const builderSrc = path.resolve(__dirname, '../../packages/builder/src');
const siteShellSrc = path.resolve(__dirname, '../../packages/site-shell/src');

export default defineConfig({
  site: 'https://flow-form.com.au',
  build: {
    inlineStylesheets: 'never',
  },
  integrations: [
    react(),
    PinyAstro(),
    sitemap(),
  ],
  vite: {
    plugins: [tailwindcss()],
    ssr: {
      noExternal: ['@flowform/ui', '@flowform/builder', '@flowform/site-shell', '@flowform/styles'],
    },
    resolve: {
      tsconfigPaths: false,
      extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
      alias: [
        { find: '@flowform/site-shell/header.css', replacement: path.resolve(siteShellSrc, 'SiteHeader.css') },
        { find: '@flowform/site-shell', replacement: path.resolve(siteShellSrc, 'index.ts') },
        { find: '@flowform/builder/node-page.css', replacement: path.resolve(builderSrc, 'pages/NodePage.css') },
        { find: '@flowform/builder', replacement: path.resolve(builderSrc, 'index.ts') },
        { find: '@flowform/ui', replacement: path.resolve(uiSrc, 'index.tsx') },
        { find: '@flowform/styles/tokens.css', replacement: path.resolve(stylesSrc, 'tokens.css') },
        { find: '@flowform/styles/components.css', replacement: path.resolve(stylesSrc, 'components.css') },
        { find: '@flowform/styles', replacement: path.resolve(stylesSrc, 'index.css') },
      ],
    },
  },
});
