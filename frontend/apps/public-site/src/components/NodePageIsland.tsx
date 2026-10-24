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

// Start a first visit with a small, editable example. Saved drafts (including an
// intentionally cleared draft) take priority over this browser-local starter.
const STARTER_NODES: SurveyNode[] = [
  {
    id: '94b79cd1-a585-435d-9f29-0b8359ba3501',
    node_key: 'current_role', node_type: 'question', sort_key: 100000,
    content: {
      family: 'choice', title: 'A survey that follows your answer', label: 'What is your current role?',
      definition: { min: 1, max: 1, options: [
        { id: 'student', label: 'Student' },
        { id: 'professional', label: 'Working professional' },
        { id: 'freelancer', label: 'Freelancer' },
      ] },
    },
  },
  {
    id: '94b79cd1-a585-435d-9f29-0b8359ba3502',
    node_key: 'relevant_followup', node_type: 'rule', sort_key: 200000,
    content: {
      if: { match: 'ALL', conditions: [
        { target_id: 'current_role', family: 'choice', requirements: { required: ['professional'] } },
      ] },
      then: { set: [{ target_id: 'experience', visible: true, required: true }] },
      else: { set: [{ target_id: 'experience', visible: false, required: false }] },
    },
  },
  {
    id: '94b79cd1-a585-435d-9f29-0b8359ba3503',
    node_key: 'experience', node_type: 'question', sort_key: 300000,
    content: {
      family: 'field', title: 'A question that fits', label: 'How many years of professional experience do you have?',
      definition: { field_type: 'number', ui: { placeholder: 'e.g. 5' } },
    },
  },
];

function BuilderRoute() {
  const navigate = useNavigate();
  const draft = useMemo(() => draftStorage(DRAFT_STORAGE_KEY), []);
  const [nodes, setNodes] = useState<SurveyNode[]>(() => draft.load() ?? STARTER_NODES);
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
