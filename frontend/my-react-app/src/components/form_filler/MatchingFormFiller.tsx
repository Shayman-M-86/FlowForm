import { useMemo, useState } from "react";
import type { MatchingContent } from "../node/questionTypes";
import { ExpandableTextArea } from "../../index.optimized";

interface MatchingFormFillerProps {
  question: MatchingContent;
  value: Record<string, string>;
  onChange: (nextValue: Record<string, string>) => void;
}

const columnHeadClass = "flex items-center justify-between gap-2.5";
const columnLabelClass = "text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground";
const columnCountClass = "inline-flex h-5.5 min-w-5.5 items-center justify-center rounded-full border border-border px-2 text-[0.78rem] text-muted-foreground";
const pairedRowClass = "grid gap-3.5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]";

const matchingCardShellClass = "flex w-full overflow-hidden rounded-2xl border transition";
const matchingTextAreaProps = {
  onChange: () => {},
  readOnly: true as const,
  minHeightClassName: "min-h-[46px]",
  maxHeightClassName: "max-h-[90px]",
  maxHeightPx: 90,
  className: "border-0 bg-transparent hover:border-0",
  textareaClassName: "font-semibold",
} as const;

interface PromptChipProps {
  id: string;
  label: string;
  isSelected: boolean;
  onPick: (id: string) => void;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
}

function PromptChip({ id, label, isSelected, onPick, onDragStart, onDragEnd }: PromptChipProps) {
  return (
    <div
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData("text/plain", id);
        event.dataTransfer.effectAllowed = "move";
        onDragStart(id);
      }}
      onDragEnd={onDragEnd}
      onClick={(event) => {
        event.stopPropagation();
        onPick(id);
      }}
      className={[
        matchingCardShellClass,
        "cursor-grab select-none active:cursor-grabbing",
        isSelected
          ? "border-accent bg-accent/10 text-accent ring-1 ring-accent"
          : "border-border bg-card text-foreground",
      ].join(" ")}
    >
      <ExpandableTextArea
        value={label || id}
        {...matchingTextAreaProps}
        textareaClassName="font-semibold cursor-grab active:cursor-grabbing"
      />
    </div>
  );
}

