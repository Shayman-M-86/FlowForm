import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type ResponseSummary = components['schemas']['SurveyResponseSummaryResponses']
export type ResponseDetail = components['schemas']['SurveyResponseDetailResponses']
export type ResponseAnswer = components['schemas']['SurveyResponseAnswerResponses']
export type ResponseStatus = ResponseSummary['status']

const responseKeys = {
  list: (projectId: number, surveyId: number) =>
    ['responses', 'project', projectId, 'survey', surveyId] as const,
  detail: (projectId: number, surveyId: number, sessionId: string) =>
    ['responses', 'project', projectId, 'survey', surveyId, 'session', sessionId] as const,
}

export function useResponses(
  projectId: number,
  surveyId: number,
  opts: { status?: ResponseStatus; page?: number; pageSize?: number } = {},
) {
  const { status, page = 1, pageSize = 25 } = opts
  return usePolicyQuery({
    queryKey: [...responseKeys.list(projectId, surveyId), { status, page, pageSize }] as const,
    enabled: projectId > 0 && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/responses',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId },
            query: { status: status ?? undefined, page, page_size: pageSize },
          },
        },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.responses,
  })
}

export function useResponseDetail(
  projectId: number,
  surveyId: number,
  sessionId: string | null,
) {
  return usePolicyQuery({
    queryKey: sessionId
      ? responseKeys.detail(projectId, surveyId, sessionId)
      : (['responses', 'disabled'] as const),
    enabled: projectId > 0 && surveyId > 0 && sessionId != null,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/responses/{session_id}',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId, session_id: sessionId! },
          },
        },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.responseDetail,
  })
}

export function useDeleteResponse(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { error } = await apiClient.DELETE(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/responses/{session_id}',
        {
          params: {
            path: { project_id: projectId, survey_id: surveyId, session_id: sessionId },
          },
        },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: responseKeys.list(projectId, surveyId) })
    },
  })
}

type ExportParams = {
  body: components['schemas']['ExportSurveyResponsesRequest']
  filename: string
}

export function useExportResponses(projectId: number, surveyId: number) {
  return useMutation({
    mutationFn: async ({ body, filename }: ExportParams) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/responses/export',
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
