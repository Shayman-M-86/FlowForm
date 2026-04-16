import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import "./MultiChoiceQuestion.css";
import { Button } from "../ui/Button";
import { NumberStepperGroup } from "../ui/NumberStepperGroup";
import { useOptionDrag } from "./useOptionDrag";
import { QUESTION_MAX, autoResizeTextarea, blurOnEnter, nextAvailableTag } from "./blankPillUtils";
import { BlankPillTopbar, BlankPillQuestionField, BlankPillCharCount, BlankPillFieldHead, BlankPillDragThresholds } from "./BlankPillShell";
import { Input } from "../ui/Input";

export interface MultiChoiceQuestionData {
  id: string;
  title: string;
  label: string;
  family: "choice";
  choice: {
    schema: {
      options: Array<{ id: string; label: string }>;
      min_selected: number;
      max_selected: number;
    };
    ui: object;
  };
}

export interface MultiChoiceQuestionHandle {
  getData(): MultiChoiceQuestionData;
}

interface MultiChoiceQuestionProps {
  onDelete?: () => void;
  title?: string;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (summary: { title: string; id: string }) => void;
}

const INITIAL_OPTIONS = [
  { id: "answer-1", placeholder: "Answer choice A", value: "", tag: "A", ghost: false },
];

const ANSWER_POOL = 4000;
const ANSWER_PER_FIELD_MAX = 1000;
const MAX_ANSWERS = 10;

export const MultiChoiceQuestion = forwardRef<MultiChoiceQuestionHandle, MultiChoiceQuestionProps>(function MultiChoiceQuestion({ onDelete, title, onEditModeChange, onDataChange }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(title ?? "");
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [minChoices, setMinChoices] = useState(1);
  const [maxChoices, setMaxChoices] = useState(1);
  const [openOptionIds, setOpenOptionIds] = useState<Set<string>>(new Set());
  const [options, setOptions] = useState(INITIAL_OPTIONS);
  const nextOptionIndexRef = useRef(2);

  const {
    activeDrag,
    optionsListRef,
    optionRefs,
    startDrag,
    getDragTransform,
    getThresholdRatioForIndex,
  } = useOptionDrag(options, setOptions);

  const multiChoiceData: MultiChoiceQuestionData = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "choice",
    choice: {
      schema: {
        options: options.map((opt) => ({ id: opt.tag, label: opt.value })),
        min_selected: minChoices,
        max_selected: maxChoices,
      },
      ui: {},
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return multiChoiceData;
    },
  }));

  useEffect(() => {
    onDataChange?.({ title: titleValue, id: tagValue });
  }, [titleValue, tagValue]);

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  return (
    <section className={`blank-pill ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Blank workspace">
      <BlankPillTopbar
        family="Multiple choice"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className="blank-pill__body">
        <BlankPillQuestionField
          value={questionValue}
          onChange={setQuestionValue}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={setTitleValue}
          showTitleEdit={true}
        />

        <div className="blank-pill__field">
          <BlankPillFieldHead label="Answers">
            {isEditMode && <div className="blank-pill__choice-range-wrapper">
              <span className="blank-pill__choice-range-title">Choices</span>
              <NumberStepperGroup
                className="multi-choice-question__choice-range"
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
            </div>}
            {isEditMode && (
              <BlankPillCharCount
                label="Total"
                value={options.reduce((sum, o) => sum + o.value.length, 0)}
                max={ANSWER_POOL}
                tooltip="Total characters used across all answer choices."
              />
            )}
          </BlankPillFieldHead>
          <div className="blank-pill__options" ref={optionsListRef}>
            {options.map((option, index) => {
              const isOpen = openOptionIds.has(option.id);
              const isDragging = activeDrag?.id === option.id;
              const thresholdRatio = getThresholdRatioForIndex(index);
              const dragTransform = getDragTransform(index);

              return (
                <div
                  key={option.id}
                  ref={(node) => {
                    optionRefs.current[option.id] = node;
                  }}
                  className={`blank-pill__option-row ${isDragging ? "blank-pill__option-row--dragging" : ""}`}
                  style={dragTransform}
                >
                  <BlankPillDragThresholds
                    itemId={option.id}
                    isDragging={isDragging}
                    thresholdRatio={activeDrag && !isDragging ? thresholdRatio : null}
                    activeDrag={activeDrag}
                  />
                  {isEditMode && (
                    <Button
                      className="blank-pill__option-handle"
                      type="button"
                      aria-label={`${option.placeholder} settings`}
                      aria-expanded={isOpen}
                      onClick={() => setOpenOptionIds((current) => {
                        const next = new Set(current);
                        if (next.has(option.id)) {
                          next.delete(option.id);
                        } else {
                          next.add(option.id);
                        }
                        return next;
                      })}
                    >
                      <span aria-hidden="true">⋮</span>
                    </Button>
                  )}
                  <div className="blank-pill__option-field">
                    <div className="blank-pill__option-main">
                      <textarea
                        className="blank-pill__option"
                        placeholder={option.placeholder}
                        rows={1}
                        maxLength={Math.min(ANSWER_PER_FIELD_MAX, ANSWER_POOL - options.filter((e) => e.id !== option.id).reduce((sum, e) => sum + e.value.length, 0))}
                        value={option.value}
                        readOnly={!isEditMode}
                        onChange={(event) =>
                          setOptions((current) =>
                            current.map((entry) =>
                              entry.id === option.id ? { ...entry, value: event.target.value } : entry
                            )
                          )
                        }
                        onInput={(event) => autoResizeTextarea(event.currentTarget)}
                      />
                      {isEditMode && (
                        <button
                          className="blank-pill__option-grab"
                          type="button"
                          aria-label={`Reorder ${option.placeholder}`}
                          onPointerDown={(event) => startDrag(event, option.id, index)}
                        >
                          <span aria-hidden="true">⋮⋮</span>
                        </button>
                      )}
                    </div>
                    {isEditMode && option.value.length === Math.min(ANSWER_PER_FIELD_MAX, ANSWER_POOL - options.filter((e) => e.id !== option.id).reduce((sum, e) => sum + e.value.length, 0)) && (
                      <span className="blank-pill__option-limit">
                        Maximum characters reached.
                      </span>
                    )}
                    {isEditMode && isOpen && (
                      <div className="blank-pill__option-inline-meta">
                        <div className="blank-pill__option-meta-group">
                          <span className="blank-pill__option-meta-label">Answer tag</span>
                          <Input
                            className=""
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
                          className="blank-pill__option-delete"
                          type="button"
                          variant="danger"
                          size="xs"
                          pill={true}
                          onClick={() =>
                            setOptions((current) => current.filter((entry) => entry.id !== option.id))
                          }
                        >
                          Delete
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {isEditMode && options.length < MAX_ANSWERS && (
              <Button
                className="blank-pill__option-add"
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
