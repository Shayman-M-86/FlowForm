import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type SubjectTree = components['schemas']['SurveySubjectTreeResponses']
export type SessionTree = components['schemas']['SurveySessionTreeResponses']
export type SurveySession = components['schemas']['SurveySessionResponses']
export type AnswerSlot = components['schemas']['SurveyAnswerSlotResponses']
export type SessionEvent = components['schemas']['SurveySessionEventResponses']
export type SubjectSummary = components['schemas']['SurveySubjectResponses']
export type ResponseStatus = SurveySession['status']

const resultKeys = {
  subjects: (projectId: number, surveyId: number) =>
    ['results', 'project', projectId, 'survey', surveyId, 'subjects'] as const,
  subject: (projectId: number, surveyId: number, subjectId: string) =>
    ['results', 'project', projectId, 'survey', surveyId, 'subject', subjectId] as const,
}

type SubjectsOpts = {
  page?: number
  pageSize?: number
  includeDecryptedAnswerValues?: boolean
  includeEvents?: boolean
}

export function useSurveyResultSubjects(
  projectId: number,
  surveyId: number,
  opts: SubjectsOpts = {},
) {
  const {
    page = 1,
    pageSize = 25,
    includeDecryptedAnswerValues = false,
    includeEvents = false,
  } = opts
  return usePolicyQuery({
    queryKey: [
      ...resultKeys.subjects(projectId, surveyId),
      { page, pageSize, includeDecryptedAnswerValues, includeEvents },
    ] as const,
    enabled: projectId > 0 && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/results/subjects',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId },
            query: {
              page,
              page_size: pageSize,
              include_decrypted_answer_values: includeDecryptedAnswerValues,
              include_events: includeEvents,
            },
          },
        },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.results,
  })
}

export function useSubjectTree(
  projectId: number,
  surveyId: number,
  subjectId: string | null,
  opts: { includeDecryptedAnswerValues?: boolean; includeEvents?: boolean } = {},
) {
  const { includeDecryptedAnswerValues = false, includeEvents = false } = opts
  return usePolicyQuery({
    queryKey: subjectId
      ? ([
          ...resultKeys.subject(projectId, surveyId, subjectId),
          { includeDecryptedAnswerValues, includeEvents },
        ] as const)
      : (['results', 'disabled'] as const),
    enabled: projectId > 0 && surveyId > 0 && subjectId != null,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/results/subjects/{subject_id}',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId, subject_id: subjectId! },
            query: {
              include_decrypted_answer_values: includeDecryptedAnswerValues,
              include_events: includeEvents,
            },
          },
        },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.resultDetail,
  })
}

export function useDeleteSession(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { error } = await apiClient.DELETE(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/results/sessions/{session_id}',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId, session_id: sessionId },
          },
        },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: resultKeys.subjects(projectId, surveyId) })
    },
  })
}

type ExportParams = {
  body: components['schemas']['ExportSurveyResultsRequest']
  filename: string
}

export function useExportResults(projectId: number, surveyId: number) {
  return useMutation({
    mutationFn: async ({ body, filename }: ExportParams) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/results/export',
        {
          params: { path: { project_id: projectId, survey_id: surveyId } },
          body,
          parseAs: 'blob',
        },
      )
      if (error) throw error

      const url = URL.createObjectURL(data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)

      return { format: body.format }
    },
  })
}
