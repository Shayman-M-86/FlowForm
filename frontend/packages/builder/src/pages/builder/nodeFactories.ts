import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

export type QuestionFamily = "choice" | "matching" | "rating" | "field";
export type NodeKind = QuestionFamily | "rule";

/** Stable client-side identity for a node in the backend UUID contract. */
export function createNodeId(): string {
  return crypto.randomUUID();
}

function createDefaultContent(kind: NodeKind): SurveyNode["content"] {
  switch (kind) {
    case "choice":
      return {
        family: "choice",
        label: "",
        title: null,
        definition: { min: 1, max: 1, options: [{ id: "A", label: "" }] },
      };
    case "matching":
      return {
        family: "matching",
        label: "",
        title: null,
        definition: {
          prompts: [{ id: "A", label: "" }],
          matches: [{ id: "A", label: "" }],
        },
      };
    case "rating":
      return {
        family: "rating",
        label: "",
        title: null,
        definition: {
          variant: "stars",
          stars: 5,
          ui: { left_label: "", right_label: "" },
        },
      };
    case "field":
      return {
        family: "field",
        label: "",
        title: null,
        definition: {
          field_type: "short_text",
          ui: { placeholder: "Type a short response" },
        },
      };
    case "rule":
      return {
        if: { match: "ALL", conditions: [] },
        then: { set: [] },
      };
  }
}

/** Build a complete, valid SurveyNode in the generated API shape. */
export function createDefaultNode(
  kind: NodeKind,
  sortKey: number,
  nodeKey: string,
): SurveyNode {
  const base = {
    id: createNodeId(),
    node_key: nodeKey,
    sort_key: sortKey,
  };

  if (kind === "rule") {
    return {
      ...base,
      node_type: "rule",
      content: createDefaultContent("rule"),
    } as SurveyNode;
  }

  return {
    ...base,
    node_type: "question",
    content: createDefaultContent(kind),
  } as SurveyNode;
}
