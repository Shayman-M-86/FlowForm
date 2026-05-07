import { useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { useProject } from '@/api/projects'
import { Spinner, Card, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { SurveysTab } from './ProjectDashboardTabPages/SurveysTab'
import { MembersTab } from './ProjectDashboardTabPages/MembersTab'
import { RolesTab } from './ProjectDashboardTabPages/RolesTab'
import { ManagementTab } from './ProjectDashboardTabPages/ManagementTab'

type DashboardTab = 'surveys' | 'members' | 'roles' | 'management'

const TABS = [
  { id: 'surveys', label: 'Surveys' },
  { id: 'members',   label: 'Members' },
  { id: 'roles',     label: 'Roles' },
  { id: 'management', label: 'Management' },
]

export function ProjectDashboardPage() {
  const { slug } = useParams({ from: '/projects/$slug/' })
  const { data: project, isPending, isError, error } = useProject(slug)
  const [activeTab, setActiveTab] = useState<DashboardTab>('surveys')

  if (isPending) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
        <Spinner size={28} />
      </div>
    )
  }

  if (isError) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <Card tone="muted">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: project.name, current: true },
      ]} />
      <div className="mt-3 flex items-center justify-between gap-4">
        <h1>{project.name}</h1>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{project.slug}</p>

      <TabSelector
        className="my-5"
        items={TABS}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id as DashboardTab)}
      />

      <div className="gap-3 p-3">
        {activeTab === 'surveys'  && <SurveysTab projectSlug={slug} />}
        {activeTab === 'members'    && <MembersTab />}
        {activeTab === 'roles'      && <RolesTab />}
        {activeTab === 'management' && <ManagementTab customRoles={[]} onAddRole={() => setActiveTab('roles')} />}
      </div>
    </main>
  )
}
