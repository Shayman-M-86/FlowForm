import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import starlight from '@astrojs/starlight';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const stylesSrc = path.resolve(__dirname, '../../packages/styles/src');
const uiSrc = path.resolve(__dirname, '../../packages/ui/src');
const builderSrc = path.resolve(__dirname, '../../packages/builder/src');
const siteShellSrc = path.resolve(__dirname, '../../packages/site-shell/src');

export default defineConfig({
  site: 'https://flow-form.com.au',
  build: {
    inlineStylesheets: 'always',
  },
  integrations: [
    starlight({
      title: 'FlowForm Docs',
      logo: {
        src: './src/assets/FlowForm_logo.png',
      },
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/Shayman-M-86/FlowForm' },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', slug: 'docs/introduction' },
            { label: 'Building Your First Form', slug: 'docs/building-your-first-form' },],
        },
        {
          label: 'Question Types',
          autogenerate: { directory: 'docs/question-types' },
        },
      ],
      components: {
        Head: './src/components/starlight/Head.astro',
        Header: './src/components/starlight/Header.astro',
        ThemeProvider: './src/components/starlight/ThemeProvider.astro',
        ThemeSelect: './src/components/starlight/ThemeSelect.astro',
        PageFrame: './src/components/starlight/PageFrame.astro',
        MobileMenuToggle: './src/components/MobileMenuToggle.astro',
      },
      customCss: ['./src/styles/starlight-overrides.css'],
    }),
    react(),
  ],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
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
