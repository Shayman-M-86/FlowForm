import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";
import { isSurveyNodeArray } from "../../components/form_filler/previewStorage";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

export interface DraftStorage {
  load: () => SurveyNode[] | null;
  save: (nodes: SurveyNode[]) => void;
  clear: () => void;
}

/**
 * localStorage-backed persistence for a builder draft, keyed by `key`. Unlike
 * previewStorage (sessionStorage, for the editor → filler handoff), this
 * survives a full page reload so a standalone/demo builder keeps its work.
 *
 * Framework-agnostic: the consumer owns the React state and decides when to
 * load/save. All access is guarded so SSR and storage failures are no-ops.
 */
export function draftStorage(key: string): DraftStorage {
  return {
    load() {
      if (typeof window === "undefined") return null;
      try {
        const stored = window.localStorage.getItem(key);
        if (!stored) return null;
        const parsed: unknown = JSON.parse(stored);
        return isSurveyNodeArray(parsed) ? parsed : null;
      } catch {
        return null;
      }
    },
    save(nodes: SurveyNode[]) {
      if (typeof window === "undefined") return;
      try {
        window.localStorage.setItem(key, JSON.stringify(nodes));
      } catch {
        // Ignore storage failures (quota, private mode, etc.).
      }
    },
    clear() {
      if (typeof window === "undefined") return;
      try {
        window.localStorage.removeItem(key);
      } catch {
        // Ignore.
      }
    },
  };
}
