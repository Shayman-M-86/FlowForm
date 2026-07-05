import {
  NodePillTopbar,
  NodePillIdField,
  NodePillFieldHead,
  NodePillCollapsed,
} from "../../NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillShellClass,
  nodePillShellEditClass,
} from "../../nodePillStyles";
import type { CreateRuleNodeRequest } from "@flowform/schema";
import type {
  RuleBranch,
  RuleCondition,
  RuleMatch,
} from "../../questionTypes";
import { RuleConditionList } from "./RuleConditionList";
import { RuleBranchEditor } from "./RuleBranchEditor";
import { sectionClass, toggleRowClass, type QuestionNode } from "./ruleEditorHelpers";

export type RulesQuestionNode = CreateRuleNodeRequest;

interface RulesQuestionProps {
  node: RulesQuestionNode;
  onChange: (next: RulesQuestionNode) => void;
  onDelete?: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed?: boolean;
  isEditMode?: boolean;
  onExpand?: () => void;
  onExpandInEditMode?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
  previousSiblings?: QuestionNode[];
  followingSiblings?: QuestionNode[];
}

export function RulesQuestion({
  node,
  onChange,
  onDelete,
  idError,
  validationError,
  isCollapsed,
  isEditMode = false,
  onExpand,
  onExpandInEditMode,
  onEditModeChange,
  previousSiblings = [],
  followingSiblings = [],
}: RulesQuestionProps) {
  const { content } = node;
  const includeElse = content.else != null;

  // The generated rule node is the only editing state — every change emits a
  // fresh node. No parallel draft, no render-time propagation.
  function updateContent(next: RulesQuestionNode["content"]) {
    onChange({ ...node, content: next });
  }

  function updateNodeKey(nextNodeKey: string) {
    onChange({ ...node, node_key: nextNodeKey });
  }

  function updateMatch(match: RuleMatch) {
    updateContent({ ...content, if: { ...content.if, match } });
  }

  function updateConditions(conditions: RuleCondition[]) {
    updateContent({ ...content, if: { ...content.if, conditions } });
  }

  function updateThen(then: RuleBranch) {
    updateContent({ ...content, then });
  }

  function updateElse(branch: RuleBranch) {
    updateContent({ ...content, else: branch });
  }

  function toggleElse(enabled: boolean) {
    updateContent({ ...content, else: enabled ? { do: { end_and_submit: true } } : null });
  }

  function toggleEditMode() {
    onEditModeChange?.(!isEditMode);
  }

  if (isCollapsed) {
    return (
      <NodePillCollapsed
        family="Rule"
        tagValue={node.node_key}
        title={node.node_key}
        onExpand={() => onExpand?.()}
        onExpandInEditMode={() => onExpandInEditMode?.()}
      />
    );
  }

  return (
    <section
      className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`}
      aria-label="Rules question"
    >
      <NodePillTopbar
        family="Rule"
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
        idField={
          <NodePillIdField
            tagValue={node.node_key}
            onTagChange={updateNodeKey}
            idError={idError}
            isEditMode={isEditMode}
          />
        }
      />

      <div className={nodePillBodyClass}>
        {validationError && (
          <span className="text-[0.78rem] text-destructive">{validationError}</span>
        )}

        <RuleConditionList
          match={content.if.match}
          conditions={content.if.conditions}
          siblings={previousSiblings}
          isEditMode={isEditMode}
          onMatchChange={updateMatch}
          onConditionsChange={updateConditions}
        />

        <div className={`${nodePillFieldClass} ${sectionClass}`}>
          <NodePillFieldHead label="Then" />
          <RuleBranchEditor
            branch={content.then}
            siblings={followingSiblings}
            isEditMode={isEditMode}
            allowSet
            onChange={updateThen}
          />
        </div>

        <div className={`${nodePillFieldClass} ${sectionClass}`}>
          <NodePillFieldHead label="Else">
            {isEditMode && (
              <label className={toggleRowClass}>
                <input
                  type="checkbox"
                  checked={includeElse}
                  onChange={(event) => toggleElse(event.target.checked)}
                />
                Enabled
              </label>
            )}
          </NodePillFieldHead>

          {includeElse && content.else ? (
            <RuleBranchEditor
              branch={content.else}
              siblings={followingSiblings}
              isEditMode={isEditMode}
              allowSet={false}
              onChange={updateElse}
            />
          ) : (
            <p className="m-0 px-4 py-2 text-[0.88rem] text-muted-foreground">No else branch.</p>
          )}
        </div>
      </div>
    </section>
  );
}
