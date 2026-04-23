import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import { Button, Input, LargeInput, NumberStepperGroup } from "@flowform/ui";
import { useOptionDrag } from "./useOptionDrag";
import { QUESTION_MAX, blurOnEnter, nextAvailableTag } from "./NodePillUtils";
import {
  NodePillTopbar,
  NodePillQuestionField,
  NodePillCharCount,
  NodePillFieldHead,
  NodePillDragThresholds,
  NodePillCollapsed,
} from "./NodePillShell";
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
} from "./nodePillStyles";
import type { ChoiceContent } from "./questionTypes";

export interface MultiChoiceQuestionHandle {
  getData(): ChoiceContent;
}

interface MultiChoiceQuestionProps {
  onDelete?: () => void;
  title?: string;
  initialTag?: string;
  initialContent?: ChoiceContent;
  idError?: string;
  isCollapsed?: boolean;
  onExpand?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (content: ChoiceContent) => void;
}

const INITIAL_OPTIONS = [
  { id: "answer-1", placeholder: "Answer choice A", value: "", tag: "A", ghost: false },
];

const ANSWER_POOL = 4000;
const ANSWER_PER_FIELD_MAX = 1000;
const MAX_ANSWERS = 10;

export const MultiChoiceQuestion = forwardRef<MultiChoiceQuestionHandle, MultiChoiceQuestionProps>(function MultiChoiceQuestion({ onDelete, title, initialTag, initialContent, idError, isCollapsed, onExpand, onEditModeChange, onDataChange }, ref) {
  const initialOptions = initialContent?.definition.options.length
    ? initialContent.definition.options.map((option, index) => ({
      id: `answer-${index + 1}`,
      placeholder: `Answer choice ${option.id || String.fromCharCode(65 + index)}`,
      value: option.label,
      tag: option.id,
      ghost: false,
    }))
    : INITIAL_OPTIONS;
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(initialContent?.title ?? title ?? "");
  const [questionValue, setQuestionValue] = useState(initialContent?.label ?? "");
  const [tagValue, setTagValue] = useState(initialContent?.id ?? initialTag ?? "question_id_1");
  const [minChoices, setMinChoices] = useState(initialContent?.definition.min ?? 1);
  const [maxChoices, setMaxChoices] = useState(initialContent?.definition.max ?? 1);
  const [openOptionIds, setOpenOptionIds] = useState<Set<string>>(new Set());
  const [options, setOptions] = useState(initialOptions);
  const nextOptionIndexRef = useRef(initialOptions.length + 1);

  const {
    activeDrag,
    optionsListRef,
    optionRefs,
    startDrag,
    getDragTransform,
    getThresholdRatioForIndex,
  } = useOptionDrag(options, setOptions);

  const multiChoiceData: ChoiceContent = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "choice",
    definition: {
      min: minChoices,
      max: maxChoices,
      options: options.map((opt) => ({ id: opt.tag, label: opt.value })),
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return multiChoiceData;
    },
  }));

  useEffect(() => {
    onDataChange?.(multiChoiceData);
  }, [titleValue, tagValue, questionValue, minChoices, maxChoices, options]);

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
    setOptions((current) => current.filter((entry) => entry.id !== optionId));
    setOpenOptionIds((current) => {
      if (!current.has(optionId)) return current;
      const next = new Set(current);
      next.delete(optionId);
      return next;
    });
  }

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  if (isCollapsed) {
    return <NodePillCollapsed family="Multiple choice" tagValue={tagValue} title={titleValue} onExpand={() => { onExpand?.(); setIsEditMode(true); onEditModeChange?.(true); }} />;
  }

  return (
    <section className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`} aria-label="node workspace">
      <NodePillTopbar
        family="Multiple choice"
        tagValue={tagValue}
        onTagChange={setTagValue}
        idError={idError}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className={nodePillBodyClass}>
        <NodePillQuestionField
          value={questionValue}
          onChange={setQuestionValue}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={setTitleValue}
          showTitleEdit={true}
        />

        <div className={nodePillFieldClass}>
          <NodePillFieldHead label="Answers">
            {isEditMode && (
              <div className="ml-auto inline-flex items-center gap-1.5">
                <span className="text-[0.7rem] text-muted-foreground opacity-60">Choices</span>
                <NumberStepperGroup
                  ariaLabel="Choices range"
                  size="xs"
                  pill
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
                      setMinChoices(value);
                      if (value > maxChoices) {
                        setMaxChoices(value);
                      }
                      return;
                    }
                    setMaxChoices(Math.max(minChoices, value));
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
                  <div className={`${nodePillOptionFieldClass} ${isEditMode ? `${nodePillOptionFieldEditClass} flex-row items-stretch` : ""}`}>
                    <div className="flex min-w-0 flex-1 flex-col">
                      <div className={nodePillOptionMainClass}>
                        <div className="min-w-0 flex-1">
                          <LargeInput
                            className="w-full"
                          shellClassName="border-0 rounded-none"
                          placeholder={option.placeholder}
                          rows={1}
                          maxText={fieldMax}
                          maxAutoGrowHeight={190}
                          value={option.value}
                          autoGrow
                          readOnly={!isEditMode}
                            onChange={(event) =>
                              setOptions((current) =>
                                current.map((entry) =>
                                  entry.id === option.id ? { ...entry, value: event.target.value } : entry
                                )
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
                                setOptions((current) =>
                                  current.map((entry) =>
                                    entry.id === option.id ? { ...entry, tag: event.target.value } : entry
                                  )
                                )
                              }
                              onKeyDown={blurOnEnter}
                            />
                          </div>
                          <Button
                            type="button"
                            variant="danger"
                            size="xs"
                            pill={true}
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
                  setOptions((current) => [
                    ...current,
                    { id: `answer-${n}`, placeholder: `Answer choice ${nextAvailableTag(current)}`, value: "", tag: nextAvailableTag(current), ghost: false },
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
});
