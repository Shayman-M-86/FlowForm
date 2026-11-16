import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PublishSuccessModal } from '@/components/PublishSuccessModal'

const surveyUrl = 'http://localhost:5174/respond/example-token'
const mounted: Array<() => void> = []

afterEach(() => {
  while (mounted.length) mounted.pop()?.()
})

describe('publish success modal', () => {
  it('creates the link only when asked and displays its URL and QR code', async () => {
    const host = document.createElement('div')
    document.body.append(host)
    const root = createRoot(host)
    mounted.push(() => {
      act(() => root.unmount())
      host.remove()
    })
    const onCreateLink = vi.fn(async () => surveyUrl)

    await act(async () => {
      root.render(
        <PublishSuccessModal
          open
          canCreateLink
          requiresLinkOnly
          onClose={() => undefined}
          onCreateLink={onCreateLink}
          onViewResponses={() => undefined}
        />,
      )
    })

    expect(document.body.textContent).toContain('Congratulations! Your survey is live.')
    expect(document.body.textContent).toContain('switch this survey to Link only access')
    expect(onCreateLink).not.toHaveBeenCalled()

    const createButton = [...document.querySelectorAll('button')].find((button) => button.textContent?.includes('Create a general link'))
    expect(createButton).toBeTruthy()
    await act(async () => createButton?.click())

    expect(onCreateLink).toHaveBeenCalledOnce()
    expect(document.body.textContent).toContain(surveyUrl)
    expect(document.querySelector('[aria-label="QR code for the survey link"] svg')).not.toBeNull()
  })

  it('offers a primary action that opens live responses', async () => {
    const host = document.createElement('div')
    document.body.append(host)
    const root = createRoot(host)
    mounted.push(() => {
      act(() => root.unmount())
      host.remove()
    })
    const onViewResponses = vi.fn()

    await act(async () => {
      root.render(
        <PublishSuccessModal
          open
          canCreateLink
          requiresLinkOnly={false}
          onClose={() => undefined}
          onCreateLink={async () => surveyUrl}
          onViewResponses={onViewResponses}
        />,
      )
    })

    const viewButton = [...document.querySelectorAll('button')].find((button) => button.textContent === 'View Live Responses')
    expect(viewButton).toBeTruthy()
    await act(async () => viewButton?.click())

    expect(onViewResponses).toHaveBeenCalledOnce()
  })
})
