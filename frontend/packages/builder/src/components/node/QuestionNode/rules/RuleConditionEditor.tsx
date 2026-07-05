import type {
  ChoiceContent,
  FieldContent,
  MatchingContent,
  RatingContent,
  RuleCondition,
} from "../../questionTypes";
import { ChoiceConditionEditor } from "./ChoiceConditionEditor";
import { MatchingConditionEditor } from "./MatchingConditionEditor";
import { RatingConditionEditor } from "./RatingConditionEditor";
import { FieldConditionEditor } from "./FieldConditionEditor";
import { findSibling, type QuestionNode } from "./ruleEditorHelpers";

interface RuleConditionEditorProps {
  condition: RuleCondition;
  siblings: QuestionNode[];
  isEditMode: boolean;
  onChange: (next: RuleCondition) => void;
}

export function RuleConditionEditor({
  condition,
  siblings,
  isEditMode,
  onChange,
}: RuleConditionEditorProps) {
  const target = findSibling(siblings, condition.target_id);

  if (!target) {
    return (
      <p className="m-0 text-[0.88rem] text-muted-foreground">
        The target question is no longer available.
      </p>
    );
  }

  const targetTitle =
    target.content.title?.trim() || target.content.label.trim() || target.node_key;

  // condition.family is kept in lockstep with the target's content.family by
  // createDefaultCondition / retargeting, so the narrowing casts are safe.
  switch (condition.family) {
    case "choice":
      return (
        <ChoiceConditionEditor
          condition={condition}
          target={target.content as ChoiceContent}
          targetTitle={targetTitle}
          isEditMode={isEditMode}
          onChange={onChange}
        />
      );
    case "matching":
      return (
        <MatchingConditionEditor
          condition={condition}
          target={target.content as MatchingContent}
          targetTitle={targetTitle}
          isEditMode={isEditMode}
          onChange={onChange}
        />
      );
    case "rating":
      return (
        <RatingConditionEditor
          condition={condition}
          target={target.content as RatingContent}
          targetTitle={targetTitle}
          isEditMode={isEditMode}
          onChange={onChange}
        />
      );
    case "field":
      return (
        <FieldConditionEditor
          condition={condition}
          target={target.content as FieldContent}
          targetTitle={targetTitle}
          isEditMode={isEditMode}
          onChange={onChange}
        />
      );
  }
}
