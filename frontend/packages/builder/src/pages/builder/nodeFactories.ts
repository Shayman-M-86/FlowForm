import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

export type QuestionFamily = "choice" | "matching" | "rating" | "field";
export type NodeKind = QuestionFamily | "rule";

/**
 * Stable client-side identity for a node. A large positive integer is enough:
 * the backend primary key is (survey_version_id, id), so collisions within a
 * single version are vanishingly unlikely. Kept within Number.MAX_SAFE_INTEGER.
 */
export function createNodeId(): number {
  const buffer = new Uint32Array(2);
  crypto.getRandomValues(buffer);
  // buffer[0] occupies the high bits (<< 20), buffer[1] >>> 12 fills the low 20.
  return buffer[0] * 0x100000 + (buffer[1] >>> 12);
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
