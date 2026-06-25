import { Badge, Card, Modal, Spinner } from '@flowform/ui'
import { useResponseDetail, type ResponseAnswer } from '@/api/hooks/responses'

type Props = {
  projectId: number
  surveyId: number
  sessionId: string | null
  onClose: () => void
}

const STATUS_BADGE_VARIANT = {
  completed: 'success',
  in_progress: 'warning',
  abandoned: 'muted',
} as const

const STATUS_LABEL = {
  completed: 'Completed',
  in_progress: 'In Progress',
  abandoned: 'Abandoned',
} as const

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function AnswerCard({ answer }: { answer: ResponseAnswer }) {
  return (
    <Card size="sm" tone="muted">
      <div className="flex items-start justify-between gap-2">
        <p className="font-mono text-xs text-muted-foreground">{answer.question_node_id.slice(0, 8)}</p>
        <div className="flex items-center gap-1.5">
          {answer.answer_family && (
            <Badge variant="muted" size="xs">{answer.answer_family}</Badge>
          )}
          <Badge variant={answer.state === 'answered' ? 'success' : 'warning'} size="xs">
            {answer.state}
          </Badge>
        </div>
      </div>
      {answer.state === 'answered' && answer.answer_value != null && (
        <pre className="mt-2 overflow-x-auto rounded bg-background p-2 text-xs text-foreground">
          {JSON.stringify(answer.answer_value, null, 2)}
        </pre>
      )}
    </Card>
  )
}

export function ResponseDetailModal({ projectId, surveyId, sessionId, onClose }: Props) {
  const { data, isLoading } = useResponseDetail(projectId, surveyId, sessionId)
  const session = data?.session
  const answers = data?.answers ?? []

  return (
    <Modal
      open={sessionId != null}
      onClose={onClose}
      title="Response detail"
      width={640}
    >
      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner size={24} /></div>
      ) : session ? (
        <div className="grid gap-4">
          {/* ── Session metadata ────────────────────────────────────────── */}
          <div className="grid gap-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge variant={STATUS_BADGE_VARIANT[session.status]} size="xs">
                {STATUS_LABEL[session.status]}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Session</span>
              <span className="font-mono text-xs text-foreground">{session.session_id.slice(0, 8)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Started</span>
              <span className="text-foreground">{formatTimestamp(session.started_at)}</span>
            </div>
            {session.completed_at && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Completed</span>
                <span className="text-foreground">{formatTimestamp(session.completed_at)}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Last activity</span>
              <span className="text-foreground">{formatTimestamp(session.last_activity_at)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Version</span>
              <span className="text-foreground">v{session.survey_version_id}</span>
            </div>
          </div>

          {/* ── Answers ─────────────────────────────────────────────────── */}
          <div>
            <h3 className="mb-2 text-sm font-semibold">
              Answers ({answers.length})
            </h3>
            {answers.length === 0 ? (
              <p className="text-xs text-muted-foreground">No answers recorded for this session.</p>
            ) : (
              <div className="grid gap-2">
                {answers.map((answer) => (
                  <AnswerCard key={`${answer.question_node_id}-${answer.revision_number}`} answer={answer} />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
