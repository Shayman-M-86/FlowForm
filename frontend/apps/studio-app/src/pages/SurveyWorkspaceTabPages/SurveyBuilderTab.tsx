import { useState } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { useNavigate, useParams } from '@tanstack/react-router'
import { NodePage, type SurveyNode } from '@flowform/builder'
import { Button, Modal, Spinner, Toast } from '@flowform/ui'
import { useGenerateAiImport } from '@/api/hooks/nodes'
import { useCreatePublicLink, usePublicLinks } from '@/api/hooks/links'
import { useUpdateSurvey } from '@/api/hooks/surveys'
import { PublishSuccessModal } from '@/components/PublishSuccessModal'
import { StudioAiImportModal } from '@/components/StudioAiImportModal'
import {
  SurveyBuilderArchivedPanel,
  SurveyBuilderNoVersionsPanel,
  SurveyBuilderPublishedNoDraftPanel,
  SurveyBuilderVersionToolbar,
} from '@/components/SurveyBuilderTabChrome'
import { defaultLinkName } from '@/lib/surveyNames'
import { useSurveyBuilderController } from './useSurveyBuilderController'

export function SurveyBuilderTab() {
  const builder = useSurveyBuilderController()
  const navigate = useNavigate()
  const { slug, surveySlug } = useParams({ from: '/_studio/projects/$slug/surveys/$surveySlug/builder' })
  const generateAiImport = useGenerateAiImport(
    builder.projectId,
    builder.surveyId > 0 ? builder.surveyId : null,
    builder.selectedVersion?.status === 'draft' ? builder.selectedVersion.version_number : null,
  )
  const createLink = useCreatePublicLink(builder.projectId, builder.surveyId > 0 ? builder.surveyId : null)
  const updateSurvey = useUpdateSurvey(builder.projectId, builder.surveyId > 0 ? String(builder.surveyId) : null)
  const [debugOpen, setDebugOpen] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [publishOpen, setPublishOpen] = useState(false)
  // Existing links are only needed to number the general link's default name.
  const { data: existingLinks = [] } = usePublicLinks(
    publishOpen ? builder.projectId : null,
    builder.surveyId > 0 ? builder.surveyId : null,
  )

  function handleAiImport(imported: SurveyNode[]) {
    builder.setNodes(imported)
    setAiOpen(false)
  }

  async function handlePublish() {
    if (await builder.publishDraft()) setPublishOpen(true)
  }

  async function createGeneralLink(): Promise<string> {
    if (builder.surveyVisibility === 'private') {
      await updateSurvey.mutateAsync({ title: null, visibility: 'link_only', public_slug: null })
    }
    const result = await createLink.mutateAsync({
      name: defaultLinkName('general_link', existingLinks),
      link_type: 'general',
      assignment_source: 'manual',
      assigned_participant_id: null,
      expires_at: null,
    })
    return result.url
  }

  function viewLiveResponses() {
    setPublishOpen(false)
    void navigate({
      to: '/projects/$slug/surveys/$surveySlug/responses',
      params: { slug, surveySlug },
      search: { status: 'in_progress' },
    })
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
        onPublish={() => void handlePublish()}
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
        <>
          <SurveyBuilderPublishedNoDraftPanel
            publishedVersion={builder.selectedVersion}
            canEdit={builder.canEdit}
            isCopying={builder.isCopying}
            onCopyToDraft={() => void builder.copyToDraft()}
          />
          <MemoryRouter>
            <NodePage
              nodes={builder.nodes}
              disabled
              readOnly
              onNodesChange={() => undefined}
            />
          </MemoryRouter>
        </>
      ) : (
        <SurveyBuilderArchivedPanel version={builder.selectedVersion} />
      )}

      {aiOpen && (
        <StudioAiImportModal
          open={aiOpen}
          hasExistingNodes={builder.nodes.length > 0}
          onClose={() => setAiOpen(false)}
          onGenerate={(prompt) => generateAiImport.mutateAsync(prompt)}
          onImport={handleAiImport}
        />
      )}

      {publishOpen && (
        <PublishSuccessModal
          open={publishOpen}
          canCreateLink={builder.canEdit}
          requiresLinkOnly={builder.surveyVisibility === 'private'}
          onClose={() => setPublishOpen(false)}
          onCreateLink={createGeneralLink}
          onViewResponses={viewLiveResponses}
        />
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
