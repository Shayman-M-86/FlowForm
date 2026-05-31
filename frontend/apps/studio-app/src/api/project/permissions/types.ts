import type { FlowFormPermission } from '../../generated/rbac.gen'

export type { FlowFormPermission }

export type ProjectPermission = FlowFormPermission
export type SurveyPermission = Extract<
  FlowFormPermission,
  | 'survey:view'
  | 'survey:create'
  | 'survey:edit'
  | 'survey:delete'
  | 'survey:publish'
  | 'survey:archive'
  | 'submission:view'
>
