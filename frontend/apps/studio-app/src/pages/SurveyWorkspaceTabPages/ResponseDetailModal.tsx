import { useEffect, useRef } from 'react'
import { Badge, Card, Modal } from '@flowform/ui'
import type { AnswerSlot, SessionTree } from '@/api/hooks/results'
import { orderAnswers, presentAnswer } from '@/lib/responsePresentation'

type Props = {
  sessionTree: SessionTree | null
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

/** Manual scrolling within this window suppresses the auto-scroll to a new answer. */
const USER_SCROLL_GRACE_MS = 1_000
const BOTTOM_PADDING_PX = 24
const SCROLL_KEYS = new Set(['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '])

/** An answer slot that holds a recorded response (not just a placeholder). */
function isRecorded(answer: AnswerSlot): boolean {
  return answer.has_encrypted_answer || answer.state != null
}

function scrolledRecently(lastUserScrollAt: number): boolean {
  return performance.now() - lastUserScrollAt < USER_SCROLL_GRACE_MS
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function AnswerCard({ answer, index }: { answer: AnswerSlot; index: number }) {
  const presented = presentAnswer(answer)
  return (
    <Card size="sm" tone="muted">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Question {index + 1}</p>
        <div className="flex items-center gap-1.5">
          {presented.family && (
            <Badge variant="muted" size="xs">{presented.family}</Badge>
          )}
          {answer.state ? (
            <Badge variant={answer.state === 'answered' ? 'success' : 'warning'} size="xs">
              {answer.state}
            </Badge>
          ) : (
            <Badge variant="muted" size="xs">
              {answer.has_encrypted_answer ? 'encrypted' : 'no answer'}
            </Badge>
          )}
        </div>
      </div>
      {presented.section && <p className="mt-2 text-xs text-muted-foreground">{presented.section}</p>}
      <p className="mt-2 text-sm font-semibold leading-6 text-foreground">{presented.question}</p>
      <div className="mt-3 rounded-md border border-border bg-background p-3">
        <p className="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">Answer</p>
        {presented.lines.length === 1 ? (
          <p className="whitespace-pre-wrap break-words text-sm text-foreground">{presented.lines[0]}</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
            {presented.lines.map((line, lineIndex) => <li key={`${lineIndex}-${line}`}>{line}</li>)}
          </ul>
        )}
        {presented.hint && <p className="mt-2 text-xs text-muted-foreground">{presented.hint}</p>}
      </div>
    </Card>
  )
}

export function ResponseDetailModal({ sessionTree, onClose }: Props) {
  const session = sessionTree?.session
  const answers = orderAnswers(sessionTree?.answers ?? [])
  const open = sessionTree != null
  const sessionId = session?.session_id ?? null
  const answeredKey = answers.filter(isRecorded).map((answer) => answer.question_node_id).join('|')

  const bodyRef = useRef<HTMLDivElement>(null)
  const lastUserScrollAt = useRef(Number.NEGATIVE_INFINITY)
  const seenAnswers = useRef<{ sessionId: string | null; ids: Set<string> }>({ sessionId: null, ids: new Set() })

  // Remember when the viewer last scrolled by hand, so live updates don't
  // yank the view away from something they are reading.
  useEffect(() => {
    const body = bodyRef.current
    if (!open || !body) return
    const listeners = new AbortController()
    const options = { passive: true, signal: listeners.signal }
    let pointerDown = false // dragging the scrollbar
    const markUserScroll = () => { lastUserScrollAt.current = performance.now() }
    body.addEventListener('wheel', markUserScroll, options)
    body.addEventListener('touchmove', markUserScroll, options)
    body.addEventListener('keydown', (event) => { if (SCROLL_KEYS.has(event.key)) markUserScroll() }, options)
    body.addEventListener('pointerdown', () => { pointerDown = true }, options)
    body.addEventListener('scroll', () => { if (pointerDown) markUserScroll() }, options)
    window.addEventListener('pointerup', () => { pointerDown = false }, options)
    return () => listeners.abort()
  }, [open])

  // When a new answer arrives for the open session, bring it into view.
  useEffect(() => {
    const ids = new Set(answeredKey ? answeredKey.split('|') : [])
    const previous = seenAnswers.current
    seenAnswers.current = { sessionId, ids }
    if (sessionId == null || previous.sessionId !== sessionId) return

    const newIds = [...ids].filter((id) => !previous.ids.has(id))
    if (newIds.length === 0) return
    if (scrolledRecently(lastUserScrollAt.current)) return

    const body = bodyRef.current
    const target = body?.querySelector<HTMLElement>(`[data-answer-id="${CSS.escape(newIds[newIds.length - 1])}"]`)
    if (!body || !target) return
    const behavior: ScrollBehavior = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    const overshoot = target.getBoundingClientRect().bottom - body.getBoundingClientRect().bottom
    body.scrollTo({ top: body.scrollTop + overshoot + BOTTOM_PADDING_PX, behavior })
  }, [sessionId, answeredKey])

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Response detail"
      width={1100}
      className="max-h-[calc(100dvh-3rem)]"
      bodyRef={bodyRef}
    >
      {session ? (
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
              <span className="text-muted-foreground">Version record</span>
              <span className="text-foreground">#{session.survey_version_id}</span>
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
                {answers.map((answer, index) => (
                  <div key={answer.question_node_id} data-answer-id={answer.question_node_id}>
                    <AnswerCard answer={answer} index={index} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
