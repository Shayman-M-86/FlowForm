import { surveyNodeImportJsonSchema, type CreateQuestionNodeRequest } from "@flowform/schema";
import type { SurveyNode } from "../../node/questionTypes";
import type { SurveyNodeImportIssue } from "./surveyNodeImport";

const questionExamples: CreateQuestionNodeRequest["content"][] = [
  { family: "choice", label: "Where do you live?", definition: { min: 1, max: 1, options: [
    { id: "au", label: "Australia" }, { id: "us", label: "United States" },
  ] } },
  { family: "choice", label: "Select up to two activities.", definition: { min: 0, max: 2, options: [
    { id: "hiking", label: "Hiking" }, { id: "reading", label: "Reading" },
  ] } },
  { family: "field", label: "Your name?", definition: { field_type: "short_text", ui: { placeholder: "Your name" } } },
  { family: "field", label: "Describe your ideal holiday.", definition: { field_type: "long_text" } },
  { family: "field", label: "Your email address?", definition: { field_type: "email", ui: { placeholder: "example@email.com" } } },
  { family: "field", label: "Your phone number?", definition: { field_type: "phone" } },
  { family: "field", label: "How many countries have you visited?", definition: { field_type: "number" } },
  { family: "field", label: "When is your next holiday?", definition: { field_type: "date" } },
  { family: "rating", label: "Rate your last holiday.", definition: { variant: "stars", stars: 5, ui: { left_label: "Poor", right_label: "Excellent" } } },
  { family: "rating", label: "How excited are you?", definition: { variant: "slider", range: { min: 0, max: 10, step: 1 }, ui: { left_label: "Not excited", right_label: "Very excited" } } },
  { family: "rating", label: "How do you feel?", definition: { variant: "emoji", emoji_list: "sad_to_happy", words: true, ui: { left_label: "Unhappy", right_label: "Happy" } } },
  { family: "matching", label: "Match each state to its country.", definition: {
    prompts: [{ id: "victoria", label: "Victoria" }, { id: "california", label: "California" }, { id: "queensland", label: "Queensland" }],
    matches: [{ id: "au", label: "Australia" }, { id: "us", label: "United States" }],
  } },
];

// A complete importable example; tests check it through the actual importer.
export const AI_IMPORT_EXAMPLE_NODES: SurveyNode[] = [
  ...questionExamples.map((content, index): SurveyNode => ({
    id: `11111111-1111-4111-8111-${String(index + 1).padStart(12, "0")}`,
    node_key: `question_id_${index + 1}`, node_type: "question",
    sort_key: (index + 1) * 100000, content,
  })),
  {
    id: "11111111-1111-4111-8111-000000000013",
    node_key: "r1", node_type: "rule", sort_key: 1300000,
    content: {
      if: { match: "ALL", conditions: [
        { target_id: "question_id_1", family: "choice", requirements: { required: ["au"], forbidden: ["us"], any_of: ["au"] } },
        { target_id: "question_id_7", family: "field", requirements: { type: "number", operator: "GTE", value: 1 } },
        { target_id: "question_id_8", family: "field", requirements: { type: "date", operator: "after", value: "2026-01-01" } },
        { target_id: "question_id_9", family: "rating", requirements: { min: 4, max: 5 } },
        { target_id: "question_id_12", family: "matching", requirements: { required: [
          { prompt_id: "victoria", match_id: "au" }, { prompt_id: "queensland", match_id: "au" },
        ] } },
      ] },
      then: { set: [{ target_id: "question_id_13", visible: true, required: true }] },
      else: { do: { skip_to: "question_id_13" } },
    },
  },
  {
    id: "11111111-1111-4111-8111-000000000014",
    node_key: "question_id_13", node_type: "question", sort_key: 1400000,
    content: { family: "field", label: "Anything else to share?", definition: { field_type: "long_text" } },
  },
];

