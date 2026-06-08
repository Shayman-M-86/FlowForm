import { MemoryRouter } from 'react-router-dom'
import { NodePage, type SurveyNode } from '@flowform/builder'
import {
  SurveyBuilderArchivedPanel,
  SurveyBuilderNoVersionsPanel,
  SurveyBuilderPublishedNoDraftPanel,
  SurveyBuilderVersionToolbar,
  type SurveyVersionView,
} from '@/components/SurveyBuilderTabChrome'

const PRESENTATION_VERSIONS: SurveyVersionView[] = [
  {
    id: 1,
    version_number: 3,
    status: 'draft',
    created_at: '2026-06-08T00:00:00.000Z',
  },
  {
    id: 2,
    version_number: 2,
    status: 'published',
    created_at: '2026-06-06T00:00:00.000Z',
  },
  {
    id: 3,
    version_number: 1,
    status: 'archived',
    created_at: '2026-06-01T00:00:00.000Z',
  },
]

const PRESENTATION_NODES: SurveyNode[] = []

function noop() {}

export function SurveyBuilderTab() {
  const selectedVersion = PRESENTATION_VERSIONS[0]

  return (
    <section className="grid gap-0">
      <SurveyBuilderVersionToolbar versions={PRESENTATION_VERSIONS} selectedVersion={selectedVersion} />

      {selectedVersion.status === 'draft' ? (
        <MemoryRouter>
          <NodePage nodes={PRESENTATION_NODES} onNodesChange={noop} />
        </MemoryRouter>
      ) : selectedVersion.status === 'published' ? (
        <SurveyBuilderPublishedNoDraftPanel publishedVersion={selectedVersion} />
      ) : selectedVersion.status === 'archived' ? (
        <SurveyBuilderArchivedPanel version={selectedVersion} />
      ) : (
        <SurveyBuilderNoVersionsPanel />
      )}
    </section>
  )
}
