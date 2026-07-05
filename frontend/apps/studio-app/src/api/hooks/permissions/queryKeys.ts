export const permissionKeys = {
  project: (projectId: number) => ['permissions', 'project', projectId] as const,
  survey: (projectId: number, surveyId: number) =>
    ['permissions', 'project', projectId, 'survey', surveyId] as const,
}
