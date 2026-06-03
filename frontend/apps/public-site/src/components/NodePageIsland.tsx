import { lazy, Suspense } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider, Spinner } from '@flowform/ui';
import { NodePage } from '@flowform/builder';

const FormFillerPage = lazy(() =>
  import('@flowform/builder').then((m) => ({ default: m.FormFillerPage }))
);

const builderOverrideCSS = `
  .builder-shell .node-page__toolbar {
    position: relative !important;
    top: auto !important;
    left: auto !important;
    right: auto !important;
  }
  .builder-shell .node-page__content {
    padding-top: 24px !important;
  }
`;

export function NodePageIsland() {
  return (
    <ThemeProvider>
      <style dangerouslySetInnerHTML={{ __html: builderOverrideCSS }} />
      <div className="builder-shell">
        <MemoryRouter initialEntries={['/node']}>
          <Routes>
            <Route path="/node" element={<NodePage />} />
            <Route path="/node/preview" element={<Suspense fallback={<div className="flex justify-center py-16"><Spinner size={20} /></div>}><FormFillerPage /></Suspense>} />
          </Routes>
        </MemoryRouter>
      </div>
    </ThemeProvider>
  );
}
