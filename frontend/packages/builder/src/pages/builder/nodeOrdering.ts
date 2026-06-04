import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";
import { incrementQuestionId } from "../../components/node/NodePillUtils";
import type { NodeKind } from "./nodeFactories";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

const SORT_KEY_STEP = 100000;

/** Next sort key after the current maximum, or the first step if empty. */
export function getNextSortKey(nodes: SurveyNode[]): number {
  const maxSortKey = nodes.reduce((max, node, index) => (
    Math.max(max, node.sort_key ?? (index + 1) * SORT_KEY_STEP)
  ), 0);
  return maxSortKey + SORT_KEY_STEP;
}

/**
 * Suggest the next node_key for a newly added node, incrementing from the last
 * node of the same kind (rules vs. questions are numbered independently).
 */
export function computeNextNodeKey(nodes: SurveyNode[], kind: NodeKind): string {
  const wantRule = kind === "rule";
  const sameKind = nodes.filter((node) => (node.node_type === "rule") === wantRule);
  if (sameKind.length === 0) return wantRule ? "r1" : "question_id_1";
  return incrementQuestionId(sameKind[sameKind.length - 1].node_key);
}

/** Move a node up or down by one position. Returns the same array if it can't move. */
export function moveNode(
  nodes: SurveyNode[],
  id: number,
  direction: "up" | "down",
): SurveyNode[] {
  const currentIndex = nodes.findIndex((node) => node.id === id);
  if (currentIndex === -1) return nodes;

  const targetIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;
  if (targetIndex < 0 || targetIndex >= nodes.length) return nodes;

  const next = [...nodes];
  const [moved] = next.splice(currentIndex, 1);
  next.splice(targetIndex, 0, moved);
  return next;
}

/**
 * The only validation the builder keeps: flag every node whose node_key collides
 * with another node's key. Returns the set of offending node ids.
 */
export function findDuplicateNodeKeyIds(nodes: SurveyNode[]): Set<number> {
  const idsByKey = new Map<string, number[]>();

  for (const node of nodes) {
    const key = node.node_key.trim();
    if (key === "") continue;
    idsByKey.set(key, [...(idsByKey.get(key) ?? []), node.id]);
  }

  const duplicates = new Set<number>();
  for (const ids of idsByKey.values()) {
    if (ids.length > 1) ids.forEach((id) => duplicates.add(id));
  }
  return duplicates;
}
