import {
  useEffect,
  useRef,
  type TextareaHTMLAttributes,
} from "react";
import {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  getTextareaShellClassName,
  controlBaseClass,
  type InputVariant,
} from "./formFieldStyles";
import {
  textareaMinHeights,
  textareaSizeClasses,
  type TextareaSize,
} from "./uiSizes";

interface LargeInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: TextareaSize;
  maxText?: number;
  showCount?: boolean;
  autoGrow?: boolean;
  maxAutoGrowHeight?: number;
}

const textareaBaseClass = [
  controlBaseClass,
  "block resize-none border-0 bg-transparent text-foreground",
].join(" ");

export function LargeInput({
  label,
  hint,
  error,
  id,
  className = "",
  variant = "secondary",
  size = "md",
  maxText,
  showCount = false,
  autoGrow = false,
  maxAutoGrowHeight,
  value,
  defaultValue,
  onInput,
  ...props
}: LargeInputProps) {
  const inputId = id ?? label?.toLowerCase().trim().replace(/\s+/g, "-");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const currentValue =
    typeof value === "string"
      ? value
      : typeof defaultValue === "string"
        ? defaultValue
        : "";

  const currentLength = currentValue.length;

  function resizeTextarea(textarea: HTMLTextAreaElement) {
    if (!autoGrow) return;

    const minHeight = textareaMinHeights[size];
    const maxHeight = maxAutoGrowHeight ?? textareaMinHeights[size] * 2;

    textarea.style.height = "0px";
    const nextHeight = Math.max(minHeight, textarea.scrollHeight);
    const clampedHeight = Math.min(nextHeight, maxHeight);

    textarea.style.height = `${clampedHeight}px`;
    textarea.style.overflowY = nextHeight > maxHeight ? "auto" : "hidden";
  }

  useEffect(() => {
    if (textareaRef.current) {
      resizeTextarea(textareaRef.current);
    }
  }, [value, defaultValue, size, autoGrow, maxAutoGrowHeight]);

  return (
    <div className={[formFieldClass, className].filter(Boolean).join(" ")}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <div
        className={getTextareaShellClassName({ variant, error: Boolean(error) })}
      >
        <textarea
          ref={textareaRef}
          id={inputId}
          maxLength={maxText}
          value={value}
          defaultValue={defaultValue}
          aria-invalid={error ? true : undefined}
          className={[
            textareaBaseClass,
            textareaSizeClasses[size],
            autoGrow ? "max-h-none overflow-y-hidden" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onInput={(event) => {
            resizeTextarea(event.currentTarget);
            onInput?.(event);
          }}
          {...props}
        />
      </div>

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : showCount && maxText ? (
        <div className="flex items-center justify-between gap-3">
          {hint ? <p className={formHintClass}>{hint}</p> : <span />}
          <p className={[formHintClass, "ml-auto whitespace-nowrap"].join(" ")}>
            {currentLength}/{maxText}
          </p>
        </div>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}