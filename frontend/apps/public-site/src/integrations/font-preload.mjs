import { readdir } from 'fs/promises';
import { resolve } from 'path';

/**
 * Astro integration that injects a <link rel="preload"> for the latin Geist
 * woff2 after build. The file is content-hashed by Vite so we scan _astro/
 * to find the current name rather than hardcoding the hash.
 *
 * The latin subset (gyByhwUxId8gMEwcGFU) covers U+0000-00FF and is the one
 * that renders for English text — the only subset worth preloading.
 */
export default function fontPreload() {
  return {
    name: 'font-preload',
    hooks: {
      'astro:build:done': async ({ dir, pages, logger }) => {
        const astroDir = resolve(dir.pathname, '_astro');
        let files;
        try {
          files = await readdir(astroDir);
        } catch {
          logger.warn('font-preload: could not read _astro/ directory');
          return;
        }

        const latinGeist = files.find(
          f => f.startsWith('gyByhwUxId8gMEwcGFU') && f.endsWith('.woff2')
        );
        if (!latinGeist) {
          logger.warn('font-preload: latin Geist woff2 not found in _astro/');
          return;
        }

        const preloadTag = `<link rel="preload" href="/_astro/${latinGeist}" as="font" type="font/woff2" crossorigin>`;

        const { readFile, writeFile } = await import('fs/promises');
        const { glob } = await import('fs/promises');

        // Inject into every HTML file in the dist
        const htmlFiles = [];
        async function walk(dir) {
          const entries = await readdir(dir, { withFileTypes: true });
          for (const entry of entries) {
            const full = resolve(dir, entry.name);
            if (entry.isDirectory()) await walk(full);
            else if (entry.name.endsWith('.html')) htmlFiles.push(full);
          }
        }
        await walk(dir.pathname);

        await Promise.all(
          htmlFiles.map(async (file) => {
            const html = await readFile(file, 'utf-8');
            if (html.includes(preloadTag)) return;
            const updated = html.replace('</head>', `${preloadTag}</head>`);
            await writeFile(file, updated, 'utf-8');
          })
        );

        logger.info(`font-preload: injected preload for /_astro/${latinGeist} into ${htmlFiles.length} page(s)`);
      },
    },
  };
}
