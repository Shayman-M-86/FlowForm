import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it } from 'vitest'
import type { AiImportPreview } from '@/api/hooks/nodes'
import { StudioAiImportModal } from '@/components/StudioAiImportModal'

const mounted: Array<() => void> = []

afterEach(() => {
  while (mounted.length) mounted.pop()?.()
})

describe('studio AI import modal', () => {
  it('shows the generating animation while waiting for a draft', async () => {
    const host = document.createElement('div')
    document.body.append(host)
    const root = createRoot(host)
    mounted.push(() => {
      act(() => root.unmount())
      host.remove()
    })
    let resolve: (preview: AiImportPreview) => void = () => undefined
    const pending = new Promise<AiImportPreview>((done) => { resolve = done })

    await act(async () => {
      root.render(
        <StudioAiImportModal
          open
          hasExistingNodes={false}
          onClose={() => undefined}
          onGenerate={() => pending}
          onImport={() => undefined}
        />,
      )
    })

    const textarea = document.querySelector('textarea')!
    await act(async () => {
      const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!
      setValue.call(textarea, 'A short sleep survey')
      textarea.dispatchEvent(new Event('input', { bubbles: true }))
    })
    const generate = [...document.querySelectorAll('button')].find((button) => button.textContent === 'Generate preview')
    await act(async () => generate?.click())

    expect(document.body.textContent).toContain('Generating your survey')
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull()
    expect(document.querySelector('.ai-gen-shell')).not.toBeNull()

    await act(async () => resolve({ title: 'Sleep', description: '', nodes: [] } as unknown as AiImportPreview))

    expect(document.body.textContent).not.toContain('Generating your survey')
    expect(document.querySelector('.ai-gen-shell')).toBeNull()
  })
})
