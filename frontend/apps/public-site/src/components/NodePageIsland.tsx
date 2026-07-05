import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { ThemeProvider, Spinner, Button } from '@flowform/ui';
import {
  NodePage,
  BuilderToolbar,
  draftStorage,
  savePreviewSurvey,
  type SurveyNode,
} from '@flowform/builder';

// Lazy boundaries: the form filler and the AI-import feature (which drags in
// the Zod validator) only load on demand, keeping the initial builder chunk small.
const FormFillerPage = lazy(() =>
  import('@flowform/builder').then((m) => ({ default: m.FormFillerPage }))
);
const AiImportModal = lazy(() => import('@flowform/builder/ai-import'));

// Standalone demo builder: no backend. The draft lives in local state and is
// persisted to localStorage so it survives reloads. Preview hands the current
// nodes to the form filler via sessionStorage + route navigation.
const DRAFT_STORAGE_KEY = 'flowform.public-site.builder-draft';

function BuilderRoute() {
  const navigate = useNavigate();
  const draft = useMemo(() => draftStorage(DRAFT_STORAGE_KEY), []);
  const [nodes, setNodes] = useState<SurveyNode[]>(() => draft.load() ?? []);
  const [aiOpen, setAiOpen] = useState(false);

  // Persist the draft on every change so it survives a full page reload.
  useEffect(() => {
    draft.save(nodes);
  }, [draft, nodes]);

  function handlePreview() {
    if (nodes.length === 0) return;
    savePreviewSurvey(nodes);
    navigate('/node/preview', { state: { survey: nodes } });
  }

  function handleAiImport(imported: SurveyNode[]) {
    setNodes(imported);
    setAiOpen(false);
  }

  return (
    <>
      <BuilderToolbar
        sticky={false}
        start={
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setAiOpen(true)}
          >
            <Sparkles size={14} aria-hidden="true" />
            AI import
          </Button>
        }
        end={
          <>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={nodes.length === 0}
              onClick={() => {
                draft.clear();
                setNodes([]);
              }}
            >
              Clear
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={nodes.length === 0}
              onClick={handlePreview}
            >
              Preview form
            </Button>
          </>
        }
      />
      <NodePage nodes={nodes} onNodesChange={setNodes} />

      {aiOpen && (
        <Suspense fallback={null}>
          <AiImportModal
            open={aiOpen}
            hasExistingQuestions={nodes.length > 0}
            onClose={() => setAiOpen(false)}
            onImport={handleAiImport}
          />
        </Suspense>
      )}
    </>
  );
}

export function NodePageIsland() {
  return (
    <ThemeProvider>
      <div className="builder-shell">
        <MemoryRouter initialEntries={['/node']}>
          <Routes>
            <Route path="/node" element={<BuilderRoute />} />
            <Route
              path="/node/preview"
              element={
                <Suspense fallback={<div className="flex justify-center py-16"><Spinner size={20} /></div>}>
                  <FormFillerPage />
                </Suspense>
              }
            />
          </Routes>
        </MemoryRouter>
      </div>
    </ThemeProvider>
  );
}
