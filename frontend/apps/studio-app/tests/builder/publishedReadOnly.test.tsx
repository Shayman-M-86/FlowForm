import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { NodePage, type SurveyNode } from '@flowform/builder'

const publishedNodes: SurveyNode[] = [{
  id: '11111111-1111-4111-8111-111111111111',
  node_key: 'sleep_duration',
  node_type: 'question',
  sort_key: 100000,
  content: {
    family: 'field',
    label: 'How long do you sleep?',
    definition: { field_type: 'long_text' },
  },
}]

describe('published builder view', () => {
  it('shows the saved question without editing or add controls', () => {
    const container = document.createElement('div')
    container.innerHTML = renderToStaticMarkup(
      <MemoryRouter>
        <NodePage nodes={publishedNodes} disabled readOnly onNodesChange={() => undefined} />
      </MemoryRouter>,
    )

    expect(container.textContent).toContain('How long do you sleep?')
    const editButtons = [...container.querySelectorAll('button')].filter((button) => button.textContent?.trim() === 'Edit')
    expect(editButtons).toHaveLength(1)
    expect(editButtons[0]?.disabled).toBe(true)
    expect(container.textContent).not.toContain('Add another question')
  })
})
