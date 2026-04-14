import { useRef, useState } from "react";
import "./MultiChoiceQuestion.css";
import { useOptionDrag } from "./useOptionDrag";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

function nextAvailableTag(options: { tag: string }[]): string {
  const used = new Set(options.map((o) => o.tag));
  for (const letter of ALPHABET) {
    if (!used.has(letter)) return letter;
  }
  return "";
}

const INITIAL_OPTIONS = [
  { id: "answer-1", placeholder: "Answer choice A", value: "", tag: "A", ghost: false },
];

const ANSWER_POOL = 4000;
const ANSWER_PER_FIELD_MAX = 1000;
const MAX_ANSWERS =   10;

export function MultiChoiceQuestion() {
  const QUESTION_MAX = 5000;
  const [isEditMode, setIsEditMode] = useState(true);
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

  function blurOnEnter(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      (event.currentTarget as HTMLElement).blur();
    }
  }

  function autoResizeTextarea(element: HTMLTextAreaElement) {
    element.style.height = "0px";
    const maxHeight = element.classList.contains("blank-pill__question") ? 600 : 200;
    const nextHeight = Math.min(element.scrollHeight, maxHeight);
    element.style.height = `${nextHeight}px`;
    element.style.overflowY = element.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  return (
    <section className={`blank-pill ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Blank workspace">
      <header className="blank-pill__topbar">
        <div className="blank-pill__topbar-left">
          <span className="blank-pill__family">Multiple choice</span>
          <input
            className={`blank-pill__topbar-tag ${!isEditMode ? "blank-pill__topbar-tag--view" : ""}`}
            type="text"
            placeholder={isEditMode ? "question_id" : ""}
            value={tagValue}
            maxLength={40}
            size={Math.max(11, tagValue.length + 2)}
            readOnly={!isEditMode}
            onChange={(e) => setTagValue(e.target.value)}
            onKeyDown={blurOnEnter}
          />
        </div>
        <div className="blank-pill__actions">
          {isEditMode && (
            <>
              <button className="blank-pill__action blank-pill__action--danger" type="button">
                Delete
              </button>
              <button className="blank-pill__action" type="button">
                Settings
              </button>
            </>
          )}
          <button
            className={`blank-pill__action ${isEditMode ? "blank-pill__action--active" : ""}`}
            type="button"
            onClick={() => setIsEditMode((m) => !m)}
          >
            {isEditMode ? "Editing" : "Edit"}
          </button>
        </div>
      </header>

      <div className="blank-pill__body">
        <div className="blank-pill__field">
          <span className="blank-pill__label">Question</span>
          <div className="blank-pill__question-stack">
            <div className="blank-pill__question-field">
              <textarea
                className="blank-pill__question"
                placeholder="Type your question here"
                rows={3}
                maxLength={QUESTION_MAX}
                value={questionValue}
                readOnly={!isEditMode}
                onChange={(e) => setQuestionValue(e.target.value)}
                onInput={(event) => autoResizeTextarea(event.currentTarget)}
              />
            </div>
            {isEditMode && questionValue.length === QUESTION_MAX && (
              <span className="blank-pill__question-limit">
                Maximum {QUESTION_MAX} characters reached.
              </span>
            )}
          </div>
        </div>

        <div className="blank-pill__field">
          <span className="blank-pill__field-head">
            <span className="blank-pill__label">Answers</span>
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
              <span className="blank-pill__answer-char-count">
                <span className="blank-pill__answer-char-count-item">
                  <span className="blank-pill__answer-char-count-label" data-tooltip="Total characters used across all answer choices.">Total</span>
                  <span className="blank-pill__answer-char-count-value">{options.reduce((sum, o) => sum + o.value.length, 0)}</span>
                </span>
                <span className="blank-pill__answer-char-count-divider">/</span>
                <span className="blank-pill__answer-char-count-item">
                  <span className="blank-pill__answer-char-count-label">Max</span>
                  <span className="blank-pill__answer-char-count-value">{ANSWER_POOL}</span>
                </span>
              </span>
            )}
          </span>
          <div className="blank-pill__options" ref={optionsListRef}>
            {options.map((option, index) => {
              const isOpen = openOptionIds.has(option.id);
              const isDragging = activeDrag?.id === option.id;
              const thresholdRatio = getThresholdRatioForIndex(index);
              const dragTransform = getDragTransform(index);

              const isReturnLockSibling = activeDrag?.reverseLock?.siblingId === option.id;
              const returnThresholdRatio = isReturnLockSibling && activeDrag?.reverseLock
                ? activeDrag.reverseLock.direction === "down" ? 0.85 : 0.15
                : null;

              const isInsertLockSibling = activeDrag?.insertLock?.siblingId === option.id;
              const insertLockThresholdRatio = isInsertLockSibling && activeDrag?.insertLock
                ? activeDrag.insertLock.direction === "down" ? 0.15 : 0.85
                : null;

              return (
                <div
                  key={option.id}
                  ref={(node) => {
                    optionRefs.current[option.id] = node;
                  }}
                  className={`blank-pill__option-row ${isDragging ? "blank-pill__option-row--dragging" : ""}`}
                  style={dragTransform}
                >
                  {activeDrag && !isDragging && thresholdRatio !== null && (
                    <>
                      <div
                        className="blank-pill__option-threshold-line"
                        style={{ top: `${thresholdRatio * 100}%` }}
                      />
                      <div className="blank-pill__option-threshold-label">
                        {thresholdRatio.toFixed(2)}
                      </div>
                    </>
                  )}
                  {returnThresholdRatio !== null && (
                    <>
                      <div
                        className="blank-pill__option-threshold-line blank-pill__option-threshold-line--return"
                        style={{ top: `${returnThresholdRatio * 100}%` }}
                      />
                      <div className="blank-pill__option-threshold-label blank-pill__option-threshold-label--return">
                        {returnThresholdRatio.toFixed(2)}
                      </div>
                    </>
                  )}
                  {insertLockThresholdRatio !== null && (
                    <>
                      <div
                        className="blank-pill__option-threshold-line blank-pill__option-threshold-line--insert-lock"
                        style={{ top: `${insertLockThresholdRatio * 100}%` }}
                      />
                      <div className="blank-pill__option-threshold-label blank-pill__option-threshold-label--insert-lock">
                        {insertLockThresholdRatio.toFixed(2)}
                      </div>
                    </>
                  )}
                  {isEditMode && (
                    <button
                      className="blank-pill__option-handle"
                      type="button"
                      aria-label={`${option.placeholder} settings`}
                      aria-expanded={isOpen}
                      onClick={() => setOpenOptionIds((current) => {
                        const next = new Set(current);
                        next.has(option.id) ? next.delete(option.id) : next.add(option.id);
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
}
