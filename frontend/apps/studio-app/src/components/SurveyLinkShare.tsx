import { useRef, useState } from 'react'
import { Check, Copy, Download } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '@flowform/ui'

type SurveyLinkShareProps = {
  url: string
  label: string
}

/** QR code, the link itself, and copy / download actions for a survey link. */
export function SurveyLinkShare({ url, label }: SurveyLinkShareProps) {
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const qrRef = useRef<SVGSVGElement>(null)

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url)
      setError(null)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy the link. You can select it above instead.')
    }
  }

  function downloadQr() {
    if (!qrRef.current) return
    const svg = new XMLSerializer().serializeToString(qrRef.current)
    const objectUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = 'flowform-survey-qr.svg'
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
  }

  return (
    <div className="grid w-full justify-items-center gap-4 rounded-lg border border-border bg-muted/20 p-4">
      <div className="rounded-lg border border-border bg-card p-3" role="img" aria-label="QR code for the survey link">
        <QRCodeSVG ref={qrRef} value={url} size={190} level="M" marginSize={2} />
      </div>
      <div className="min-w-0 w-full">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
        <a className="block break-all text-sm text-primary underline" href={url} target="_blank" rel="noopener noreferrer">
          {url}
        </a>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={() => void copyLink()}>
          {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
          {copied ? 'Copied' : 'Copy link'}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={downloadQr}>
          <Download size={14} aria-hidden="true" />
          Download QR
        </Button>
      </div>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
