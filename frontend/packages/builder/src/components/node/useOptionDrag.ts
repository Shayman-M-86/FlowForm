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
  startIndex: number;
  targetIndex: number;
  rowHeight: number;
  offsetY: number;
};

// Full internal drag state — kept in a ref so pointer-move updates don't trigger re-renders.
type DragState = {
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
  onReorder?: (reordered: T[]) => void,
) {
  const optionsListRef = useRef<HTMLDivElement | null>(null);
  const optionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  // Visual state — only offsetY + targetIndex needed to paint transforms.
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);
  // Full internal state — mutated in place during drag, never triggers re-renders.
  const dragStateRef = useRef<DragState | null>(null);
  // Keep refs to current options and onReorder so the stable effect closure can read them.
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const onReorderRef = useRef(onReorder);
  onReorderRef.current = onReorder;

  function getVisualIndex(index: number, drag: DragState) {
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

  function getThresholdRatio(index: number, drag: DragState) {
    const siblingVisualIndex = getVisualIndex(index, drag);
    return siblingVisualIndex > drag.targetIndex
      ? OPTION_INSERT_THRESHOLD_DOWN
      : OPTION_INSERT_THRESHOLD_UP;
  }

  function getOptionIdAtVisualIndex(visualIndex: number, drag: DragState) {
    const opts = optionsRef.current;
    for (let index = 0; index < opts.length; index += 1) {
      const option = opts[index];
      if (option.id === drag.id) continue;
      if (getVisualIndex(index, drag) === visualIndex) return option.id;
    }
    return null;
  }

  // Registered once — reads drag state from the ref, no re-subscription on each frame.
  useEffect(() => {
    function handlePointerMove(event: PointerEvent) {
      const drag = dragStateRef.current;
      const listElement = optionsListRef.current;
      if (!drag || !listElement) return;

      const opts = optionsRef.current;
      const listRect = listElement.getBoundingClientRect();
      const desiredTopInList = event.clientY - listRect.top - drag.pointerOffsetY;
      const maxTopInList = listRect.height - drag.rowHeight;
      const nextTopInList = Math.max(0, Math.min(maxTopInList, desiredTopInList));
      const nextOffset = nextTopInList - drag.startTop;
      const draggedTopY = listRect.top + nextTopInList;
      const draggedBottomY = draggedTopY + drag.rowHeight;

      let nextInsertLock = drag.insertLock;
      if (nextInsertLock) {
        const siblingRect = optionRefs.current[nextInsertLock.siblingId]?.getBoundingClientRect();
        if (siblingRect) {
          const isCleared = nextInsertLock.direction === "down"
            ? draggedBottomY <= siblingRect.top + siblingRect.height * OPTION_INSERT_LOCK_THRESHOLD_DOWN
            : draggedTopY >= siblingRect.top + siblingRect.height * OPTION_INSERT_LOCK_THRESHOLD_UP;
          if (isCleared) nextInsertLock = null;
        }
      }

      let nextTargetIndex = drag.targetIndex;
      if (!nextInsertLock) {
        nextTargetIndex = 0;
        for (let index = 0; index < opts.length; index += 1) {
          const option = opts[index];
          if (option.id === drag.id) continue;
          const siblingRect = optionRefs.current[option.id]?.getBoundingClientRect();
          if (!siblingRect) continue;
          const siblingVisualIndex = getVisualIndex(index, drag);
          const threshold = getThresholdRatio(index, drag);
          const thresholdY = siblingRect.top + siblingRect.height * threshold;
          const draggedEdgeY = siblingVisualIndex > drag.targetIndex ? draggedBottomY : draggedTopY;
          if (draggedEdgeY > thresholdY) nextTargetIndex += 1;
        }
      }

      if (nextTargetIndex > drag.targetIndex + 1) nextTargetIndex = drag.targetIndex + 1;
      if (nextTargetIndex < drag.targetIndex - 1) nextTargetIndex = drag.targetIndex - 1;

      let nextReverseLock = drag.reverseLock;
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
              ? drag.targetIndex + 1
              : drag.targetIndex - 1;
            nextReverseLock = null;
          } else if (isUnlocked && !nextInsertLock) {
            nextReverseLock = null;
          }
        }
      }

      if (nextReverseLock) {
        if (nextReverseLock.direction === "down" && nextTargetIndex > drag.targetIndex) {
          nextTargetIndex = drag.targetIndex;
        }
        if (nextReverseLock.direction === "up" && nextTargetIndex < drag.targetIndex) {
          nextTargetIndex = drag.targetIndex;
        }
      }

      if (!nextReverseLock && nextTargetIndex !== drag.targetIndex) {
        const crossedVisualIndex = nextTargetIndex < drag.targetIndex
          ? drag.targetIndex - 1
          : drag.targetIndex + 1;
        const crossedSiblingId = getOptionIdAtVisualIndex(crossedVisualIndex, drag);
        if (crossedSiblingId) {
          const swapDirection = nextTargetIndex < drag.targetIndex ? "down" : "up";
          nextReverseLock = { direction: swapDirection, siblingId: crossedSiblingId };
          nextInsertLock = { direction: swapDirection, siblingId: crossedSiblingId };
        }
      }

      // Mutate the ref in place — no re-render for lock/index bookkeeping.
      drag.offsetY = nextOffset;
      drag.targetIndex = nextTargetIndex;
      drag.reverseLock = nextReverseLock;
      drag.insertLock = nextInsertLock;

      // Only setState for values consumed by render (transforms).
      setActiveDrag((current) =>
        current
          ? { ...current, offsetY: nextOffset, targetIndex: nextTargetIndex }
          : current,
      );
    }

    function handlePointerUp() {
      const drag = dragStateRef.current;
      if (!drag) return;

      let reordered: T[] | null = null;
      if (drag.startIndex !== drag.targetIndex) {
        const current = optionsRef.current;
        const sourceIndex = current.findIndex((o) => o.id === drag.id);
        if (sourceIndex >= 0) {
          const next = [...current];
          const [moved] = next.splice(sourceIndex, 1);
          next.splice(drag.targetIndex, 0, moved);
          reordered = next;
          setOptions(next);
        }
      }
      if (reordered) onReorderRef.current?.(reordered);
      dragStateRef.current = null;
      setActiveDrag(null);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  // Empty deps — registered once, reads live data from refs.
  }, [setOptions]);

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
    const state: DragState = {
      id: optionId,
      pointerOffsetY: rowRect ? event.clientY - rowRect.top : 0,
      startIndex: index,
      targetIndex: index,
      rowHeight: rowRect?.height ?? 0,
      startTop: rowRect && listRect ? rowRect.top - listRect.top : 0,
      offsetY: 0,
      reverseLock: null,
      insertLock: null,
    };
    dragStateRef.current = state;
    setActiveDrag({
      id: optionId,
      startIndex: index,
      targetIndex: index,
      rowHeight: rowRect?.height ?? 0,
      offsetY: 0,
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
    const drag = dragStateRef.current;
    return drag ? getThresholdRatio(index, drag) : null;
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