const SCHEMA_PROMPT = `You are a survey schema generator for FlowForm.

Return ONLY one raw JSON array of survey nodes. No explanation, markdown, code fences, comments, placeholders, ellipses, or trailing commas. Use double-quoted keys and strings, JSON booleans and finite numbers. Do not escape @ or apostrophes with a backslash; example@email.com is valid as written. Use literal Unicode for emoji.

The complete input JSON Schema below is authoritative. Follow every required field, enum, length, array limit, and numeric constraint. Resolve all $ref values within its $defs. Fields absent from an object's required list are optional; omit unused optional fields. Do not invent properties. This is a node-array import, not a survey-document wrapper or an API response.

QUESTION VARIANTS
- Choice: definition.min, max, options; max=1 for single choice, max>1 for multi-select.
- Fields: short_text, long_text, email, phone, number, date. Optional definition.ui.placeholder.
- Stars: definition.variant="stars", stars (integer 1–12), ui with left_label and right_label.
- Slider: definition.variant="slider", range={"min":0,"max":10,"step":1}, ui with both labels. range is required; min, max, step do not belong directly in definition.
- Emoji: definition.variant="emoji", emoji_list is ONE string: sad_to_happy | angry_to_happy | disgust_to_happy. It is not an array of emoji. Optional words is boolean. ui with both labels is required.
- Matching: definition.prompts and matches contain {"id":"...","label":"..."} items. Countries and states belong in these lists; more than one prompt can match the same country. Do not invent an answer-key property; required pairs belong to matching RULE conditions.
- title is an optional section heading inside question content. label is the required question text. family, title, label, definition belong in content, not at the node root.

IDENTITY AND ORDER
- Every node needs a unique UUID string id, unique node_key (1–128 characters), node_type, positive integer sort_key, and content.
- Use question_id_1, question_id_2, ... for questions and r1, r2, ... for rules. target_id and skip_to reference a QUESTION'S node_key, never its UUID or label.
- Keep array order and sort_key order aligned. Use (array index + 1) * 100000 for every node, including rules. No duplicate id, node_key, or sort_key.
- Return 1–500 nodes within 1,000,000 UTF-8 bytes.

CONSTRAINTS BEYOND JSON SCHEMA
- Choice: 1–10 options, option ids unique within the question, 0 <= min <= max <= option count.
- Matching: 1–10 prompts and 1–10 matches; ids unique within each list. Matching rule pairs must use existing prompt_id and match_id from the referenced question.
- Slider: -1000 <= min < max <= 1000 and step > 0.
- Rules require if and then; else is optional. if.match is ALL, ANY, or NONE over its conditions. Do not invent nested condition groups.
- Conditions can only reference EARLIER question sort_keys; family must match the target. Actions can only reference LATER question sort_keys.
- Choice conditions use required (all selected), forbidden (none selected), and/or any_of (at least one selected) arrays of existing option ids. Never put the same option in required and forbidden.
- Matching conditions use requirements.required=[{"prompt_id":"victoria","match_id":"au"}].
- Rating conditions use numeric min and/or max within the target's range (stars: 1..stars; emoji: 1..5; slider: range.min..range.max), with min <= max.
- Field conditions only support number and date targets: number uses type="number", operator LT|LTE|GT|GTE|EQ|NEQ and numeric value; date uses type="date", operator before|after and YYYY-MM-DD string value. No conditions on text/email/phone fields.
- Each then/else branch must contain exactly ONE of set or do. Omit the unused key. set is a nonempty list of unique future targets, each with at least one boolean visible or required.
- do must contain ONE action: {"skip_to":"question_id_13"}, {"end_and_submit":true}, or {"end_and_discard":true}. End actions have no target.

COMPLETE INPUT JSON SCHEMA
${JSON.stringify(surveyNodeImportJsonSchema, null, 2)}

VALID EXAMPLE ARRAY (all question types and rule condition families)
Adapt this example to the user request. Do not include every type unless requested. If all question types are requested, include single and multi-choice, all six field types, all three rating variants, and matching.
${JSON.stringify(AI_IMPORT_EXAMPLE_NODES, null, 2)}

Before returning, check JSON syntax, required variant fields, all limits, unique identities, every referenced option/item/node_key, and rule direction. Return the complete array, not a patch.
`;

export function buildSurveyNodePrompt(description: string): string {
  return `${SCHEMA_PROMPT}\nUSER REQUEST\n${description.trim()}`;
}

export function buildSurveyNodeFixPrompt(
  rawJson: string,
  issues: SurveyNodeImportIssue[],
  description: string,
): string {
  const summary = issues.map((issue, index) => {
    const location = [
      issue.path,
      issue.line ? `line ${issue.line}${issue.column ? ` col ${issue.column}` : ""}` : null,
      issue.nodeIndex !== null ? `node index ${issue.nodeIndex}` : null,
    ].filter(Boolean).join(", ");
    return `${index + 1}. ${location}: ${issue.message}${issue.suggestion ? ` Suggested fix: ${issue.suggestion}` : ""}`;
  }).join("\n");

  return `${buildSurveyNodePrompt(description)}\n\nREPAIR REQUEST\nThe previous JSON failed FlowForm import validation. Use the complete schema and examples above to fix ALL errors, then recheck the whole array. Preserve the user's survey content and intent. Return ONLY the complete corrected JSON array, no explanation or markdown. Do not ask the user to supply schema definitions; they are included above.\n\nVALIDATION ERRORS (${issues.length})\n${summary}\n\nJSON TO REPAIR\n${rawJson}`;
}
