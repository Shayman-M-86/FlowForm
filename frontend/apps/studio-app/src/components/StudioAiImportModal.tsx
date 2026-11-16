import { useState } from 'react'
import type { SurveyNode } from '@flowform/builder'
import { Button, LargeInput, Modal } from '@flowform/ui'
import { Sparkles } from 'lucide-react'
import type { AiImportPreview } from '@/api/hooks/nodes'

type StudioAiImportModalProps = {
  open: boolean
  hasExistingNodes: boolean
  onClose: () => void
  onGenerate: (prompt: string) => Promise<AiImportPreview>
  onImport: (nodes: SurveyNode[]) => void
}

export function StudioAiImportModal({
  open,
  hasExistingNodes,
  onClose,
  onGenerate,
  onImport,
}: StudioAiImportModalProps) {
  const [prompt, setPrompt] = useState('')
  const [preview, setPreview] = useState<AiImportPreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [confirmReplace, setConfirmReplace] = useState(false)

  async function generate() {
    setError(null)
    setPreview(null)
    setConfirmReplace(false)
    setIsGenerating(true)
    try {
      setPreview(await onGenerate(prompt.trim()))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not generate a survey draft.')
    } finally {
      setIsGenerating(false)
    }
  }

  function importPreview() {
    if (!preview) return
    if (hasExistingNodes && !confirmReplace) {
      setConfirmReplace(true)
      return
    }
    onImport(preview.nodes as SurveyNode[])
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Generate survey questions"
      width={600}
      required={isGenerating}
      footer={(
        <div className="flex w-full justify-end gap-2">
          <Button type="button" variant="ghost" size="sm" disabled={isGenerating} onClick={onClose}>
            Cancel
          </Button>
          {preview ? (
            <Button type="button" variant={confirmReplace ? 'destructive' : 'primary'} size="sm" onClick={importPreview}>
              {confirmReplace ? 'Confirm replace' : hasExistingNodes ? 'Replace draft questions' : 'Add to draft'}
            </Button>
          ) : (
            <Button type="button" variant="primary" size="sm" disabled={!prompt.trim() || isGenerating} onClick={() => void generate()}>
              {isGenerating ? 'Generating…' : 'Generate preview'}
            </Button>
          )}
        </div>
      )}
    >
      <div className="grid gap-4">
        <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
          <p>Describe the questions you need. Review the result before adding it to this draft.</p>
        </div>
        <LargeInput
          label="Survey request"
          rows={5}
          maxText={4000}
          showCount
          value={prompt}
          onChange={(event) => {
            setPrompt(event.target.value)
            setPreview(null)
            setConfirmReplace(false)
            setError(null)
          }}
          placeholder="Create a short survey about students' sleep habits, including sleep duration, caffeine, and sleep quality."
          disabled={isGenerating}
        />
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {preview && (
          <div className="grid gap-3 rounded-lg border border-border bg-card p-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Suggested title</p>
              <p className="font-semibold text-foreground">{preview.title}</p>
              {preview.description && <p className="mt-1 text-sm text-muted-foreground">{preview.description}</p>}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {preview.nodes.length} question{preview.nodes.length === 1 ? '' : 's'}
              </p>
              <ol className="mt-2 max-h-56 list-decimal space-y-2 overflow-y-auto pl-5 text-sm text-foreground">
                {preview.nodes.map((node) => <li key={node.id}>{node.content.label}</li>)}
              </ol>
            </div>
            <p className="text-xs text-muted-foreground">Only the questions will be added to this draft. Use Save to store them.</p>
            {confirmReplace && (
              <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                This will replace the questions and rules currently in the draft. Confirm to continue.
              </p>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}
