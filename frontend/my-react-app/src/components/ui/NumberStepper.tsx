import { useEffect, useState } from "react";
import { Button } from "./Button";
import { Input } from "./Input";
import {
  stepperShellClass,
  stepperButtonClass,
  stepperValueClass,
  stepperInputClass,
  type StepperSize,
  type StepperVariant,
} from "./stepperStyles";

interface NumberStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  canDecrement?: boolean;
  canIncrement?: boolean;
  onDecrement?: () => void;
  onIncrement?: () => void;
  className?: string;
  ariaLabel?: string;
  size?: StepperSize;
  pill?: boolean;
  variant?: StepperVariant;
  allowInput?: boolean;
}

function clamp(value: number, min?: number, max?: number) {
  if (min !== undefined && value < min) return min;
  if (max !== undefined && value > max) return max;
  return value;
}

export function NumberStepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled = false,
  canDecrement,
  canIncrement,
  onDecrement,
  onIncrement,
  className = "",
  ariaLabel = "Number selector",
  size = "sm",
  pill = false,
  variant = "primary",
  allowInput = false,
}: NumberStepperProps) {
  const [draftValue, setDraftValue] = useState(String(value));

  useEffect(() => {
    setDraftValue(String(value));
  }, [value]);

  const canDecrementValue =
    !disabled && (canDecrement ?? (min === undefined || value > min));
  const canIncrementValue =
    !disabled && (canIncrement ?? (max === undefined || value < max));

  function decrement() {
    if (!canDecrementValue) return;
    if (onDecrement) {
      onDecrement();
      return;
    }
    const next = value - step;
    onChange(clamp(next, min, max));
  }

  function increment() {
    if (!canIncrementValue) return;
    if (onIncrement) {
      onIncrement();
      return;
    }
    const next = value + step;
    onChange(clamp(next, min, max));
  }

  function commitDraft(rawValue: string) {
    const parsedValue = Number(rawValue);

    if (rawValue.trim() === "" || Number.isNaN(parsedValue)) {
      setDraftValue(String(value));
      return;
    }

    const nextValue = clamp(parsedValue, min, max);
    setDraftValue(String(nextValue));
    onChange(nextValue);
  }

  const shellPadding = size === "xs" ? "gap-0.5 p-0.5" : "gap-1 p-1";

  return (
    <div
      className={[stepperShellClass({ size, variant, pill }), shellPadding, className]
        .filter(Boolean)
        .join(" ")}
      role="group"
      aria-label={ariaLabel}
    >
      <Button
        type="button"
        variant="ghost"
        size={size}
        pill={pill}
        onClick={decrement}
        disabled={!canDecrementValue}
        className={stepperButtonClass({ size, variant, pill })}
        aria-label="Decrease value"
      >
        −
      </Button>

      {allowInput ? (
        <Input
          className={stepperInputClass(size)}
          type="text"
          variant="ghost"
          size={size}
          inputMode="numeric"
          value={draftValue}
          disabled={disabled}
          aria-label="Value"
          onChange={(event) => setDraftValue(event.target.value)}
          onBlur={(event) => commitDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              commitDraft(event.currentTarget.value);
              event.currentTarget.blur();
            }

            if (event.key === "Escape") {
              setDraftValue(String(value));
              event.currentTarget.blur();
            }
          }}
        />
      ) : (
        <span className={stepperValueClass(size)} aria-live="polite" aria-atomic="true">
          {value}
        </span>
      )}

      <Button
        type="button"
        variant="ghost"
        size={size}
        pill={pill}
        onClick={increment}
        disabled={!canIncrementValue}
        className={stepperButtonClass({ size, variant, pill })}
        aria-label="Increase value"
      >
        +
      </Button>
    </div>
  );
}
