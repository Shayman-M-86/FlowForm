import { useEffect, useRef, useState } from "react";

const OPTION_GAP = 18;
const OPTION_INSERT_THRESHOLD_UP = 0.55;
const OPTION_INSERT_THRESHOLD_DOWN = 0.45;
const OPTION_RETURN_THRESHOLD_UP = 0.85;
const OPTION_RETURN_THRESHOLD_DOWN = 0.15;
const OPTION_INSERT_LOCK_THRESHOLD_UP = 0.85;
const OPTION_INSERT_LOCK_THRESHOLD_DOWN = 0.15;
const OPTION_THRESHOLD_MIN = Math.min(OPTION_INSERT_THRESHOLD_UP, OPTION_INSERT_THRESHOLD_DOWN);
const OPTION_THRESHOLD_MAX = Math.max(OPTION_INSERT_THRESHOLD_UP, OPTION_INSERT_THRESHOLD_DOWN);

export { OPTION_GAP };

type Lock = { direction: "up" | "down"; siblingId: string };

export type ActiveDrag = {
  id: string;
  pointerOffsetY: number;
  startIndex: number;
  targetIndex: number;
  rowHeight: number;
  startTop: number;
  offsetY: number;
  reverseLock: Lock | null;
  insertLock: Lock | null;
};

type Option = { id: string };

