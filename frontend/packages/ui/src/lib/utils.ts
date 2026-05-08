import {
  useCallback,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
} from "react";
import { twMerge } from "tailwind-merge";

export type ClassValue = string | false | null | undefined;

export function cn(...values: ClassValue[]) {
  return twMerge(values.filter(Boolean).join(" "));
}

export const isBrowser = typeof window !== "undefined";

export function slugifyId(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function useFieldId(id?: string, label?: string) {
  const reactId = useId();

  return useMemo(() => {
    if (id) return id;
    if (label) return `${slugifyId(label)}-${reactId.replace(/:/g, "")}`;
    return reactId;
  }, [id, label, reactId]);
}

export function clampNumber(value: number, min?: number, max?: number) {
  if (min !== undefined && value < min) return min;
  if (max !== undefined && value > max) return max;
  return value;
}

export function parseNumericValue(rawValue: string) {
  const trimmed = rawValue.trim();
  if (!trimmed) return null;

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function resizeTextareaElement({
  textarea,
  minHeight = 0,
  maxHeight,
}: {
  textarea: HTMLTextAreaElement;
  minHeight?: number;
  maxHeight?: number;
}) {
  textarea.style.height = "auto";

  const nextHeight = Math.max(minHeight, textarea.scrollHeight);
  const clampedHeight = maxHeight ? Math.min(nextHeight, maxHeight) : nextHeight;

  textarea.style.height = `${clampedHeight}px`;
  textarea.style.overflowY = maxHeight && nextHeight > maxHeight ? "auto" : "hidden";
}

export function useAutoResizingTextarea({
  value,
  minHeight,
  maxHeight,
}: {
  value: string;
  minHeight?: number;
  maxHeight?: number;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  const resize = useCallback(
    (textarea: HTMLTextAreaElement) => {
      resizeTextareaElement({ textarea, minHeight, maxHeight });
    },
    [minHeight, maxHeight],
  );

  useLayoutEffect(() => {
    if (ref.current) resize(ref.current);
  }, [resize, value]);

  return { ref, resize };
}
