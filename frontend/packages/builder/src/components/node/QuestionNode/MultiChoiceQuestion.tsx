import { useMemo, useRef, useState } from "react";
import { Button, Input, LargeInput, NumberStepperGroup } from "@flowform/ui";
import { useOptionDrag } from "../useOptionDrag";
import { QUESTION_MAX, TITLE_MAX, blurOnEnter, nextAvailableTag } from "../NodePillUtils";
import {
  NodePillTopbar,
  NodePillIdField,
  NodePillQuestionField,
  NodePillCharCount,
  NodePillFieldHead,
  NodePillDragThresholds,
  NodePillCollapsed,
} from "../NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillLimitTextClass,
  nodePillOptionAddClass,
  nodePillOptionFieldClass,
  nodePillOptionFieldEditClass,
  nodePillOptionGrabClass,
  nodePillOptionHandleClass,
  nodePillOptionInlineMetaClass,
  nodePillOptionMainClass,
  nodePillOptionMetaGroupClass,
  nodePillOptionMetaLabelClass,
  nodePillOptionRowClass,
  nodePillOptionDraggingClass,
  nodePillOptionsListClass,
  nodePillShellClass,
  nodePillShellEditClass,
} from "../nodePillStyles";
import type { ChoiceContent } from "../questionTypes";
import type { CreateQuestionNodeRequest } from "@flowform/schema";

export type MultiChoiceQuestionNode = Omit<CreateQuestionNodeRequest, "content"> & {
  content: ChoiceContent;
};

interface MultiChoiceQuestionProps {
  node: MultiChoiceQuestionNode;
  onChange: (next: MultiChoiceQuestionNode) => void;
  onDelete?: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed?: boolean;
  isEditMode?: boolean;
  onExpand?: () => void;
  onExpandInEditMode?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
}

const ANSWER_POOL = 4000;
const ANSWER_PER_FIELD_MAX = 1000;
const MAX_ANSWERS = 10;

type OptionRow = {
  id: string;
  placeholder: string;
  value: string;
  tag: string;
};

function contentToOptions(content: ChoiceContent): OptionRow[] {
  if (!content.definition.options.length) {
    return [{ id: "answer-1", placeholder: "Answer choice A", value: "", tag: "A" }];
  }
  return content.definition.options.map((option, index) => ({
    id: `answer-${index + 1}`,
    placeholder: `Answer choice ${option.id || String.fromCharCode(65 + index)}`,
    value: option.label,
    tag: option.id,
  }));
}