export function useOptionDrag<T extends Option>(
  options: T[],
  setOptions: React.Dispatch<React.SetStateAction<T[]>>,
) {
  const optionsListRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);

  function getVisualIndex(index: number, drag: ActiveDrag) {
    if (drag.targetIndex < drag.startIndex) {
      if (index >= drag.targetIndex && index < drag.startIndex) return index + 1;
      return index;
    }
    if (drag.targetIndex > drag.startIndex) {
      if (index > drag.startIndex && index <= drag.targetIndex) return index - 1;
      return index;
    }
    return index;
  }

  function getThresholdRatio(index: number, drag: ActiveDrag) {
    const siblingVisualIndex = getVisualIndex(index, drag);
    return siblingVisualIndex > drag.targetIndex
      ? OPTION_INSERT_THRESHOLD_DOWN
      : OPTION_INSERT_THRESHOLD_UP;
  }

  function getOptionIdAtVisualIndex(visualIndex: number, drag: ActiveDrag) {
    for (let index = 0; index < options.length; index += 1) {
      const option = options[index];
      if (option.id === drag.id) continue;
      if (getVisualIndex(index, drag) === visualIndex) return option.id;
    }
    return null;
  }

  useEffect(() => {
    if (!activeDrag) return;

    const currentDrag = activeDrag;

    function handlePointerMove(event: PointerEvent) {
      const listElement = optionsListRef.current;
      if (!listElement) return;

      const listRect = listElement.getBoundingClientRect();
      const desiredTopInList = event.clientY - listRect.top - currentDrag.pointerOffsetY;
      const maxTopInList = listRect.height - currentDrag.rowHeight;
      const nextTopInList = Math.max(0, Math.min(maxTopInList, desiredTopInList));
      const nextOffset = nextTopInList - currentDrag.startTop;
      const draggedTopY = listRect.top + nextTopInList;
      const draggedBottomY = draggedTopY + currentDrag.rowHeight;

      let nextInsertLock = currentDrag.insertLock;
      if (nextInsertLock) {
        const siblingRect = optionRefs.current[nextInsertLock.siblingId]?.getBoundingClientRect();
        if (siblingRect) {
          const isCleared = nextInsertLock.direction === "down"
            ? draggedBottomY <= siblingRect.top + siblingRect.height * OPTION_INSERT_LOCK_THRESHOLD_DOWN
            : draggedTopY >= siblingRect.top + siblingRect.height * OPTION_INSERT_LOCK_THRESHOLD_UP;
          if (isCleared) nextInsertLock = null;
        }
      }

      let nextTargetIndex = currentDrag.targetIndex;
      if (!nextInsertLock) {
        nextTargetIndex = 0;
        for (let index = 0; index < options.length; index += 1) {
          const option = options[index];
          if (option.id === currentDrag.id) continue;
          const siblingRect = optionRefs.current[option.id]?.getBoundingClientRect();
          if (!siblingRect) continue;
          const siblingVisualIndex = getVisualIndex(index, currentDrag);
          const threshold = getThresholdRatio(index, currentDrag);
          const thresholdY = siblingRect.top + siblingRect.height * threshold;
          const draggedEdgeY = siblingVisualIndex > currentDrag.targetIndex
            ? draggedBottomY
            : draggedTopY;
          if (draggedEdgeY > thresholdY) nextTargetIndex += 1;
        }
      }

      if (nextTargetIndex > currentDrag.targetIndex + 1) nextTargetIndex = currentDrag.targetIndex + 1;
      if (nextTargetIndex < currentDrag.targetIndex - 1) nextTargetIndex = currentDrag.targetIndex - 1;

      let nextReverseLock = currentDrag.reverseLock;
      if (nextReverseLock) {
        const siblingRect = optionRefs.current[nextReverseLock.siblingId]?.getBoundingClientRect();
        if (siblingRect) {
          const shouldReturn = nextReverseLock.direction === "down"
            ? draggedBottomY >= siblingRect.top + siblingRect.height * OPTION_RETURN_THRESHOLD_UP
            : draggedTopY <= siblingRect.top + siblingRect.height * OPTION_RETURN_THRESHOLD_DOWN;
          const isUnlocked = nextReverseLock.direction === "down"
            ? draggedBottomY <= siblingRect.top + siblingRect.height * OPTION_THRESHOLD_MIN
            : draggedTopY >= siblingRect.top + siblingRect.height * OPTION_THRESHOLD_MAX;

          if (shouldReturn) {
            nextTargetIndex = nextReverseLock.direction === "down"
              ? currentDrag.targetIndex + 1
              : currentDrag.targetIndex - 1;
            nextReverseLock = null;
          } else if (isUnlocked && !nextInsertLock) {
            nextReverseLock = null;
          }
        }
      }

      if (nextReverseLock) {
        if (nextReverseLock.direction === "down" && nextTargetIndex > currentDrag.targetIndex) {
          nextTargetIndex = currentDrag.targetIndex;
        }
        if (nextReverseLock.direction === "up" && nextTargetIndex < currentDrag.targetIndex) {
          nextTargetIndex = currentDrag.targetIndex;
        }
      }

      if (!nextReverseLock && nextTargetIndex !== currentDrag.targetIndex) {
        const crossedVisualIndex = nextTargetIndex < currentDrag.targetIndex
          ? currentDrag.targetIndex - 1
          : currentDrag.targetIndex + 1;
        const crossedSiblingId = getOptionIdAtVisualIndex(crossedVisualIndex, currentDrag);
        if (crossedSiblingId) {
          const swapDirection = nextTargetIndex < currentDrag.targetIndex ? "down" : "up";
          nextReverseLock = { direction: swapDirection, siblingId: crossedSiblingId };
          nextInsertLock = { direction: swapDirection, siblingId: crossedSiblingId };
        }
      }

      setActiveDrag((current) => current
        ? { ...current, offsetY: nextOffset, targetIndex: nextTargetIndex, reverseLock: nextReverseLock, insertLock: nextInsertLock }
        : current
      );
    }

    function handlePointerUp() {
      setOptions((current) => {
        if (!currentDrag || currentDrag.startIndex === currentDrag.targetIndex) return current;
        const sourceIndex = current.findIndex((o) => o.id === currentDrag.id);
        if (sourceIndex < 0) return current;
        const next = [...current];
        const [moved] = next.splice(sourceIndex, 1);
        next.splice(currentDrag.targetIndex, 0, moved);
        return next;
      });
      setActiveDrag(null);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [activeDrag, options]);

  function startDrag(
    event: React.PointerEvent,
    optionId: string,
    index: number,
  ) {
    event.preventDefault();
    const rowElement = optionRefs.current[optionId];
    const listElement = optionsListRef.current;
    const rowRect = rowElement?.getBoundingClientRect();
    const listRect = listElement?.getBoundingClientRect();
    setActiveDrag({
      id: optionId,
      pointerOffsetY: rowRect ? event.clientY - rowRect.top : 0,
      startIndex: index,
      targetIndex: index,
      rowHeight: rowRect?.height ?? 0,
      startTop: rowRect && listRect ? rowRect.top - listRect.top : 0,
      offsetY: 0,
      reverseLock: null,
      insertLock: null,
    });
  }

  function getDragTransform(index: number): React.CSSProperties | undefined {
    if (!activeDrag) return undefined;
    if (activeDrag.id === options[index]?.id) {
      return { transform: `translateY(${activeDrag.offsetY}px)` };
    }
    if (
      activeDrag.targetIndex > activeDrag.startIndex &&
      index > activeDrag.startIndex &&
      index <= activeDrag.targetIndex
    ) {
      return { transform: `translateY(-${activeDrag.rowHeight + OPTION_GAP}px)` };
    }
    if (
      activeDrag.targetIndex < activeDrag.startIndex &&
      index >= activeDrag.targetIndex &&
      index < activeDrag.startIndex
    ) {
      return { transform: `translateY(${activeDrag.rowHeight + OPTION_GAP}px)` };
    }
    return undefined;
  }

  function getThresholdRatioForIndex(index: number) {
    return activeDrag ? getThresholdRatio(index, activeDrag) : null;
  }

  return {
    activeDrag,
    optionsListRef,
    optionRefs,
    startDrag,
    getDragTransform,
    getThresholdRatioForIndex,
  };
}
