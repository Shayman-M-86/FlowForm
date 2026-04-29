import {
  useEffect,
  useRef,
  type TextareaHTMLAttributes,
} from "react";
import { cn } from "../../lib/utils";
import {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  getTextareaShellClassName,
  controlBaseClass,
  type InputVariant,
  textareaBodySizeClasses,
  textareaSizeClasses,
  type TextareaSize,
} from "../../index.optimized";

interface LargeInputProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: TextareaSize;
  maxText?: number;
  showCount?: boolean;
  autoGrow?: boolean;
  maxAutoGrowHeight?: number;
  shellClassName?: string;
}

const textareaBaseClass = cn(
  controlBaseClass,
  "block resize-none border-0 bg-transparent text-foreground"
);

function getTextareaMinHeight(
  textarea: HTMLTextAreaElement,
  rows: number,
): number {
  const styles = window.getComputedStyle(textarea);

  const lineHeight = parseFloat(styles.lineHeight) || 0;
  const paddingTop = parseFloat(styles.paddingTop) || 0;
  const paddingBottom = parseFloat(styles.paddingBottom) || 0;
  const borderTop = parseFloat(styles.borderTopWidth) || 0;
  const borderBottom = parseFloat(styles.borderBottomWidth) || 0;

  return (
    lineHeight * rows +
    paddingTop +
    paddingBottom +
    borderTop +
    borderBottom
  );
}

function resizeTextarea(params: {
  textarea: HTMLTextAreaElement;
  autoGrow: boolean;
  rows: number;
  maxAutoGrowHeight?: number;
}) {
  const { textarea, autoGrow, rows, maxAutoGrowHeight } = params;

  if (!autoGrow) return;

  const minHeight = getTextareaMinHeight(textarea, rows);
  const maxHeight = maxAutoGrowHeight ?? minHeight * 2;

  textarea.style.minHeight = `${minHeight}px`;
  textarea.style.height = "0px";

  const nextHeight = Math.max(minHeight, textarea.scrollHeight);
  const clampedHeight = Math.min(nextHeight, maxHeight);

  textarea.style.height = `${clampedHeight}px`;
  textarea.style.overflowY = nextHeight > maxHeight ? "auto" : "hidden";
}

export function LargeInput({
  label,
  hint,
  error,
  id,
  className,
  variant = "secondary",
  size = "md",
  maxText,
  showCount = false,
  autoGrow = false,
  maxAutoGrowHeight,
  shellClassName,
  value,
  defaultValue,
  rows = 1,
  onInput,
  ...props
}: LargeInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const inputId = id ?? label?.toLowerCase().trim().replace(/\s+/g, "-");

  const currentValue =
    typeof value === "string"
      ? value
      : typeof defaultValue === "string"
        ? defaultValue
        : "";

  const currentLength = currentValue.length;
  const showCounter = showCount && typeof maxText === "number";

  useEffect(() => {
    if (!textareaRef.current) return;

    resizeTextarea({
      textarea: textareaRef.current,
      autoGrow,
      rows,
      maxAutoGrowHeight,
    });
  }, [autoGrow, rows, maxAutoGrowHeight, value, defaultValue, size]);

  return (
    <div className={cn(formFieldClass, className)}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <div
        className={cn(
          getTextareaShellClassName({ variant, error: Boolean(error) }),
          shellClassName,
        )}
      >
        <textarea
          ref={textareaRef}
          id={inputId}
          rows={rows}
          maxLength={maxText}
          value={value}
          defaultValue={defaultValue}
          aria-invalid={error ? true : undefined}
          className={cn(
            textareaBaseClass,
            autoGrow ? textareaBodySizeClasses[size] : textareaSizeClasses[size],
            autoGrow && "max-h-none overflow-y-hidden",
          )}
          onInput={(event) => {
            resizeTextarea({
              textarea: event.currentTarget,
              autoGrow,
              rows,
              maxAutoGrowHeight,
            });
            onInput?.(event);
          }}
          {...props}
        />
      </div>

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : showCounter ? (
        <div className="flex items-center justify-between gap-3">
          {hint ? <p className={formHintClass}>{hint}</p> : <span />}
          <p className={cn(formHintClass, "ml-auto whitespace-nowrap")}>
            {currentLength}/{maxText}
          </p>
        </div>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}