export function MatchingFormFiller({
  question,
  value,
  onChange,
}: MatchingFormFillerProps) {
  const [draggedPromptId, setDraggedPromptId] = useState<string | null>(null);
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const assignedPromptByMatchId = useMemo(() => {
    const next: Record<string, string> = {};
    for (const [promptId, matchId] of Object.entries(value)) {
      if (matchId) next[matchId] = promptId;
    }
    return next;
  }, [value]);
  const unassignedPrompts = question.definition.prompts.filter((prompt) => !value[prompt.id]);

  function assignPromptToMatch(promptId: string, matchId: string) {
    const sourceMatchId = value[promptId] ?? "";
    const promptCurrentlyAssignedToMatch = assignedPromptByMatchId[matchId];

    const nextValue: Record<string, string> = {
      ...value,
      [promptId]: matchId,
    };

    if (promptCurrentlyAssignedToMatch && promptCurrentlyAssignedToMatch !== promptId) {
      nextValue[promptCurrentlyAssignedToMatch] = sourceMatchId && sourceMatchId !== matchId
        ? sourceMatchId
        : "";
    }

    onChange(nextValue);
  }

  function unassignPrompt(promptId: string) {
    onChange({ ...value, [promptId]: "" });
  }

  function handlePromptPick(promptId: string) {
    setSelectedPromptId((current) => (current === promptId ? null : promptId));
  }

  function handleDropToMatch(matchId: string) {
    const promptId = selectedPromptId ?? draggedPromptId;
    if (!promptId) return;
    assignPromptToMatch(promptId, matchId);
    setSelectedPromptId(null);
    setDraggedPromptId(null);
  }

  function handleReturnToPromptList() {
    const promptId = selectedPromptId ?? draggedPromptId;
    if (!promptId) return;
    unassignPrompt(promptId);
    setSelectedPromptId(null);
    setDraggedPromptId(null);
  }

  const isPickingPrompt = Boolean(draggedPromptId || selectedPromptId);

  return (
    <div className="flex flex-col gap-4.5">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.6fr)]">
        <section className="flex flex-col gap-2.5">
          <div className={columnHeadClass}>
            <div className="flex items-center gap-2">
              <span className={columnLabelClass}>Available prompts</span>
              <span className="text-[0.72rem] text-muted-foreground">Pick Up and Match</span>
            </div>
            <span className={columnCountClass}>{unassignedPrompts.length}</span>
          </div>

          <div
            className="flex min-h-18 flex-col gap-3.5 rounded-2xl border border-dashed border-border/80 bg-muted/10 p-2"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const promptId = event.dataTransfer.getData("text/plain");
              if (promptId) unassignPrompt(promptId);
              setSelectedPromptId(null);
              setDraggedPromptId(null);
            }}
            onClick={() => {
              if (selectedPromptId) handleReturnToPromptList();
            }}
          >
            <div
              className={[
                "flex min-h-13 items-center justify-center rounded-2xl border border-dashed px-4 text-center text-sm text-muted-foreground transition",
                isPickingPrompt ? "border-accent text-foreground" : "border-border/80",
              ].join(" ")}
            >
              {isPickingPrompt
                ? "Tap or drop here to return the selected prompt."
                : "Drop a paired prompt here to unassign it."}
            </div>

            {unassignedPrompts.map((prompt) => (
              <PromptChip
                key={prompt.id}
                id={prompt.id}
                label={prompt.label || prompt.id}
                isSelected={selectedPromptId === prompt.id}
                onPick={handlePromptPick}
                onDragStart={setDraggedPromptId}
                onDragEnd={() => setDraggedPromptId(null)}
              />
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-2.5">
          <div className={pairedRowClass}>
            <div className={columnHeadClass}>
              <span className={columnLabelClass}>Drop prompts here</span>
              <span className={columnCountClass}>{question.definition.matches.length}</span>
            </div>
            <div className={columnHeadClass}>
              <span className={columnLabelClass}>Available matches</span>
              <span className={columnCountClass}>{question.definition.matches.length}</span>
            </div>
          </div>

          <div className="flex flex-col gap-3.5">
            {question.definition.matches.map((match) => {
              const assignedPromptId = assignedPromptByMatchId[match.id];
              const assignedPrompt = question.definition.prompts.find((p) => p.id === assignedPromptId);

              return (
                <div
                  key={match.id}
                  className="rounded-[1.6rem] border border-border bg-muted/10 p-2"
                >
                  <div className={pairedRowClass}>
                    <div
                      className={[
                        "flex rounded-2xl border p-0 transition",
                        isPickingPrompt
                          ? "border-dashed border-accent text-muted-foreground"
                          : assignedPrompt
                            ? "border-transparent bg-transparent"
                            : "border-border bg-muted/10 text-muted-foreground",
                      ].join(" ")}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => {
                        event.preventDefault();
                        const promptId = event.dataTransfer.getData("text/plain");
                        if (promptId) assignPromptToMatch(promptId, match.id);
                        setSelectedPromptId(null);
                        setDraggedPromptId(null);
                      }}
                      onClick={() => handleDropToMatch(match.id)}
                    >
                      {assignedPrompt ? (
                        <PromptChip
                          id={assignedPrompt.id}
                          label={assignedPrompt.label || assignedPrompt.id}
                          isSelected={selectedPromptId === assignedPrompt.id}
                          onPick={(promptId) => {
                            if (selectedPromptId && selectedPromptId !== promptId) {
                              handleDropToMatch(match.id);
                            } else {
                              handlePromptPick(promptId);
                            }
                          }}
                          onDragStart={setDraggedPromptId}
                          onDragEnd={() => setDraggedPromptId(null)}
                        />
                      ) : (
                        <span className="flex min-h-13 w-full items-center px-4 py-3">Drop a prompt here</span>
                      )}
                    </div>

                    <div className={[matchingCardShellClass, "border-border bg-muted/40 text-foreground"].join(" ")}>
                      <ExpandableTextArea
                        value={match.label || match.id}
                        {...matchingTextAreaProps}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
