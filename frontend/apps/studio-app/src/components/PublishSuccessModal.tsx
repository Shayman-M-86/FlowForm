import { useRef, useState } from 'react'
import { PartyPopper } from 'lucide-react'
import { Button, Modal } from '@flowform/ui'
import { SurveyLinkShare } from './SurveyLinkShare'
import './PublishSuccessModal.css'

type PublishSuccessModalProps = {
  open: boolean
  canCreateLink: boolean
  requiresLinkOnly: boolean
  onClose: () => void
  onCreateLink: () => Promise<string>
  onViewResponses: () => void
}

export function PublishSuccessModal({
  open,
  canCreateLink,
  requiresLinkOnly,
  onClose,
  onCreateLink,
  onViewResponses,
}: PublishSuccessModalProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const creatingRef = useRef(false)

  async function createLink() {
    if (creatingRef.current || url) return
    creatingRef.current = true
    setIsCreating(true)
    setError(null)
    try {
      setUrl(await onCreateLink())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create the general link. Please try again.')
    } finally {
      creatingRef.current = false
      setIsCreating(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      required={isCreating}
      title="Survey published"
      width={520}
      footer={(
        <div className="flex w-full items-center justify-between gap-2">
          <Button type="button" variant="secondary" size="sm" disabled={isCreating} onClick={onClose}>
            Done
          </Button>
          <Button type="button" variant="primary" size="sm" disabled={isCreating} onClick={onViewResponses}>
            View Live Responses
          </Button>
        </div>
      )}
    >
      <div className="grid justify-items-center gap-5 py-2 text-center">
        <div className="publish-success__celebration relative grid size-20 place-items-center rounded-full bg-success/10 text-success">
          <span className="publish-success__spark" aria-hidden="true" />
          <span className="publish-success__spark" aria-hidden="true" />
          <span className="publish-success__spark" aria-hidden="true" />
          <span className="publish-success__spark" aria-hidden="true" />
          <span className="publish-success__spark" aria-hidden="true" />
          <span className="publish-success__spark" aria-hidden="true" />
          <PartyPopper size={35} strokeWidth={1.8} aria-hidden="true" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-foreground">Congratulations! Your survey is live.</h3>
          <p className="mt-1 text-sm text-muted-foreground">Your published version is ready to share.</p>
        </div>

        {!url && (
          <div className="grid justify-items-center gap-2">
            <Button type="button" variant="primary" disabled={!canCreateLink || isCreating} onClick={() => void createLink()}>
              {isCreating ? 'Creating link…' : 'Create a general link'}
            </Button>
            <p className="max-w-sm text-xs text-muted-foreground">
              Anyone with a general link can open the survey.
              {requiresLinkOnly && ' Creating one will switch this survey to Link only access.'}
              {!canCreateLink && ' Survey edit permission is required to create a link.'}
            </p>
          </div>
        )}

        {url && <SurveyLinkShare url={url} label="General link" />}

        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      </div>
    </Modal>
  )
}
