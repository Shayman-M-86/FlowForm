import { useQuery } from '@tanstack/react-query'
import { isDesignPreviewMode } from './designPreview'
import { getMockSurvey } from './mockData'
import { useApi } from './useApi'
import type { SurveyOut } from './types'
import type { ApiExecutor } from './types'

// ── Query key factory ─────────────────────────────────────────────────────────

export const surveyKeys = {
  all: () => ['surveys'] as const,
  detail: (projectRef: string | number | null, surveyRef: string | number | null) =>
    [...surveyKeys.all(), 'detail', projectRef, surveyRef] as const,
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

function fetchSurvey(
  executor: ApiExecutor,
  projectRef: string | number,
  surveyRef: string | number,
): Promise<SurveyOut> {
  return executor.get(`/api/v1/projects/${projectRef}/surveys/${surveyRef}`)
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSurvey(projectRef: string | null, surveyRef: string | null) {
  const { executor } = useApi()
  return useQuery({
    queryKey: surveyKeys.detail(projectRef, surveyRef),
    queryFn: () => {
      if (projectRef === null || surveyRef === null) throw new Error('refs are required')
      if (isDesignPreviewMode) {
        const mock = getMockSurvey(projectRef, surveyRef)
        return Promise.resolve(mock ? ({ title: mock.title } as SurveyOut) : null)
      }
      return fetchSurvey(executor, projectRef, surveyRef)
    },
    enabled: projectRef !== null && surveyRef !== null,
  })
}
