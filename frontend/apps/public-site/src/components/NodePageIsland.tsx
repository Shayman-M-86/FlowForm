import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '@react-app/index.optimized';
import { NodePage } from '@react-app/pages/NodePage';
import { FormFillerPage } from '@react-app/pages/FormFillerPage';
import '@react-app/pages/NodePage.css';

const builderOverrideCSS = `
  .builder-shell .node-page__toolbar {
    position: sticky !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
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
