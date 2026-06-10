import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;
type QuestionNode = CreateQuestionNodeRequest;
type NodeId = SurveyNode["id"];

export interface RuleSiblings {
  previous: QuestionNode[];
  following: QuestionNode[];
}

/**
 * For every rule node, collect the question nodes that come before it and after
 * it (in array order). RulesQuestion uses these to offer branching targets and
 * to resolve a condition's target_id (node_key) to a readable label and its
 * content. Keyed by the rule node's id.
 */
export function buildRuleSiblings(nodes: SurveyNode[]): Map<NodeId, RuleSiblings> {
  const questionNodes = nodes.filter(
    (node): node is QuestionNode => node.node_type !== "rule",
  );

  const siblings = new Map<NodeId, RuleSiblings>();
  const previous: QuestionNode[] = [];
  let consumed = 0;

  for (const node of nodes) {
    if (node.node_type !== "rule") {
      previous.push(node);
      consumed += 1;
      continue;
    }

    siblings.set(node.id, {
      previous: [...previous],
      following: questionNodes.slice(consumed),
    });
  }

  return siblings;
}
