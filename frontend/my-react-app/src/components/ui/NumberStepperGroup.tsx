import { useEffect, useState } from "react";
import { Button } from "./Button";
import "./NumberStepperGroup.css";
import { Input } from "./Input";

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
  variant?: "primary" | "secondary" | "ghost";
  allowInput?: boolean;
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
  variant = "primary",
  allowInput = false,
}: NumberStepperGroupProps) {
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});

  useEffect(() => {
    setDraftValues(
      Object.fromEntries(items.map((item) => [item.key, String(item.value)])),
    );
  }, [items]);

  function commitDraft(item: NumberStepperItem, rawValue: string) {
    const parsedValue = Number(rawValue);

    if (rawValue.trim() === "" || Number.isNaN(parsedValue)) {
      setDraftValues((current) => ({ ...current, [item.key]: String(item.value) }));
      return;
    }

    const nextValue = clamp(parsedValue, item.min, item.max);
    setDraftValues((current) => ({ ...current, [item.key]: String(nextValue) }));
    onChange(item.key, nextValue);
  }

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

            {allowInput ? (
              <Input
                className="ns-input"
                type="text"
                variant="ghost"
                size={size}
                inputMode="numeric"
                value={draftValues[item.key] ?? String(item.value)}
                disabled={item.disabled}
                aria-label={`${item.label} value`}
                onChange={(event) =>
                  setDraftValues((current) => ({
                    ...current,
                    [item.key]: event.target.value,
                  }))
                }
                onBlur={(event) => commitDraft(item, event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    commitDraft(item, event.currentTarget.value);
                    event.currentTarget.blur();
                  }

                  if (event.key === "Escape") {
                    setDraftValues((current) => ({
                      ...current,
                      [item.key]: String(item.value),
                    }));
                    event.currentTarget.blur();
                  }
                }}
              />
            ) : (
              <span className="ns-value">{item.value}</span>
            )}

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
