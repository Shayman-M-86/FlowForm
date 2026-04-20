import type {
  QuestionContent,
  QuestionNode,
  RuleContent,
  RuleNode,
  SurveyNode,
} from "./questionTypes";

export function serializeQuestions(contents: QuestionContent[]): QuestionNode[] {
  return contents.map((content, index) => ({
    type: "question",
    sort_key: (index + 1) * 100000,
    content,
  }));
}

export type SurveyEntry =
  | { kind: "question"; content: QuestionContent }
  | { kind: "rule"; content: RuleContent };

export function serializeSurveyEntries(entries: SurveyEntry[]): SurveyNode[] {
  return entries.map((entry, index) => {
    const sort_key = (index + 1) * 100000;
    if (entry.kind === "question") {
      return { type: "question", sort_key, content: entry.content };
    }
    return { type: "rule", sort_key, content: entry.content };
  });
}
