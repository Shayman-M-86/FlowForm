import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

export type QuestionFamily = "choice" | "matching" | "rating" | "field";
export type NodeKind = QuestionFamily | "rule";

// Backend contract: a node id is a positive 32-bit integer (0 < id < 2147483647).
// Collisions are scoped to a single survey version (PK is (survey_version_id, id)),
// so the ~2.1e9 space is more than enough to keep them vanishingly unlikely.
const NODE_ID_MAX = 2147483646; // one below the backend's exclusive maximum

/** Stable client-side identity for a node: a random integer in [1, NODE_ID_MAX]. */
export function createNodeId(): number {
  const buffer = new Uint32Array(1);
  // Rejection-sample to avoid modulo bias against the top of the uint32 range.
  const limit = Math.floor(0x100000000 / NODE_ID_MAX) * NODE_ID_MAX;
  let value: number;
  do {
    crypto.getRandomValues(buffer);
    value = buffer[0];
  } while (value >= limit);
  return (value % NODE_ID_MAX) + 1;
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
