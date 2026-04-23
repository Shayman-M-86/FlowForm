import { useEffect, useRef, useState, forwardRef, useImperativeHandle } from "react";
import { Button, Input, LargeInput } from "@flowform/ui";
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
import type { MatchingContent } from "./questionTypes";

export interface MatchingQuestionHandle {
  getData(): MatchingContent;
}

interface MatchingQuestionProps {
  onDelete?: () => void;
  title?: string;
  initialTag?: string;
  initialContent?: MatchingContent;
  idError?: string;
  isCollapsed?: boolean;
  onExpand?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (content: MatchingContent) => void;
}

const ANSWER_POOL = 2000;
const ANSWER_PER_FIELD_MAX = 200;
const MAX_ITEMS_PER_COLUMN = 10;

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

export const MatchingQuestion = forwardRef<MatchingQuestionHandle, MatchingQuestionProps>(function MatchingQuestion({ onDelete, title, initialTag, initialContent, idError, isCollapsed, onExpand, onEditModeChange, onDataChange }, ref) {
  const initialLeftItems = initialContent?.definition.prompts.length
    ? initialContent.definition.prompts.map((item, index) => ({
      id: `left-${index + 1}`,
      placeholder: `Prompt ${item.id || String.fromCharCode(65 + index)}`,
      value: item.label,
      tag: item.id,
    }))
    : INITIAL_LEFT_ITEMS;
  const initialRightItems = initialContent?.definition.matches.length
    ? initialContent.definition.matches.map((item, index) => ({
      id: `right-${index + 1}`,
      placeholder: `Match ${item.id || String.fromCharCode(65 + index)}`,
      value: item.label,
      tag: item.id,
    }))
    : INITIAL_RIGHT_ITEMS;
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(initialContent?.title ?? title ?? "");
  const [questionValue, setQuestionValue] = useState(initialContent?.label ?? "");
  const [tagValue, setTagValue] = useState(initialContent?.id ?? initialTag ?? "question_id_1");
  const [openItemIds, setOpenItemIds] = useState<Set<string>>(new Set());
  const [leftItems, setLeftItems] = useState(initialLeftItems);
  const [rightItems, setRightItems] = useState(initialRightItems);

  const nextLeftIndexRef = useRef(initialLeftItems.length + 1);
  const nextRightIndexRef = useRef(initialRightItems.length + 1);

  const leftDrag = useOptionDrag(leftItems, setLeftItems);
  const rightDrag = useOptionDrag(rightItems, setRightItems);

  const totalCharacters = [...leftItems, ...rightItems].reduce(
    (sum, item) => sum + item.value.length,
    0,
  );

  const matchingData: MatchingContent = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "matching",
    definition: {
      prompts: leftItems.map((item) => ({ id: item.tag, label: item.value })),
      matches: rightItems.map((item) => ({ id: item.tag, label: item.value })),
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return matchingData;
    },
  }));

  useEffect(() => {
    onDataChange?.(matchingData);
  }, [titleValue, tagValue, questionValue, leftItems, rightItems]);

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
    columnTitle: string,
    singularTitle: string,
    items: MatchItem[],
    setItems: React.Dispatch<React.SetStateAction<MatchItem[]>>,
    drag: MatchItemDrag,
    nextIndexRef: React.MutableRefObject<number>,
    idPrefix: "left" | "right",
  ) {
    return (
      <section className="flex min-w-0 flex-col gap-2.5">
        <div className="flex items-center justify-between gap-2.5">
          <span className="text-[0.95rem] font-semibold text-foreground">{columnTitle}</span>
          {isEditMode && (
            <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full border border-border px-2 text-[0.78rem] text-muted-foreground">
              {items.length}
            </span>
          )}
        </div>

        <div className={nodePillOptionsListClass} ref={drag.optionsListRef}>
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
                className={`${nodePillOptionRowClass} ${isDragging ? nodePillOptionDraggingClass : ""}`}
                style={dragTransform}
              >
                <NodePillDragThresholds
                  itemId={item.id}
                  isDragging={isDragging}
                  thresholdRatio={drag.activeDrag && !isDragging ? thresholdRatio : null}
                  activeDrag={drag.activeDrag}
                />

                {isEditMode && (
                  <Button
                    className={nodePillOptionHandleClass}
                    variant="primary"
                    type="button"
                    aria-label={`${item.placeholder} settings`}
                    aria-expanded={isOpen}
                    onClick={() => toggleItemPanel(item.id)}
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
                          placeholder={item.placeholder}
                          rows={1}
                          maxText={fieldMax}
                          maxAutoGrowHeight={110}
                          value={item.value}
                          autoGrow
                          readOnly={!isEditMode}
                          onChange={(event) =>
                            setItems((current) =>
                              current.map((entry) =>
                                entry.id === item.id ? { ...entry, value: event.target.value } : entry,
                              ),
                            )
                          }
                        />
                      </div>
                    </div>

                    {isEditMode && item.value.length === fieldMax && (
                      <span className={`${nodePillLimitTextClass} px-1.5`}>
                        Maximum characters reached.
                      </span>
                    )}

                    {isEditMode && isOpen && (
                      <div className={nodePillOptionInlineMetaClass}>
                        <div className={nodePillOptionMetaGroupClass}>
                          <span className={nodePillOptionMetaLabelClass}>Item tag</span>
                          <Input
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

                  {isEditMode && (
                    <button
                      className={nodePillOptionGrabClass}
                      type="button"
                      aria-label={`Reorder ${item.placeholder}`}
                      onPointerDown={(event) => drag.startDrag(event, item.id, index)}
                    >
                      <span aria-hidden="true">⋮⋮</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {isEditMode && items.length < MAX_ITEMS_PER_COLUMN && (
            <Button
              className={nodePillOptionAddClass}
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

  if (isCollapsed) {
    return <NodePillCollapsed family="Matching" tagValue={tagValue} title={titleValue} onExpand={() => { onExpand?.(); setIsEditMode(true); onEditModeChange?.(true); }} />;
  }

  return (
    <section className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`} aria-label="Matching question">
      <NodePillTopbar
        family="Matching"
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
          <NodePillFieldHead label="Pairs">
            {isEditMode && (
              <NodePillCharCount
                label="Total"
                value={totalCharacters}
                max={ANSWER_POOL}
                tooltip="Total characters used across both matching columns."
              />
            )}
          </NodePillFieldHead>

          <div className="grid gap-5 lg:grid-cols-2">
            {renderColumn("Prompts", "Prompt", leftItems, setLeftItems, leftDrag, nextLeftIndexRef, "left")}
            {renderColumn("Matches", "Match", rightItems, setRightItems, rightDrag, nextRightIndexRef, "right")}
          </div>
        </div>
      </div>
    </section>
  );
});
