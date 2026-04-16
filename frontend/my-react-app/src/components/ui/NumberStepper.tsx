import { useEffect, useState } from "react";
import { Button } from "./Button";
import { Input } from "./Input";
import "./NumberStepper.css";

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
  size?: "xs" | "sm";
  pill?: boolean;
  variant?: "primary" | "secondary" | "ghost";
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

  return (
    <div
      className={`ns-shell ns-shell--${size} ns-shell--${variant} ${pill ? "ns-shell--pill" : ""} number-stepper number-stepper--${size} ${className}`}
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
        className="ns-button"
        aria-label="Decrease value"
      >
        −
      </Button>

      {allowInput ? (
        <Input
          className="ns-input"
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
        <span className="ns-value" aria-live="polite" aria-atomic="true">
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
        className="ns-button"
        aria-label="Increase value"
      >
        +
      </Button>
    </div>
  );
}
