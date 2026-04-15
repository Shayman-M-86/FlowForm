import {
  useEffect,
  useRef,
  type TextareaHTMLAttributes,
} from "react";
import "./LargeInput.css";
/**
 * LargeInput props:
 * label, hint, error, size ("sm" | "md" | "lg"), maxText, showCount,
 * autoGrow, maxAutoGrowHeight, className, id,
 * plus all normal textarea props such as placeholder, value, defaultValue,
 * onChange, onInput, disabled, readOnly, required, name, rows, maxLength,
 * autoComplete, aria-*, data-*, and other standard textarea attributes.
 */
interface LargeInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  size?: "sm" | "md" | "lg";
  maxText?: number;
  showCount?: boolean;
  autoGrow?: boolean;
  maxAutoGrowHeight?: number;
}

const SIZE_MIN_HEIGHT: Record<NonNullable<LargeInputProps["size"]>, number> = {
  sm: 88,
  md: 120,
  lg: 168,
};

export function LargeInput({
  label,
  hint,
  error,
  id,
  className = "",
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
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
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

    const minHeight = SIZE_MIN_HEIGHT[size];
    const maxHeight = maxAutoGrowHeight ?? SIZE_MIN_HEIGHT[size] * 2;

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
    <div className={`input-field ${className}`}>
      {label && (
        <label className="input-label" htmlFor={inputId}>
          {label}
        </label>
      )}

      <div
        className={`large-input-shell ${error ? "large-input-shell--error" : ""}`}
      >
        <textarea
          ref={textareaRef}
          id={inputId}
          maxLength={maxText}
          value={value}
          defaultValue={defaultValue}
          className={`input-control large-input-control large-input-control--${size} ${
            autoGrow ? "large-input-control--autogrow" : ""
          }`}
          onInput={(event) => {
            resizeTextarea(event.currentTarget);
            onInput?.(event);
          }}
          {...props}
        />
      </div>

      {hint && !error && !showCount && <p className="input-hint">{hint}</p>}

      {!error && showCount && maxText && (
        <div className="large-input__meta">
          {hint ? <p className="input-hint">{hint}</p> : <span />}
          <p className="input-hint input-hint--count">
            {currentLength}/{maxText}
          </p>
        </div>
      )}

      {error && <p className="input-error">{error}</p>}
    </div>
    );
  }
