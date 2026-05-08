export const PERMISSION_TOOLTIP = {
  'project:edit':
    'Allows changes to project-level details such as the project name, slug, and general configuration.',
  'project:delete':
    'Allows permanent removal of the project and its related workspace data. Reserve this for trusted administrators.',
  'project:manage_members':
    'Allows inviting, removing, and changing project members, including assigning roles to other people.',
  'project:manage_roles':
    'Allows creating and editing roles, including changing which permissions each role grants.',
  'survey:view':
    'Allows viewing surveys in the project, including draft and published survey structure.',
  'survey:create':
    'Allows creating new surveys and starting new survey drafts within this project.',
  'survey:edit':
    'Allows editing survey content, question order, branching logic, and survey settings.',
  'survey:delete':
    'Allows deleting surveys from the project. Use carefully when surveys may contain live work.',
  'survey:publish':
    'Allows publishing surveys, pausing live surveys, and changing whether respondents can access them.',
  'survey:archive':
    'Allows archiving surveys that should no longer appear in active project workflows.',
  'submission:view':
    'Allows viewing collected responses, submission summaries, and respondent data available to the project.',
} as const
