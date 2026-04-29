import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@flowform/ui';
import { FormFillerPage, NodePage } from '@flowform/builder';

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
            <Route path="/node/preview" element={<FormFillerPage />} />
          </Routes>
        </MemoryRouter>
      </div>
    </ThemeProvider>
  );
}
