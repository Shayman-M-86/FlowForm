import { useMemo, useState } from "react";
import type { MatchingContent } from "../node/questionTypes";

interface MatchingFormFillerProps {
  question: MatchingContent;
  value: Record<string, string>;
  onChange: (nextValue: Record<string, string>) => void;
}

const columnHeadClass = "flex items-center justify-between gap-2.5";
const columnLabelClass = "text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground";
const columnCountClass = "inline-flex h-5.5 min-w-5.5 items-center justify-center rounded-full border border-border px-2 text-[0.78rem] text-muted-foreground";
const pairedRowClass = "grid gap-3.5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]";

const matchingCardShellClass = "flex w-full min-w-0 items-center justify-center overflow-hidden rounded-2xl border transition-colors";
const matchingLabelClass = "flex min-h-[46px] max-h-[90px] w-full flex-col overflow-y-auto break-words px-3 py-2 text-center text-base font-semibold leading-6";

function MatchingLabel({ label }: { label: string }) {
  return <span className={matchingLabelClass}><span className="my-auto min-w-0">{label}</span></span>;
}

interface PromptChipProps {
  id: string;
  label: string;
  isSelected: boolean;
  isPlacementTarget?: boolean;
  onPick: (id: string) => void;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
}

function PromptChip({ id, label, isSelected, isPlacementTarget = false, onPick, onDragStart, onDragEnd }: PromptChipProps) {
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
        "col-start-1 row-start-1 select-none",
        isPlacementTarget ? "cursor-pointer" : "cursor-grab active:cursor-grabbing",
        isSelected
          ? "border-accent bg-accent/10 text-accent ring-1 ring-accent"
          : "border-border bg-card text-foreground",
      ].join(" ")}
    >
      <MatchingLabel label={label || id} />
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
  const [dragOverTarget, setDragOverTarget] = useState<string | null>(null);
  const activePromptId = draggedPromptId ?? selectedPromptId;
  const canReturnPrompt = Boolean(activePromptId && value[activePromptId]);
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
    handlePromptDragEnd();
  }

  function handleReturnToPromptList() {
    const promptId = activePromptId;
    if (!promptId || !value[promptId]) return;
    unassignPrompt(promptId);
    setSelectedPromptId(null);
    handlePromptDragEnd();
  }

  function handlePromptDragEnd() {
    setDraggedPromptId(null);
    setDragOverTarget(null);
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
            className={[
              "flex min-h-18 flex-col gap-3.5 rounded-2xl border border-dashed border-border/80 bg-muted/10 p-2 transition-colors",
              canReturnPrompt ? "cursor-pointer hover:border-accent hover:bg-accent/10 hover:ring-1 hover:ring-accent" : "",
              canReturnPrompt && dragOverTarget === "available" ? "border-accent bg-accent/10 ring-1 ring-accent" : "",
            ].join(" ")}
            onDragOver={(event) => {
              if (!draggedPromptId || !canReturnPrompt) return;
              event.preventDefault();
              event.dataTransfer.dropEffect = "move";
              setDragOverTarget("available");
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverTarget(null);
            }}
            onDrop={(event) => {
              event.preventDefault();
              const promptId = event.dataTransfer.getData("text/plain");
              if (promptId && value[promptId]) unassignPrompt(promptId);
              setSelectedPromptId(null);
              handlePromptDragEnd();
            }}
            onClick={() => {
              if (canReturnPrompt && selectedPromptId) handleReturnToPromptList();
            }}
          >
            <div
              className={[
                "flex min-h-13 items-center justify-center rounded-2xl border border-dashed px-4 text-center text-sm text-muted-foreground transition",
                canReturnPrompt ? "border-accent text-foreground" : "border-border/80",
              ].join(" ")}
            >
              Tap or drop a paired prompt here to unassign it.
            </div>

            <div className="grid">
              {/* Reserve the full list's natural height, including wrapped labels. */}
              <div aria-hidden="true" inert className="invisible col-start-1 row-start-1 flex flex-col gap-3.5">
                {question.definition.prompts.map((prompt) => (
                  <div key={prompt.id} className={matchingCardShellClass}>
                    <MatchingLabel label={prompt.label || prompt.id} />
                  </div>
                ))}
              </div>
              <div className="col-start-1 row-start-1 flex flex-col gap-3.5 self-start">
                {unassignedPrompts.map((prompt) => (
                  <PromptChip
                    key={prompt.id}
                    id={prompt.id}
                    label={prompt.label || prompt.id}
                    isSelected={selectedPromptId === prompt.id}
                    onPick={handlePromptPick}
                    onDragStart={setDraggedPromptId}
                    onDragEnd={handlePromptDragEnd}
                  />
                ))}
              </div>
            </div>
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
                        "grid min-w-0 rounded-2xl border p-0 transition-colors",
                        isPickingPrompt
                          ? "cursor-pointer border-dashed border-accent text-muted-foreground hover:bg-accent/10 hover:text-accent hover:ring-1 hover:ring-accent"
                          : assignedPrompt
                            ? "border-transparent bg-transparent"
                            : "border-border bg-muted/10 text-muted-foreground",
                        isPickingPrompt && dragOverTarget === `match:${match.id}` ? "bg-accent/10 text-accent ring-1 ring-accent" : "",
                      ].join(" ")}
                      onDragOver={(event) => {
                        if (!draggedPromptId) return;
                        event.preventDefault();
                        event.dataTransfer.dropEffect = "move";
                        setDragOverTarget(`match:${match.id}`);
                      }}
                      onDragLeave={(event) => {
                        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragOverTarget(null);
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        const promptId = event.dataTransfer.getData("text/plain");
                        if (promptId) assignPromptToMatch(promptId, match.id);
                        setSelectedPromptId(null);
                        handlePromptDragEnd();
                      }}
                      onClick={() => handleDropToMatch(match.id)}
                    >
                      {/* Each target reserves enough space for any prompt at this width. */}
                      {question.definition.prompts.map((prompt) => (
                        <div
                          key={prompt.id}
                          aria-hidden="true"
                          inert
                          className={[matchingCardShellClass, "invisible col-start-1 row-start-1"].join(" ")}
                        >
                          <MatchingLabel label={prompt.label || prompt.id} />
                        </div>
                      ))}
                      <span
                        aria-hidden={assignedPrompt ? true : undefined}
                        className={[
                          "col-start-1 row-start-1 flex min-h-13 w-full items-center justify-center px-4 py-3 text-center",
                          assignedPrompt ? "invisible" : "",
                        ].join(" ")}
                      >
                        Drop a prompt here
                      </span>
                      {assignedPrompt ? (
                        <PromptChip
                          id={assignedPrompt.id}
                          label={assignedPrompt.label || assignedPrompt.id}
                          isSelected={selectedPromptId === assignedPrompt.id}
                          isPlacementTarget={isPickingPrompt && (selectedPromptId ?? draggedPromptId) !== assignedPrompt.id}
                          onPick={(promptId) => {
                            if (selectedPromptId && selectedPromptId !== promptId) {
                              handleDropToMatch(match.id);
                            } else {
                              handlePromptPick(promptId);
                            }
                          }}
                          onDragStart={setDraggedPromptId}
                          onDragEnd={handlePromptDragEnd}
                        />
                      ) : null}
                    </div>

                    <div className={[matchingCardShellClass, "border-border bg-muted/40 text-foreground"].join(" ")}>
                      <MatchingLabel label={match.label || match.id} />
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
