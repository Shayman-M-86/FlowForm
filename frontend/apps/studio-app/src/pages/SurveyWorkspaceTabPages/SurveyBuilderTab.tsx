import { MemoryRouter } from 'react-router-dom'
import { NodePage } from '@flowform/builder'
import { Button, Modal, Spinner, Toast } from '@flowform/ui'
import {
  SurveyBuilderArchivedPanel,
  SurveyBuilderNoVersionsPanel,
  SurveyBuilderPublishedNoDraftPanel,
  SurveyBuilderVersionToolbar,
} from '@/components/SurveyBuilderTabChrome'
import { useSurveyBuilderController } from './useSurveyBuilderController'

export function SurveyBuilderTab() {
  const builder = useSurveyBuilderController()

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
          <NodePage nodes={builder.nodes} disabled={!builder.canEdit || builder.isSaving} onNodesChange={builder.setNodes} />
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
    </section>
  )
}
