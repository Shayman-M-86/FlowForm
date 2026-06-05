import { Card, Select } from "@flowform/ui";
import type { MatchingContent, RuleCondition } from "../../questionTypes";
import {
  choiceTagClass,
  getMatch,
  pickerHeadClass,
  pickerHintClass,
  pickerTitleClass,
  setMatchingPair,
} from "./ruleEditorHelpers";

type MatchingCondition = Extract<RuleCondition, { family: "matching" }>;

interface MatchingConditionEditorProps {
  condition: MatchingCondition;
  target: MatchingContent;
  targetTitle: string;
  isEditMode: boolean;
  onChange: (next: MatchingCondition) => void;
}

export function MatchingConditionEditor({
  condition,
  target,
  targetTitle,
  isEditMode,
  onChange,
}: MatchingConditionEditorProps) {
  const matchOptions = [
    { value: "", label: "Any match" },
    ...target.definition.matches.map((m) => ({
      value: m.id,
      label: `${m.label || "—"} (${m.id})`,
    })),
  ];

  function setPair(promptId: string, matchId: string) {
    onChange({
      ...condition,
      requirements: {
        required: setMatchingPair(condition.requirements.required, promptId, matchId),
      },
    });
  }

  return (
    <Card tone="muted" size="sm" className="flex flex-col gap-2.5">
      <div className={pickerHeadClass}>
        <span className={pickerTitleClass}>{targetTitle}</span>
        <span className={pickerHintClass}>Required pairings</span>
      </div>
      <div className="flex flex-col gap-2">
        {target.definition.prompts.map((prompt) => (
          <div key={prompt.id} className="grid grid-cols-1 items-center gap-3 sm:grid-cols-2">
            <span className="flex min-w-0 flex-1 items-center gap-2">
              <span className={choiceTagClass}>{prompt.id}</span>
              <span className="overflow-hidden text-ellipsis text-[0.92rem] text-foreground">
                {prompt.label || "—"}
              </span>
            </span>
            <Select
              value={getMatch(condition.requirements.required, prompt.id)}
              options={matchOptions}
              disabled={!isEditMode}
              onChange={(event) => setPair(prompt.id, event.target.value)}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}
