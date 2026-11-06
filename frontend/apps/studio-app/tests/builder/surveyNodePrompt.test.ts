/// <reference types="node" />
// @vitest-environment node
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { describe, expect, it } from 'vitest'
import { surveyNodeImportJsonSchema } from '@flowform/schema'
import {
  AI_IMPORT_EXAMPLE_NODES,
  buildSurveyNodeFixPrompt,
  buildSurveyNodePrompt,
} from '../../../../packages/builder/src/components/Utils/ai-import/surveyNodePrompt'
import {
  parseSurveyNodeJson,
  SurveyNodeImportError,
  type SurveyNodeImportIssue,
} from '../../../../packages/builder/src/components/Utils/ai-import/surveyNodeImport'

const { load } = createRequire(import.meta.url)('js-yaml') as {
  load(source: string): { components: { schemas: Record<string, unknown> } }
}

function extractSchema(prompt: string): typeof surveyNodeImportJsonSchema {
  return JSON.parse(prompt.split('COMPLETE INPUT JSON SCHEMA\n')[1].split('\n\nVALID EXAMPLE ARRAY')[0])
}

describe('AI import prompt contract', () => {
  it('includes the entire OpenAPI input contract with every reference resolvable', () => {
    const prompt = buildSurveyNodePrompt('All question types, including countries and states')
    const schema = extractSchema(prompt)
    const spec = load(readFileSync(new URL('../../../../../backend/openapi.yaml', import.meta.url), 'utf8'))
    const definitions: Record<string, unknown> = schema.$defs
    const refs = [...JSON.stringify(schema).matchAll(/#\/\$defs\/([A-Za-z0-9_-]+)/g)]
    expect(refs.length).toBeGreaterThan(0)
    for (const [, name] of refs) expect(definitions).toHaveProperty(name)
    // Preserve every constraint and optional/required field, not a handpicked subset.
    for (const [name, definition] of Object.entries(definitions)) {
      expect(definition).toEqual(JSON.parse(
        JSON.stringify(spec.components.schemas[name]).replaceAll('#/components/schemas/', '#/$defs/'),
      ))
    }
    expect(schema.$defs.RatingSliderDefinitionIn.required).toContain('range')
    expect(schema.$defs.RatingRangeIn.required).toEqual(expect.arrayContaining(['min', 'max', 'step']))
    expect(schema.$defs.RatingEmojiDefinitionIn.required).toContain('emoji_list')
    expect(schema.$defs.RatingEmojiDefinitionIn.properties.emoji_list.enum).toEqual([
      'sad_to_happy', 'angry_to_happy', 'disgust_to_happy',
    ])
  })

  it('provides an importable example with all question variants and reference families', () => {
    const prompt = buildSurveyNodePrompt('Show all question types')
    const rawExample = prompt.split('Adapt this example to the user request.')[1]
      .split('\n').slice(1).join('\n').split('\n\nBefore returning')[0]
    expect(parseSurveyNodeJson(rawExample)).toEqual(AI_IMPORT_EXAMPLE_NODES)
    const variants = AI_IMPORT_EXAMPLE_NODES.flatMap((node) => {
      if (node.node_type === 'rule') return []
      const { content } = node
      return [content.family === 'field' ? content.definition.field_type
        : content.family === 'rating' ? content.definition.variant
          : content.family === 'choice' ? (content.definition.max === 1 ? 'single' : 'multi')
            : content.family]
    })
    expect(new Set(variants)).toEqual(new Set([
      'single', 'multi', 'short_text', 'long_text', 'email', 'phone', 'number', 'date',
      'stars', 'slider', 'emoji', 'matching',
    ]))
  })

  it('makes the missing-slider-range and missing-emoji-list repair self-contained', () => {
    const broken = JSON.parse(JSON.stringify(AI_IMPORT_EXAMPLE_NODES))
    delete broken[9].content.definition.range
    delete broken[10].content.definition.emoji_list
    const raw = JSON.stringify(broken)
    let issues: SurveyNodeImportIssue[] = []
    try {
      parseSurveyNodeJson(raw)
      throw new Error('Expected import failure')
    } catch (error) {
      expect(error).toBeInstanceOf(SurveyNodeImportError)
      issues = (error as SurveyNodeImportError).issues
    }
    expect(issues.map((issue) => issue.path)).toEqual([
      '$[9].content.definition.range', '$[10].content.definition.emoji_list',
    ])
    const repair = buildSurveyNodeFixPrompt(raw, issues, 'All question types')
    expect(extractSchema(repair)).toEqual(surveyNodeImportJsonSchema)
    expect(repair).toContain('USER REQUEST\nAll question types')
    expect(repair).toContain('"range": {')
    expect(repair).toContain('"emoji_list": "sad_to_happy"')
    expect(repair).toContain(`JSON TO REPAIR\n${raw}`)
    broken[9].content.definition.range = { min: 0, max: 10, step: 1 }
    broken[10].content.definition.emoji_list = 'sad_to_happy'
    expect(parseSurveyNodeJson(JSON.stringify(broken))).toHaveLength(broken.length)
  })

  it('copies every validation issue even when the modal only displays the first eight', () => {
    const issues = Array.from({ length: 20 }, (_, index): SurveyNodeImportIssue => ({
      path: `$[${index}].id`, message: `Invalid id ${index}`, suggestion: 'Use a UUID',
      nodeIndex: index, line: index + 1, column: 5,
    }))
    const prompt = buildSurveyNodeFixPrompt('[]', issues, '')
    for (const issue of issues) expect(prompt).toContain(issue.message)
    expect(prompt).toContain('20. $[19].id, line 20 col 5, node index 19: Invalid id 19 Suggested fix: Use a UUID')
  })

  it('includes JSON escaping guidance even for syntax-error repairs', () => {
    const raw = '[{"placeholder":"example\\@email.com"}]'
    let issues: SurveyNodeImportIssue[] = []
    try { parseSurveyNodeJson(raw) } catch (error) {
      expect(error).toBeInstanceOf(SurveyNodeImportError)
      issues = (error as SurveyNodeImportError).issues
    }
    expect(issues[0].path).toBe('$')
    expect(buildSurveyNodeFixPrompt(raw, issues, '')).toContain('Do not escape @')
  })
})
