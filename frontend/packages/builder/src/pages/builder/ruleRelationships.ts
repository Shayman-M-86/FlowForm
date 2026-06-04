import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;
type QuestionContent = CreateQuestionNodeRequest["content"];

export interface RuleSiblings {
  previous: QuestionContent[];
  following: QuestionContent[];
}

/**
 * For every rule node, collect the content of the question nodes that come
 * before it and after it (in array order). RulesQuestion uses these to offer
 * branching targets. Keyed by the rule node's id.
 */
export function buildRuleSiblings(nodes: SurveyNode[]): Map<number, RuleSiblings> {
  const questionContents = nodes
    .filter((node) => node.node_type !== "rule")
    .map((node) => node.content as QuestionContent);

  const siblings = new Map<number, RuleSiblings>();
  const previous: QuestionContent[] = [];
  let consumed = 0;

  for (const node of nodes) {
    if (node.node_type !== "rule") {
      previous.push(node.content as QuestionContent);
      consumed += 1;
      continue;
    }

    siblings.set(node.id, {
      previous: [...previous],
      following: questionContents.slice(consumed),
    });
  }

  return siblings;
}
