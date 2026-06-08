import { lazy, Suspense, useState } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { NodePage, type SurveyNode } from '@flowform/builder'
import { Button, Modal, Spinner, Toast } from '@flowform/ui'
import {
  SurveyBuilderArchivedPanel,
  SurveyBuilderNoVersionsPanel,
  SurveyBuilderPublishedNoDraftPanel,
  SurveyBuilderVersionToolbar,
} from '@/components/SurveyBuilderTabChrome'
import { useSurveyBuilderController } from './useSurveyBuilderController'

// The AI-import feature drags in the Zod validator, so it stays behind a lazy
// boundary and only loads when the user opens it from the toolbar menu.
const AiImportModal = lazy(() => import('@flowform/builder/ai-import'))

export function SurveyBuilderTab() {
  const builder = useSurveyBuilderController()
  const [debugOpen, setDebugOpen] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)

  function handleAiImport(imported: SurveyNode[]) {
    builder.setNodes(imported)
    setAiOpen(false)
  }

  if (builder.isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={20} />
      </div>
    )
  }

  return (
    <section className="grid gap-0">
      {builder.toast && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm">
          <Toast variant={builder.toast.variant} onClose={builder.dismissToast}>
            {builder.toast.message}
          </Toast>
        </div>
      )}

      <Modal
        open={builder.pendingSwitch != null}
        onClose={builder.cancelSwitch}
        title="Unsaved changes"
        width={420}
        footer={(
          <div className="flex w-full items-center justify-between gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={builder.cancelSwitch}>
              Keep editing
            </Button>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={builder.confirmSwitch}>
                Discard changes
              </Button>
              <Button type="button" variant="primary" size="sm" disabled={builder.isSaving} onClick={() => void builder.saveAndSwitch()}>
                {builder.isSaving ? 'Saving...' : 'Save and switch'}
              </Button>
            </div>
          </div>
        )}
      >
        <p className="text-sm text-muted-foreground">
          You have unsaved changes to this draft. What would you like to do before switching versions?
        </p>
      </Modal>

      <SurveyBuilderVersionToolbar
        versions={builder.versions}
        selectedVersion={builder.selectedVersion}
        canEdit={builder.canEdit}
        canPublish={builder.canPublish}
        canArchive={builder.canArchive}
        isDirty={builder.isDirty}
        isCreating={builder.isCreating}
        isCopying={builder.isCopying}
        isSaving={builder.isSaving}
        isPublishing={builder.isPublishing}
        isArchiving={builder.isArchiving}
        onSelectVersion={builder.selectVersion}
        onCreateDraft={() => void builder.createDraft()}
        onCopyToDraft={() => void builder.copyToDraft()}
        onAiImport={() => setAiOpen(true)}
        onSave={() => void builder.saveDraft()}
        onPublish={() => void builder.publishDraft()}
        onArchive={() => void builder.archiveVersion()}
      />

      {builder.isError ? (
        <div className="px-6 py-8 md:px-16">
          <p className="text-sm text-destructive">Failed to load the survey builder.</p>
        </div>
      ) : !builder.selectedVersion ? (
        <SurveyBuilderNoVersionsPanel
          canEdit={builder.canEdit}
          isCreating={builder.isCreating}
          onCreateDraft={() => void builder.createDraft()}
        />
      ) : builder.selectedVersion.status === 'draft' ? (
        <MemoryRouter>
          <NodePage
            nodes={builder.nodes}
            disabled={!builder.canEdit || builder.isSaving}
            onNodesChange={builder.setNodes}
            invalidNodeIds={builder.invalidNodeIds}
          />
        </MemoryRouter>
      ) : builder.selectedVersion.status === 'published' ? (
        <SurveyBuilderPublishedNoDraftPanel
          publishedVersion={builder.selectedVersion}
          canEdit={builder.canEdit}
          isCopying={builder.isCopying}
          onCopyToDraft={() => void builder.copyToDraft()}
        />
      ) : (
        <SurveyBuilderArchivedPanel version={builder.selectedVersion} />
      )}

      {aiOpen && (
        <Suspense fallback={null}>
          <AiImportModal
            open={aiOpen}
            hasExistingQuestions={builder.nodes.length > 0}
            onClose={() => setAiOpen(false)}
            onImport={handleAiImport}
          />
        </Suspense>
      )}

      {import.meta.env.DEV && (
        <div className="fixed bottom-6 left-6 z-50 max-w-sm font-mono text-xs">
          <button
            type="button"
            onClick={() => setDebugOpen((o) => !o)}
            className="rounded bg-black/70 px-2 py-1 text-white backdrop-blur"
          >
            {debugOpen ? '▼ nodes' : '▶ nodes'} ({builder.nodes.length})
          </button>
          {debugOpen && (
            <pre className="mt-1 max-h-96 overflow-auto rounded bg-black/80 p-3 text-green-400 backdrop-blur">
              {JSON.stringify(builder.nodes, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
