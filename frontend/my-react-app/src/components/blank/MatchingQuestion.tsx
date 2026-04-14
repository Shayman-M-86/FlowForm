import { useRef, useState } from "react";
import "./MatchingQuestion.css";
import { useOptionDrag } from "./useOptionDrag";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const QUESTION_MAX = 5000;
const ANSWER_POOL = 2000;
const ANSWER_PER_FIELD_MAX = 250;

type MatchItem = {
  id: string;
  placeholder: string;
  value: string;
  tag: string;
};

type MatchItemDrag = {
  activeDrag: ReturnType<typeof useOptionDrag>["activeDrag"];
  optionsListRef: ReturnType<typeof useOptionDrag>["optionsListRef"];
  optionRefs: ReturnType<typeof useOptionDrag>["optionRefs"];
  startDrag: ReturnType<typeof useOptionDrag>["startDrag"];
  getDragTransform: ReturnType<typeof useOptionDrag>["getDragTransform"];
  getThresholdRatioForIndex: ReturnType<typeof useOptionDrag>["getThresholdRatioForIndex"];
};

const INITIAL_LEFT_ITEMS: MatchItem[] = [
  { id: "left-1", placeholder: "Prompt A", value: "", tag: "A" },
];

const INITIAL_RIGHT_ITEMS: MatchItem[] = [
  { id: "right-1", placeholder: "Match A", value: "", tag: "A" },
];

function nextAvailableTag(items: { tag: string }[]) {
  const used = new Set(items.map((item) => item.tag));
  for (const letter of ALPHABET) {
    if (!used.has(letter)) return letter;
  }
  return "";
}

