import { Button } from "./Button";
import "./NumberStepper.css";

interface NumberStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
  size?: "xs" | "sm";
  pill?: boolean;
  variant?: "ghost" | "secondary";
}

export function NumberStepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled = false,
  className = "",
  ariaLabel = "Number selector",
  size = "sm",
  pill = false,
  variant = "ghost",
}: NumberStepperProps) {
  const canDecrement = !disabled && (min === undefined || value > min);
  const canIncrement = !disabled && (max === undefined || value < max);

  function decrement() {
    if (!canDecrement) return;
    const next = value - step;
    onChange(min !== undefined ? Math.max(next, min) : next);
  }

  function increment() {
    if (!canIncrement) return;
    const next = value + step;
    onChange(max !== undefined ? Math.min(next, max) : next);
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
        disabled={!canDecrement}
        className="ns-button"
        aria-label="Decrease value"
      >
        −
      </Button>

      <span className="ns-value" aria-live="polite" aria-atomic="true">
        {value}
      </span>

      <Button
        type="button"
        variant="ghost"
        size={size}
        pill={pill}
        onClick={increment}
        disabled={!canIncrement}
        className="ns-button"
        aria-label="Increase value"
      >
        +
      </Button>
    </div>
  );
}
