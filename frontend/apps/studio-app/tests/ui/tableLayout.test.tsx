import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import {
  Table,
  resolveTableLayout,
  type TableColumn,
} from '@flowform/ui'

type Row = { id: number; name: string }

function column(
  key: string,
  policy: Partial<TableColumn<Row>> = {},
): TableColumn<Row> {
  return {
    key,
    header: key,
    minWidth: 100,
    cell: (row) => row.name,
    ...policy,
  }
}

describe('resolveTableLayout', () => {
  it('grows columns by weight and stops at maximum widths', () => {
    const layout = resolveTableLayout([
      column('primary', {
        idealWidth: 200,
        maxWidth: 300,
        growWeight: 3,
      }),
      column('secondary', {
        idealWidth: 200,
        maxWidth: 220,
        growWeight: 1,
      }),
    ], 500)

    expect(layout.columns.map(({ width }) => width)).toEqual([280, 220])
    expect(layout.totalWidth).toBe(500)
  })

  it('shrinks lower-priority columns first and resolves compact modes', () => {
    const layout = resolveTableLayout([
      column('primary', {
        minWidth: 100,
        idealWidth: 220,
        shrinkPriority: 2,
        compactBelow: 180,
      }),
      column('secondary', {
        minWidth: 80,
        idealWidth: 180,
        shrinkPriority: 0,
        compactBelow: 120,
      }),
    ], 300)

    expect(layout.columns.map(({ width, mode }) => ({ width, mode }))).toEqual([
      { width: 220, mode: 'full' },
      { width: 80, mode: 'compact' },
    ])
  })

  it('hides optional columns by visibility priority before scrolling', () => {
    const layout = resolveTableLayout([
      column('required', { minWidth: 180, idealWidth: 180 }),
      column('later', {
        minWidth: 100,
        idealWidth: 100,
        hideable: true,
        visibilityPriority: 20,
      }),
      column('first', {
        minWidth: 80,
        idealWidth: 80,
        hideable: true,
        visibilityPriority: 10,
      }),
    ], 230)

    expect(layout.columns.map(({ definition }) => definition.key)).toEqual([
      'required',
    ])
    expect(layout.hiddenColumns.map(({ key }) => key)).toEqual([
      'first',
      'later',
    ])
    expect(layout.totalWidth).toBe(230)
  })

  it('keeps required columns and overflows as the final fallback', () => {
    const layout = resolveTableLayout([
      column('name', { minWidth: 200 }),
      column('actions', { minWidth: 150 }),
    ], 300)

    expect(layout.columns).toHaveLength(2)
    expect(layout.hiddenColumns).toHaveLength(0)
    expect(layout.totalWidth).toBe(350)
  })
})

describe('Table', () => {
  it('renders semantic table markup with a colgroup', () => {
    const markup = renderToStaticMarkup(
      <Table
        columns={[column('name', { idealWidth: 180 })]}
        rows={[{ id: 1, name: 'Example' }]}
        getRowKey={(row) => row.id}
      />,
    )

    expect(markup).toContain('<table')
    expect(markup).toContain('<colgroup>')
    expect(markup).toContain('<th')
    expect(markup).toContain('<td')
    expect(markup).not.toContain('role="table"')
  })
})
