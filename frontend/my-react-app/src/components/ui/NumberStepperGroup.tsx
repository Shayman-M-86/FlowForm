import { Button } from "./Button";
import "./NumberStepperGroup.css";

interface NumberStepperItem {
  key: string;
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}

interface NumberStepperGroupProps {
  items: NumberStepperItem[];
  onChange: (key: string, value: number) => void;
  className?: string;
  ariaLabel?: string;
  size?: "xs" | "sm";
  pill?: boolean;
  variant?: "ghost" | "secondary";
}

function clamp(value: number, min?: number, max?: number) {
  if (min !== undefined && value < min) return min;
  if (max !== undefined && value > max) return max;
  return value;
}

export function NumberStepperGroup({
  items,
  onChange,
  className = "",
  ariaLabel = "Number selectors",
  size = "sm",
  pill = false,
  variant = "ghost",
}: NumberStepperGroupProps) {
  return (
    <div
      className={`ns-shell ns-shell--${size} ns-shell--${variant} ${pill ? "ns-shell--pill" : ""} number-stepper-group number-stepper-group--${size} ${className}`}
      role="group"
      aria-label={ariaLabel}
    >
      {items.map((item) => {
        const step = item.step ?? 1;
        const canDecrement = !item.disabled && (item.min === undefined || item.value > item.min);
        const canIncrement = !item.disabled && (item.max === undefined || item.value < item.max);

        return (
          <div key={item.key} className="number-stepper-group__segment">
            <span className="number-stepper-group__label">{item.label}</span>

            <Button
              type="button"
              variant="ghost"
              size={size}
              pill={pill}
              className="ns-button"
              disabled={!canDecrement}
              aria-label={`Decrease ${item.label}`}
              onClick={() =>
                onChange(item.key, clamp(item.value - step, item.min, item.max))
              }
            >
              −
            </Button>

            <span className="ns-value">{item.value}</span>

            <Button
              type="button"
              variant="ghost"
              size={size}
              pill={pill}
              className="ns-button"
              disabled={!canIncrement}
              aria-label={`Increase ${item.label}`}
              onClick={() =>
                onChange(item.key, clamp(item.value + step, item.min, item.max))
              }
            >
              +
            </Button>
          </div>
        );
      })}
    </div>
  );
}
