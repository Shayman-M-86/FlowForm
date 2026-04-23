// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import starlight from '@astrojs/starlight';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const reactSrc = path.resolve(__dirname, '../../my-react-app/src');

export default defineConfig({
  build: {
    inlineStylesheets: 'always',
  },
  integrations: [
    starlight({
      title: 'FlowForm Docs',
      logo: {
        src: './public/favicon.svg',
      },
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/Shayman-M-86/FlowForm' },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', slug: 'docs/introduction' },
            { label: 'Building Your First Form', slug: 'docs/building-your-first-form' },
          ],
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
      },
      customCss: ['./src/styles/starlight-overrides.css'],
    }),
    react(),
  ],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        '@react-app': reactSrc,
      },
    },
  },
});