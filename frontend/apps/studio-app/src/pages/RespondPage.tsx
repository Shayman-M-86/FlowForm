import { useCallback, useEffect, useRef, useState } from 'react'
import { FormFiller, type FormFillerResult } from '@flowform/builder'
import type { SurveyNode, QuestionNode } from '@flowform/builder'
import { Card, Spinner } from '@flowform/ui'
import { respondentClient } from '@/api/respondentClient'
import type { components } from '@/api/generated/schema'

type ResolveResponse = components['schemas']['ResolveSurveyAccessLinkResponse']
type SaveAnswerRequest = components['schemas']['SaveSubmissionSessionAnswerRequest']

type PageState =
  | { phase: 'loading' }
  | { phase: 'error'; message: string }
  | { phase: 'filling'; survey: SurveyNode[]; title: string; nodes: QuestionNode[] }
  | { phase: 'submitting' }
  | { phase: 'complete' }

interface RespondPageProps {
  token: string
}

export function RespondPage({ token }: RespondPageProps) {
  const [state, setState] = useState<PageState>({ phase: 'loading' })
  const resolveData = useRef<ResolveResponse | null>(null)
  const questionNodesRef = useRef<QuestionNode[]>([])

  useEffect(() => {
    let cancelled = false

    async function resolve() {
      const { data, error } = await respondentClient.POST('/api/v1/respondent/links/resolve', {
        body: { token },
      })

      if (cancelled) return

      if (error || !data) {
        setState({ phase: 'error', message: 'This link is invalid or has expired.' })
        return
      }

      resolveData.current = data

      const schema = data.published_version?.compiled_schema as { nodes?: unknown[] } | null
      const rawNodes = schema?.nodes
      if (!rawNodes || !Array.isArray(rawNodes) || rawNodes.length === 0) {
        setState({ phase: 'error', message: 'This survey has not been published yet.' })
        return
      }

      const surveyNodes = rawNodes.map(normalizeNode) as SurveyNode[]
      const questionNodes = surveyNodes.filter(
        (n): n is QuestionNode => n.node_type === 'question',
      )
      const title = data.survey?.title ?? 'Survey'

      questionNodesRef.current = questionNodes
      setState({ phase: 'filling', survey: surveyNodes, title, nodes: questionNodes })
    }

    void resolve()
    return () => { cancelled = true }
  }, [token])

  const handleComplete = useCallback(async (result: FormFillerResult) => {
    if (result.status === 'discarded') {
      setState({ phase: 'error', message: 'This survey has been closed.' })
      return
    }

    setState({ phase: 'submitting' })

    try {
      const { error: startError } = await respondentClient.POST(
        '/api/v1/respondent/submission-sessions',
        { body: { access: { type: 'link_token' as const, token } } },
      )
      if (startError) throw new Error('Failed to start submission session.')

      const questionNodes = questionNodesRef.current
      if (questionNodes.length === 0) throw new Error('Missing survey data.')

      const nodeById = new Map<string, QuestionNode>()
      for (const node of questionNodes) {
        nodeById.set(node.node_key, node)
      }

      for (const answer of result.answers) {
        if (answer.answer == null) continue

        const node = nodeById.get(answer.question_key)
        if (!node) continue

        const payload = mapAnswerToPayload(node, answer.answer)
        if (!payload) continue

        const { error: saveError } = await respondentClient.PUT(
          '/api/v1/respondent/submission-sessions/current/answers/{question_node_id}',
          {
            params: { path: { question_node_id: node.id } },
            body: payload,
          },
        )
        if (saveError) throw new Error(`Failed to save answer for ${answer.question_key}.`)
      }

      const { error: completeError } = await respondentClient.POST(
        '/api/v1/respondent/submission-sessions/current/complete',
      )
      if (completeError) throw new Error('Failed to complete submission.')

      setState({ phase: 'complete' })
    } catch (err) {
      setState({
        phase: 'error',
        message: err instanceof Error ? err.message : 'Something went wrong submitting your answers.',
      })
    }
  }, [token])

  switch (state.phase) {
    case 'loading':
      return (
        <CenteredCard>
          <div className="flex items-center gap-3 text-muted-foreground">
            <Spinner size={18} />
            <span className="text-sm">Loading survey…</span>
          </div>
        </CenteredCard>
      )

    case 'error':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Unable to load survey</h1>
          <p className="text-muted-foreground text-sm">{state.message}</p>
        </CenteredCard>
      )

    case 'filling':
      return (
        <FormFiller
          survey={state.survey}
          title={state.title}
          exitLabel="Close"
          showAnswerSummary
          onComplete={handleComplete}
        />
      )

    case 'submitting':
      return (
        <CenteredCard>
          <div className="flex items-center gap-3 text-muted-foreground">
            <Spinner size={18} />
            <span className="text-sm">Submitting your answers…</span>
          </div>
        </CenteredCard>
      )

    case 'complete':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Thank you!</h1>
          <p className="text-muted-foreground text-sm">Your response has been recorded.</p>
        </CenteredCard>
      )
  }
}

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center p-6 bg-background">
      <Card size="xl" className="w-full max-w-lg">
        {children}
      </Card>
    </div>
  )
}

function normalizeNode(raw: Record<string, unknown>): Record<string, unknown> {
  return {
    ...raw,
    id: raw.node_id ?? raw.id,
    node_key: (raw.node_id as string) ?? raw.node_key,
    node_type: raw.type ?? raw.node_type,
  }
}

function mapAnswerToPayload(
  node: QuestionNode,
  answer: NonNullable<FormFillerResult['answers'][number]['answer']>,
): SaveAnswerRequest | null {
  const base = {
    client_mutation_id: crypto.randomUUID(),
    state: 'answered' as const,
  }

  const family = node.content.family

  switch (family) {
    case 'choice': {
      if (!Array.isArray(answer)) return null
      return {
        ...base,
        answer_family: 'choice',
        answer_value: { selected: answer as string[] },
      }
    }

    case 'matching': {
      if (typeof answer !== 'object' || Array.isArray(answer)) return null
      const pairs = Object.entries(answer as Record<string, string>).map(
        ([left_key, right_key]) => ({ left_key, right_key }),
      )
      if (pairs.length === 0) return null
      return {
        ...base,
        answer_family: 'matching',
        answer_value: { pairs },
      }
    }

    case 'rating': {
      if (typeof answer !== 'number') return null
      const variant = node.content.definition.variant
      return {
        ...base,
        answer_family: 'rating',
        answer_value: { variant, number: answer },
      }
    }

    case 'field': {
      const fieldType = node.content.definition.field_type
      if (fieldType === 'number') {
        const num = Number(answer)
        if (Number.isNaN(num)) return null
        return {
          ...base,
          answer_family: 'field',
          answer_value: { field_type: 'number', number: num },
        }
      }

      const textValue = String(answer)
      if (!textValue) return null

      switch (fieldType) {
        case 'short_text':
          return { ...base, answer_family: 'field', answer_value: { field_type: 'short_text', text: textValue } }
        case 'long_text':
          return { ...base, answer_family: 'field', answer_value: { field_type: 'long_text', text: textValue } }
        case 'email':
          return { ...base, answer_family: 'field', answer_value: { field_type: 'email', email: textValue } }
        case 'date':
          return { ...base, answer_family: 'field', answer_value: { field_type: 'date', date: textValue } }
        case 'phone':
          return { ...base, answer_family: 'field', answer_value: { field_type: 'phone', phone: textValue } }
        default:
          return null
      }
    }

    default:
      return null
  }
}
