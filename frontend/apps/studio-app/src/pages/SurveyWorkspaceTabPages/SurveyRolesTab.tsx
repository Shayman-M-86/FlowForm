import { RolesWorkspace } from '../ProjectDashboardTabPages/RolesWorkspace'
import {
  SURVEY_PERMISSION_GROUPS,
  SURVEY_PRESET_ROLES,
} from '../ProjectDashboardTabPages/roleDefinitions'
import { useRenderDebug } from '@/debug/useRenderDebug'

export function SurveyRolesTab() {
  useRenderDebug('SurveyRolesTab')
  return (
    <RolesWorkspace
      presets={SURVEY_PRESET_ROLES}
      permissionGroups={SURVEY_PERMISSION_GROUPS}
      defaultRoleDescription="Custom survey role."
    />
  )
}
