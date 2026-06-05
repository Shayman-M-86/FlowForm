import { Button, Card, CardStack, Select } from "@flowform/ui";
import type { RuleBranch, RuleSetEntry } from "../../questionTypes";
import {
  addBtnClass,
  DO_OPTIONS,
  doToKind,
  doToSkipTo,
  emptyTextClass,
  makeDo,
  questionOption,
  toggleRowClass,
  type DoKind,
  type QuestionNode,
} from "./ruleEditorHelpers";

interface RuleBranchEditorProps {
  branch: RuleBranch;
  siblings: QuestionNode[];
  isEditMode: boolean;
  allowSet: boolean;
  onChange: (branch: RuleBranch) => void;
}

export function RuleBranchEditor({
  branch,
  siblings,
  isEditMode,
  allowSet,
  onChange,
}: RuleBranchEditorProps) {
  const targetOptions = [
    { value: "", label: "Select a question…" },
    ...siblings.map(questionOption),
  ];
  const mode: "set" | "do" = branch.do ? "do" : "set";
  const setEntries = branch.set ?? [];

  function updateSet(entries: RuleSetEntry[]) {
    onChange({ set: entries });
  }

  function updateDo(kind: DoKind, skipTo: string) {
    onChange({ do: makeDo(kind, skipTo) });
  }

  function addSetEntry(targetId: string) {
    if (!targetId) return;
    updateSet([...setEntries, { target_id: targetId }]);
  }

  function updateSetEntry(index: number, patch: Partial<RuleSetEntry>) {
    updateSet(setEntries.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));
  }

  function removeSetEntry(index: number) {
    updateSet(setEntries.filter((_, i) => i !== index));
  }

  if (allowSet) {
    return (
      <>
        {isEditMode && (
          <div className="flex justify-end px-4 pt-1">
            <Select
              value={mode}
              options={[
                { value: "set", label: "Set" },
                { value: "do", label: "Do" },
              ]}
              onChange={(event) =>
                event.target.value === "set"
                  ? updateSet(setEntries)
                  : updateDo(doToKind(branch.do), doToSkipTo(branch.do))
              }
            />
          </div>
        )}
        {mode === "set" ? (
          <CardStack gap="sm" className="px-4 py-3">
            {setEntries.length === 0 && <p className={emptyTextClass}>No set entries yet.</p>}
            {setEntries.map((entry, index) => (
              <Card
                key={index}
                tone="muted"
                size="sm"
                className="grid grid-cols-1 items-center gap-2.5 sm:grid-cols-[1fr_auto_auto_auto]"
              >
                <span className="flex min-w-0 items-center gap-2 text-[0.92rem] text-foreground">
                  {targetOptions.find((o) => o.value === entry.target_id)?.label ?? entry.target_id}
                </span>
                <label className={toggleRowClass}>
                  <input
                    type="checkbox"
                    checked={entry.visible === false}
                    disabled={!isEditMode}
                    onChange={(event) =>
                      updateSetEntry(index, {
                        visible: event.target.checked ? false : undefined,
                      })
                    }
                  />
                  Hide
                </label>
                <label className={toggleRowClass}>
                  <input
                    type="checkbox"
                    checked={entry.required === true}
                    disabled={!isEditMode}
                    onChange={(event) =>
                      updateSetEntry(index, {
                        required: event.target.checked ? true : undefined,
                      })
                    }
                  />
                  Required
                </label>
                {isEditMode && (
                  <Button
                    type="button"
                    variant="danger"
                    size="xs"
                    onClick={() => removeSetEntry(index)}
                  >
                    Remove
                  </Button>
                )}
              </Card>
            ))}
            {isEditMode && (
              <Select
                className={addBtnClass}
                label="Add set target"
                value=""
                options={targetOptions}
                onChange={(event) => addSetEntry(event.target.value)}
              />
            )}
          </CardStack>
        ) : (
          <DoEditor
            branch={branch}
            targetOptions={targetOptions}
            isEditMode={isEditMode}
            onChange={updateDo}
          />
        )}
      </>
    );
  }

  return (
    <DoEditor
      branch={branch}
      targetOptions={targetOptions}
      isEditMode={isEditMode}
      onChange={updateDo}
    />
  );
}

function DoEditor({
  branch,
  targetOptions,
  isEditMode,
  onChange,
}: {
  branch: RuleBranch;
  targetOptions: Array<{ value: string; label: string }>;
  isEditMode: boolean;
  onChange: (kind: DoKind, skipTo: string) => void;
}) {
  const kind = doToKind(branch.do);
  const skipTo = doToSkipTo(branch.do);

  return (
    <div className="flex flex-row flex-wrap items-end gap-3 px-4 py-3">
      <Select
        label="Action"
        value={kind}
        options={DO_OPTIONS}
        disabled={!isEditMode}
        onChange={(event) => onChange(event.target.value as DoKind, skipTo)}
      />
      {kind === "skip_to" && (
        <Select
          label="Skip target"
          value={skipTo}
          options={targetOptions}
          disabled={!isEditMode}
          onChange={(event) => onChange("skip_to", event.target.value)}
        />
      )}
    </div>
  );
}
