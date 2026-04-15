import { useRef, useState, forwardRef, useImperativeHandle } from "react";
import "./MultiChoiceQuestion.css";
import { useOptionDrag } from "./useOptionDrag";
import { QUESTION_MAX, autoResizeTextarea, blurOnEnter, nextAvailableTag } from "./blankPillUtils";
import { BlankPillTopbar, BlankPillQuestionField, BlankPillCharCount, BlankPillFieldHead, BlankPillDragThresholds } from "./BlankPillShell";

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
}

const INITIAL_OPTIONS = [
  { id: "answer-1", placeholder: "Answer choice A", value: "", tag: "A", ghost: false },
];

const ANSWER_POOL = 4000;
const ANSWER_PER_FIELD_MAX = 1000;
const MAX_ANSWERS = 10;

export const MultiChoiceQuestion = forwardRef<MultiChoiceQuestionHandle, MultiChoiceQuestionProps>(function MultiChoiceQuestion({ onDelete, title }, ref) {
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

  return (
    <section className={`blank-pill ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Blank workspace">
      <BlankPillTopbar
        family="Multiple choice"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={() => setIsEditMode((m) => !m)}
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
              <div className="blank-pill__choice-range">
                <div className="blank-pill__choice-range-field">
                  <span className="blank-pill__choice-range-label" data-tooltip="Minimum number of answers the user must select.">Min</span>
                  <div className="blank-pill__stepper">
                    <button
                      className="blank-pill__stepper-btn"
                      type="button"
                      disabled={!isEditMode || minChoices <= 1}
                      onClick={() => setMinChoices((v) => Math.max(1, v - 1))}
                    >−</button>
                    <span className="blank-pill__stepper-value">{minChoices}</span>
                    <button
                      className="blank-pill__stepper-btn"
                      type="button"
                      disabled={!isEditMode || minChoices >= options.length}
                      onClick={() => {
                        const next = Math.min(options.length, minChoices + 1);
                        setMinChoices(next);
                        if (next > maxChoices) setMaxChoices(next);
                      }}
                    >+</button>
                  </div>
                </div>
                <div className="blank-pill__choice-range-field">
                  <span className="blank-pill__choice-range-label" data-tooltip="Maximum number of answers the user can select.">Max</span>
                  <div className="blank-pill__stepper">
                    <button
                      className="blank-pill__stepper-btn"
                      type="button"
                      disabled={!isEditMode || maxChoices <= minChoices}
                      onClick={() => setMaxChoices((v) => Math.max(minChoices, v - 1))}
                    >−</button>
                    <span className="blank-pill__stepper-value">{maxChoices}</span>
                    <button
                      className="blank-pill__stepper-btn"
                      type="button"
                      disabled={!isEditMode || maxChoices >= options.length}
                      onClick={() => setMaxChoices((v) => Math.min(options.length, v + 1))}
                    >+</button>
                  </div>
                </div>
              </div>
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
                    <button
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
                    </button>
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
                          <input
                            className="blank-pill__option-tag-input"
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
                        <button
                          className="blank-pill__option-delete"
                          type="button"
                          onClick={() =>
                            setOptions((current) => current.filter((entry) => entry.id !== option.id))
                          }
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            {isEditMode && options.length < MAX_ANSWERS && (
              <button
                className="blank-pill__option-add"
                type="button"
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
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
});