export function MatchingQuestion() {
  const [isEditMode, setIsEditMode] = useState(true);
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [openItemIds, setOpenItemIds] = useState<Set<string>>(new Set());
  const [leftItems, setLeftItems] = useState(INITIAL_LEFT_ITEMS);
  const [rightItems, setRightItems] = useState(INITIAL_RIGHT_ITEMS);

  const nextLeftIndexRef = useRef(2);
  const nextRightIndexRef = useRef(2);

  const leftDrag = useOptionDrag(leftItems, setLeftItems);
  const rightDrag = useOptionDrag(rightItems, setRightItems);

  const totalCharacters = [...leftItems, ...rightItems].reduce(
    (sum, item) => sum + item.value.length,
    0,
  );

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

  function availableCharactersFor(itemId: string) {
    const usedByOthers = [...leftItems, ...rightItems]
      .filter((item) => item.id !== itemId)
      .reduce((sum, item) => sum + item.value.length, 0);
    return Math.min(ANSWER_PER_FIELD_MAX, ANSWER_POOL - usedByOthers);
  }

  function toggleItemPanel(itemId: string) {
    setOpenItemIds((current) => {
      const next = new Set(current);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  function deleteItem(
    itemId: string,
    setItems: React.Dispatch<React.SetStateAction<MatchItem[]>>,
  ) {
    setItems((current) => current.filter((entry) => entry.id !== itemId));
    setOpenItemIds((current) => {
      if (!current.has(itemId)) return current;
      const next = new Set(current);
      next.delete(itemId);
      return next;
    });
  }

  function renderThresholds(
    isDragging: boolean,
    thresholdRatio: number | null,
    returnThresholdRatio: number | null,
    insertLockThresholdRatio: number | null,
  ) {
    return (
      <>
        {thresholdRatio !== null && !isDragging && (
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
      </>
    );
  }

  function renderColumn(
    title: string,
    singularTitle: string,
    items: MatchItem[],
    setItems: React.Dispatch<React.SetStateAction<MatchItem[]>>,
    drag: MatchItemDrag,
    nextIndexRef: React.MutableRefObject<number>,
    idPrefix: "left" | "right",
  ) {
    return (
      <section className="blank-pill__match-column">
        <div className="blank-pill__match-column-head">
          <span className="blank-pill__match-column-label">{title}</span>
          {isEditMode && (
            <span className="blank-pill__match-column-count">{items.length}</span>
          )}
        </div>

        <div className="blank-pill__options" ref={drag.optionsListRef}>
          {items.map((item, index) => {
            const isOpen = openItemIds.has(item.id);
            const isDragging = drag.activeDrag?.id === item.id;
            const thresholdRatio = drag.getThresholdRatioForIndex(index);
            const dragTransform = drag.getDragTransform(index);

            const isReturnLockSibling = drag.activeDrag?.reverseLock?.siblingId === item.id;
            const returnThresholdRatio = isReturnLockSibling && drag.activeDrag?.reverseLock
              ? drag.activeDrag.reverseLock.direction === "down" ? 0.85 : 0.15
              : null;

            const isInsertLockSibling = drag.activeDrag?.insertLock?.siblingId === item.id;
            const insertLockThresholdRatio = isInsertLockSibling && drag.activeDrag?.insertLock
              ? drag.activeDrag.insertLock.direction === "down" ? 0.15 : 0.85
              : null;

            const fieldMax = availableCharactersFor(item.id);

            return (
              <div
                key={item.id}
                ref={(node) => {
                  drag.optionRefs.current[item.id] = node;
                }}
                className={`blank-pill__option-row ${isDragging ? "blank-pill__option-row--dragging" : ""}`}
                style={dragTransform}
              >
                {renderThresholds(
                  isDragging,
                  thresholdRatio,
                  returnThresholdRatio,
                  insertLockThresholdRatio,
                )}

                {isEditMode && (
                  <button
                    className="blank-pill__option-handle"
                    type="button"
                    aria-label={`${item.placeholder} settings`}
                    aria-expanded={isOpen}
                    onClick={() => toggleItemPanel(item.id)}
                  >
                    <span aria-hidden="true">⋮</span>
                  </button>
                )}

                <div className="blank-pill__option-field">
                  <div className="blank-pill__option-main">
                    <textarea
                      className="blank-pill__option"
                      placeholder={item.placeholder}
                      rows={1}
                      maxLength={fieldMax}
                      value={item.value}
                      readOnly={!isEditMode}
                      onChange={(event) =>
                        setItems((current) =>
                          current.map((entry) =>
                            entry.id === item.id ? { ...entry, value: event.target.value } : entry,
                          ),
                        )
                      }
                      onInput={(event) => autoResizeTextarea(event.currentTarget)}
                    />

                    {isEditMode && (
                      <button
                        className="blank-pill__option-grab"
                        type="button"
                        aria-label={`Reorder ${item.placeholder}`}
                        onPointerDown={(event) => drag.startDrag(event, item.id, index)}
                      >
                        <span aria-hidden="true">⋮⋮</span>
                      </button>
                    )}
                  </div>

                  {isEditMode && item.value.length === fieldMax && (
                    <span className="blank-pill__option-limit">
                      Maximum characters reached.
                    </span>
                  )}

                  {isEditMode && isOpen && (
                    <div className="blank-pill__option-inline-meta">
                      <div className="blank-pill__option-meta-group">
                        <span className="blank-pill__option-meta-label">Item tag</span>
                        <input
                          className="blank-pill__option-tag-input"
                          type="text"
                          placeholder={`${idPrefix}_${index + 1}`}
                          value={item.tag}
                          onChange={(event) =>
                            setItems((current) =>
                              current.map((entry) =>
                                entry.id === item.id ? { ...entry, tag: event.target.value } : entry,
                              ),
                            )
                          }
                          onKeyDown={blurOnEnter}
                        />
                      </div>

                      <button
                        className="blank-pill__option-delete"
                        type="button"
                        onClick={() => deleteItem(item.id, setItems)}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isEditMode && (
            <button
              className="blank-pill__option-add"
              type="button"
              onClick={() => {
                const nextTag = nextAvailableTag(items);
                const nextIndex = nextIndexRef.current++;
                setItems((current) => [
                  ...current,
                  {
                    id: `${idPrefix}-${nextIndex}`,
                    placeholder: `${singularTitle} ${nextTag || nextIndex}`,
                    value: "",
                    tag: nextTag,
                  },
                ]);
              }}
            >
              <span aria-hidden="true">+</span>
              Add {singularTitle.toLowerCase()}
            </button>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className={`blank-pill ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Matching question">
      <header className="blank-pill__topbar">
        <div className="blank-pill__topbar-left">
          <span className="blank-pill__family">Matching</span>
          <input
            className={`blank-pill__topbar-tag ${!isEditMode ? "blank-pill__topbar-tag--view" : ""}`}
            type="text"
            placeholder={isEditMode ? "question_id" : ""}
            value={tagValue}
            maxLength={40}
            size={Math.max(11, tagValue.length + 2)}
            readOnly={!isEditMode}
            onChange={(event) => setTagValue(event.target.value)}
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
            onClick={() => setIsEditMode((mode) => !mode)}
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
                onChange={(event) => setQuestionValue(event.target.value)}
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
            <span className="blank-pill__label">Pairs</span>
            {isEditMode && (
              <span className="blank-pill__answer-char-count">
                <span className="blank-pill__answer-char-count-item">
                  <span
                    className="blank-pill__answer-char-count-label"
                    data-tooltip="Total characters used across both matching columns."
                  >
                    Total
                  </span>
                  <span className="blank-pill__answer-char-count-value">{totalCharacters}</span>
                </span>
                <span className="blank-pill__answer-char-count-divider">/</span>
                <span className="blank-pill__answer-char-count-item">
                  <span className="blank-pill__answer-char-count-label">Max</span>
                  <span className="blank-pill__answer-char-count-value">{ANSWER_POOL}</span>
                </span>
              </span>
            )}
          </span>

          <div className="blank-pill__matching-grid">
            {renderColumn("Prompts", "Prompt", leftItems, setLeftItems, leftDrag, nextLeftIndexRef, "left")}
            {renderColumn("Matches", "Match", rightItems, setRightItems, rightDrag, nextRightIndexRef, "right")}
          </div>
        </div>
      </div>
    </section>
  );
}
