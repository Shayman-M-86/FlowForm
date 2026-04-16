import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import { Button } from "../ui/Button";
import "./MatchingQuestion.css";
import { useOptionDrag } from "./useOptionDrag";
import { QUESTION_MAX, autoResizeTextarea, blurOnEnter, nextAvailableTag } from "./blankPillUtils";
import { BlankPillTopbar, BlankPillQuestionField, BlankPillCharCount, BlankPillFieldHead, BlankPillDragThresholds } from "./BlankPillShell";
import { Input } from "../ui/Input";

export interface MatchingQuestionData {
  id: string;
  title: string;
  label: string;
  family: "matching";
  matching: {
    schema: {
      prompts: Array<{ id: string; label: string }>;
      matches: Array<{ id: string; label: string }>;
    };
    ui: object;
  };
}

export interface MatchingQuestionHandle {
  getData(): MatchingQuestionData;
}

interface MatchingQuestionProps {
  onDelete?: () => void;
  title?: string;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (summary: { title: string; id: string }) => void;
}

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

export const MatchingQuestion = forwardRef<MatchingQuestionHandle, MatchingQuestionProps>(function MatchingQuestion({ onDelete, title, onEditModeChange, onDataChange }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(title ?? "");
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

  const matchingData: MatchingQuestionData = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "matching",
    matching: {
      schema: {
        prompts: leftItems.map((item) => ({ id: item.tag, label: item.value })),
        matches: rightItems.map((item) => ({ id: item.tag, label: item.value })),
      },
      ui: {},
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return matchingData;
    },
  }));

  useEffect(() => {
    onDataChange?.({ title: titleValue, id: tagValue });
  }, [titleValue, tagValue]);

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

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
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
                <BlankPillDragThresholds
                  itemId={item.id}
                  isDragging={isDragging}
                  thresholdRatio={drag.activeDrag && !isDragging ? thresholdRatio : null}
                  activeDrag={drag.activeDrag}
                />

                {isEditMode && (
                  <Button
                    className="blank-pill__option-handle"
                    type="button"
                    aria-label={`${item.placeholder} settings`}
                    aria-expanded={isOpen}
                    onClick={() => toggleItemPanel(item.id)}
                  >
                    <span aria-hidden="true">⋮</span>
                  </Button>
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
                        <Input
                          className=""
                          size="sm"
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

                      <Button
                        className="blank-pill__option-delete"
                        type="button"
                        variant="danger"
                        size="xs"
                        pill={true}
                        onClick={() => deleteItem(item.id, setItems)}
                      >
                        Delete
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {isEditMode && (
            <Button
              className="blank-pill__option-add"
              type="button"
              variant="ghost"
              borderStyle="dotted"
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
            </Button>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className={`blank-pill ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Matching question">
      <BlankPillTopbar
        family="Matching"
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
          <BlankPillFieldHead label="Pairs">
            {isEditMode && (
              <BlankPillCharCount
                label="Total"
                value={totalCharacters}
                max={ANSWER_POOL}
                tooltip="Total characters used across both matching columns."
              />
            )}
          </BlankPillFieldHead>

          <div className="blank-pill__matching-grid">
            {renderColumn("Prompts", "Prompt", leftItems, setLeftItems, leftDrag, nextLeftIndexRef, "left")}
            {renderColumn("Matches", "Match", rightItems, setRightItems, rightDrag, nextRightIndexRef, "right")}
          </div>
        </div>
      </div>
    </section>
  );
});