export function MultiChoiceQuestion({
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
}: MultiChoiceQuestionProps) {
  const { content } = node;
  const titleValue = content.title ?? "";
  const questionValue = content.label;
  const minChoices = content.definition.min;
  const maxChoices = content.definition.max;

  const [options, setOptions] = useState<OptionRow[]>(() => contentToOptions(content));
  const [openOptionIds, setOpenOptionIds] = useState<Set<string>>(new Set());
  const nextOptionIndexRef = useRef(options.length + 1);

  const {
    activeDrag,
    optionsListRef,
    optionRefs,
    startDrag,
    getDragTransform,
    getThresholdRatioForIndex,
  } = useOptionDrag(options, setOptions);

  function updateContent(update: (current: ChoiceContent) => ChoiceContent) {
    onChange({ ...node, content: update(content) });
  }

  function updateNodeKey(nextNodeKey: string) {
    onChange({ ...node, node_key: nextNodeKey });
  }

  function updateTitle(nextTitle: string) {
    updateContent((current) => ({ ...current, title: nextTitle || undefined }));
  }

  function updateQuestion(nextQuestion: string) {
    updateContent((current) => ({ ...current, label: nextQuestion }));
  }

  function updateMinChoices(value: number) {
    updateContent((current) => ({
      ...current,
      definition: {
        ...current.definition,
        min: value,
        max: Math.max(current.definition.max, value),
      },
    }));
  }

  function updateMaxChoices(value: number) {
    updateContent((current) => ({
      ...current,
      definition: {
        ...current.definition,
        max: Math.max(current.definition.min, value),
      },
    }));
  }

  const syncOptions = useMemo(
    () => (nextOptions: OptionRow[]) => {
      updateContent((current) => ({
        ...current,
        definition: {
          ...current.definition,
          options: nextOptions.map((opt) => ({ id: opt.tag, label: opt.value })),
        },
      }));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [node.node_key],
  );

  function setOptionsAndSync(updater: (current: OptionRow[]) => OptionRow[]) {
    setOptions((current) => {
      const next = updater(current);
      syncOptions(next);
      return next;
    });
  }

  function availableCharactersFor(optionId: string) {
    const usedByOthers = options
      .filter((option) => option.id !== optionId)
      .reduce((sum, option) => sum + option.value.length, 0);
    return Math.min(ANSWER_PER_FIELD_MAX, ANSWER_POOL - usedByOthers);
  }

  function toggleOptionPanel(optionId: string) {
    setOpenOptionIds((current) => {
      const next = new Set(current);
      if (next.has(optionId)) {
        next.delete(optionId);
      } else {
        next.add(optionId);
      }
      return next;
    });
  }

  function deleteOption(optionId: string) {
    setOptionsAndSync((current) => current.filter((entry) => entry.id !== optionId));
    setOpenOptionIds((current) => {
      if (!current.has(optionId)) return current;
      const next = new Set(current);
      next.delete(optionId);
      return next;
    });
  }

  function toggleEditMode() {
    onEditModeChange?.(!isEditMode);
  }

  if (isCollapsed) {
    return (
      <NodePillCollapsed
        family="Multiple choice"
        tagValue={node.node_key}
        title={titleValue}
        onExpand={() => onExpand?.()}
        onExpandInEditMode={() => onExpandInEditMode?.()}
      />
    );
  }

  return (
    <section
      className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`}
      aria-label="node workspace"
    >
      <NodePillTopbar
        family="Multiple choice"
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
        settings={{
          tagValue: node.node_key,
          onTagChange: updateNodeKey,
          titleValue,
          onTitleChange: updateTitle,
          idError,
        }}
      />

      <div className={nodePillBodyClass}>
        <NodePillQuestionField
          idField={
            <NodePillIdField
              tagValue={node.node_key}
              onTagChange={updateNodeKey}
              idError={idError}
              isEditMode={isEditMode}
            />
          }
          value={questionValue}
          onChange={updateQuestion}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={updateTitle}
          titleMax={TITLE_MAX}
          showTitleEdit
          validationError={
            validationError && !options.some((o) => !o.value.trim()) ? validationError : undefined
          }
        />

        <div className={nodePillFieldClass}>
          {isEditMode && (
            <NodePillFieldHead label="Answers">
              {isEditMode && (
                <div className="ml-auto inline-flex items-center gap-1.5">
                  <span className="text-[0.7rem] text-muted-foreground opacity-60">Choices</span>
                  <NumberStepperGroup
                    ariaLabel="Choices range"
                    size="xs"
                    variant="ghost"
                    items={[
                      {
                        key: "min",
                        label: "Min",
                        value: minChoices,
                        min: 1,
                        max: options.length,
                        disabled: !isEditMode,
                      },
                      {
                        key: "max",
                        label: "Max",
                        value: maxChoices,
                        min: minChoices,
                        max: options.length,
                        disabled: !isEditMode,
                      },
                    ]}
                    onChange={(key, value) => {
                      if (key === "min") {
                        updateMinChoices(value);
                      } else {
                        updateMaxChoices(value);
                      }
                    }}
                  />
                </div>
              )}
              {isEditMode && (
                <NodePillCharCount
                  label="Total"
                  value={options.reduce((sum, o) => sum + o.value.length, 0)}
                  max={ANSWER_POOL}
                  tooltip="Total characters used across all answer choices."
                />
              )}
            </NodePillFieldHead>
          )}
          <div className={nodePillOptionsListClass} ref={optionsListRef}>
            {options.map((option, index) => {
              const isOpen = openOptionIds.has(option.id);
              const isDragging = activeDrag?.id === option.id;
              const thresholdRatio = getThresholdRatioForIndex(index);
              const dragTransform = getDragTransform(index);
              const fieldMax = availableCharactersFor(option.id);

              return (
                <div
                  key={option.id}
                  ref={(node) => {
                    optionRefs.current[option.id] = node;
                  }}
                  className={`${nodePillOptionRowClass} ${isDragging ? nodePillOptionDraggingClass : ""}`}
                  style={dragTransform}
                >
                  <NodePillDragThresholds
                    itemId={option.id}
                    isDragging={isDragging}
                    thresholdRatio={activeDrag && !isDragging ? thresholdRatio : null}
                    activeDrag={activeDrag}
                  />
                  {isEditMode && (
                    <Button
                      className={nodePillOptionHandleClass}
                      variant="primary"
                      type="button"
                      aria-label={`${option.placeholder} settings`}
                      aria-expanded={isOpen}
                      onClick={() => toggleOptionPanel(option.id)}
                    >
                      <span aria-hidden="true">⋮</span>
                    </Button>
                  )}
                  <div
                    className={`${nodePillOptionFieldClass} ${isEditMode ? `${nodePillOptionFieldEditClass} flex-row items-stretch` : ""}${validationError && !option.value.trim() ? " ring-2 ring-destructive" : ""}`}
                  >
                    <div className="flex min-w-0 flex-1 flex-col">
                      <div className={nodePillOptionMainClass}>
                        <div className="min-w-0 flex-1">
                          <LargeInput
                            className="w-full"
                            shellClassName="border-0 rounded-none"
                            variant={isEditMode ? "secondary" : "ghost"}
                            placeholder={option.placeholder}
                            rows={1}
                            maxText={fieldMax}
                            maxAutoGrowHeight={190}
                            value={option.value}
                            autoGrow
                            readOnly={!isEditMode}
                            onChange={(event) =>
                              setOptionsAndSync((current) =>
                                current.map((entry) =>
                                  entry.id === option.id
                                    ? { ...entry, value: event.target.value }
                                    : entry,
                                ),
                              )
                            }
                          />
                        </div>
                      </div>

                      {isEditMode && option.value.length === fieldMax && (
                        <span className={`${nodePillLimitTextClass} px-1.5`}>
                          Maximum characters reached.
                        </span>
                      )}

                      {isEditMode && isOpen && (
                        <div className={nodePillOptionInlineMetaClass}>
                          <div className={nodePillOptionMetaGroupClass}>
                            <span className={nodePillOptionMetaLabelClass}>Answer tag</span>
                            <Input
                              size="sm"
                              type="text"
                              placeholder={`answer_${index + 1}`}
                              value={option.tag}
                              onChange={(event) =>
                                setOptionsAndSync((current) =>
                                  current.map((entry) =>
                                    entry.id === option.id
                                      ? { ...entry, tag: event.target.value }
                                      : entry,
                                  ),
                                )
                              }
                              onKeyDown={blurOnEnter}
                            />
                          </div>
                          <Button
                            type="button"
                            variant="danger"
                            size="xs"
                            onClick={() => deleteOption(option.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      )}
                    </div>

                    {isEditMode && (
                      <button
                        className={nodePillOptionGrabClass}
                        type="button"
                        aria-label={`Reorder ${option.placeholder}`}
                        onPointerDown={(event) => startDrag(event, option.id, index)}
                      >
                        <span aria-hidden="true">⋮⋮</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
            {isEditMode && options.length < MAX_ANSWERS && (
              <Button
                className={nodePillOptionAddClass}
                type="button"
                variant="ghost"
                borderStyle="dotted"
                onClick={() => {
                  const n = nextOptionIndexRef.current++;
                  setOptionsAndSync((current) => [
                    ...current,
                    {
                      id: `answer-${n}`,
                      placeholder: `Answer choice ${nextAvailableTag(current)}`,
                      value: "",
                      tag: nextAvailableTag(current),
                    },
                  ]);
                }}
              >
                <span aria-hidden="true">+</span>
                Add another choice
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
