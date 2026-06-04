import { useRef, useState } from "react";
import { Button, Input, LargeInput } from "@flowform/ui";
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
import type { MatchingContent } from "../questionTypes";
import type { CreateQuestionNodeRequest } from "@flowform/schema";

export type MatchingQuestionNode = Omit<CreateQuestionNodeRequest, "content"> & {
  content: MatchingContent;
};

interface MatchingQuestionProps {
  node: MatchingQuestionNode;
  onChange: (next: MatchingQuestionNode) => void;
  onDelete?: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed?: boolean;
  isEditMode?: boolean;
  onExpand?: () => void;
  onExpandInEditMode?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
}

const ANSWER_POOL = 2000;
const ANSWER_PER_FIELD_MAX = 200;
const MAX_ITEMS_PER_COLUMN = 10;

type MatchItem = { id: string; placeholder: string; value: string; tag: string };

type MatchItemDrag = {
  activeDrag: ReturnType<typeof useOptionDrag>["activeDrag"];
  optionsListRef: ReturnType<typeof useOptionDrag>["optionsListRef"];
  optionRefs: ReturnType<typeof useOptionDrag>["optionRefs"];
  startDrag: ReturnType<typeof useOptionDrag>["startDrag"];
  getDragTransform: ReturnType<typeof useOptionDrag>["getDragTransform"];
  getThresholdRatioForIndex: ReturnType<typeof useOptionDrag>["getThresholdRatioForIndex"];
};

function contentToItems(
  items: MatchingContent["definition"]["prompts"] | MatchingContent["definition"]["matches"],
  idPrefix: string,
  fallbackLabel: string,
): MatchItem[] {
  if (!items.length) {
    return [{ id: `${idPrefix}-1`, placeholder: `${fallbackLabel} A`, value: "", tag: "A" }];
  }
  return items.map((item, index) => ({
    id: `${idPrefix}-${index + 1}`,
    placeholder: `${fallbackLabel} ${item.id || String.fromCharCode(65 + index)}`,
    value: item.label,
    tag: item.id,
  }));
}

export function MatchingQuestion({
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
}: MatchingQuestionProps) {
  const { content } = node;
  const titleValue = content.title ?? "";
  const questionValue = content.label;

  const [leftItems, setLeftItems] = useState<MatchItem[]>(() =>
    contentToItems(content.definition.prompts, "left", "Prompt"),
  );
  const [rightItems, setRightItems] = useState<MatchItem[]>(() =>
    contentToItems(content.definition.matches, "right", "Match"),
  );
  const [openItemIds, setOpenItemIds] = useState<Set<string>>(new Set());

  const nextLeftIndexRef = useRef(leftItems.length + 1);
  const nextRightIndexRef = useRef(rightItems.length + 1);

  const leftDrag = useOptionDrag(leftItems, setLeftItems);
  const rightDrag = useOptionDrag(rightItems, setRightItems);

  const totalCharacters = [...leftItems, ...rightItems].reduce(
    (sum, item) => sum + item.value.length,
    0,
  );

  function updateContent(update: (current: MatchingContent) => MatchingContent) {
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

  function syncItems(nextLeft: MatchItem[], nextRight: MatchItem[]) {
    updateContent((current) => ({
      ...current,
      definition: {
        prompts: nextLeft.map((item) => ({ id: item.tag, label: item.value })),
        matches: nextRight.map((item) => ({ id: item.tag, label: item.value })),
      },
    }));
  }

  function setLeftAndSync(updater: (current: MatchItem[]) => MatchItem[]) {
    setLeftItems((current) => {
      const next = updater(current);
      syncItems(next, rightItems);
      return next;
    });
  }

  function setRightAndSync(updater: (current: MatchItem[]) => MatchItem[]) {
    setRightItems((current) => {
      const next = updater(current);
      syncItems(leftItems, next);
      return next;
    });
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
    setItems: (updater: (current: MatchItem[]) => MatchItem[]) => void,
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
    onEditModeChange?.(!isEditMode);
  }

  function renderColumn(
    columnTitle: string,
    singularTitle: string,
    items: MatchItem[],
    setItems: (updater: (current: MatchItem[]) => MatchItem[]) => void,
    drag: MatchItemDrag,
    nextIndexRef: React.MutableRefObject<number>,
    idPrefix: "left" | "right",
  ) {
    const highlightEmpty = Boolean(validationError);
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

                <div
                  className={`${nodePillOptionFieldClass} ${isEditMode ? `${nodePillOptionFieldEditClass} flex-row items-stretch` : ""}${highlightEmpty && !item.value.trim() ? " ring-2 ring-destructive" : ""}`}
                >
                  <div className="flex min-w-0 flex-1 flex-col">
                    <div className={nodePillOptionMainClass}>
                      <div className="min-w-0 flex-1">
                        <LargeInput
                          className="w-full"
                          shellClassName="border-0 rounded-none"
                          variant={isEditMode ? "secondary" : "ghost"}
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
                                entry.id === item.id
                                  ? { ...entry, value: event.target.value }
                                  : entry,
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
                                  entry.id === item.id
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
    return (
      <NodePillCollapsed
        family="Matching"
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
      aria-label="Matching question"
    >
      <NodePillTopbar
        family="Matching"
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
            validationError &&
            !leftItems.some((i) => !i.value.trim()) &&
            !rightItems.some((i) => !i.value.trim())
              ? validationError
              : undefined
          }
        />

        <div className={nodePillFieldClass}>
          {isEditMode && (
            <NodePillFieldHead label="Pairs">
              <NodePillCharCount
                label="Total"
                value={totalCharacters}
                max={ANSWER_POOL}
                tooltip="Total characters used across both matching columns."
              />
            </NodePillFieldHead>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            {renderColumn("Prompts", "Prompt", leftItems, setLeftAndSync, leftDrag, nextLeftIndexRef, "left")}
            {renderColumn("Matches", "Match", rightItems, setRightAndSync, rightDrag, nextRightIndexRef, "right")}
          </div>
        </div>
      </div>
    </section>
  );
}
