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
} from "../../index.optimized";

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

  const segmentBase =
    "inline-flex items-center gap-0.5 [&+&]:border-l [&+&]:border-border";
  const segmentSize =
    size === "xs"
      ? "min-h-[34px] px-[5px]"
      : "min-h-10 pl-2.5 pr-1.5";
  const segmentBorderOverride =
    variant === "ghost" ? "[&+&]:border-l-transparent" : "";

  const labelBase = "whitespace-nowrap pr-1 text-muted-foreground";
  const labelSize = size === "xs" ? "text-[0.82rem]" : "text-[0.86rem]";

  return (
    <div
      className={[
        stepperShellClass({ size, variant, pill }),
        "overflow-hidden",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      role="group"
      aria-label={ariaLabel}
    >
      {items.map((item) => {
        const step = item.step ?? 1;
        const canDecrement = !item.disabled && (item.min === undefined || item.value > item.min);
        const canIncrement = !item.disabled && (item.max === undefined || item.value < item.max);

        return (
          <div
            key={item.key}
            className={[segmentBase, segmentSize, segmentBorderOverride]
              .filter(Boolean)
              .join(" ")}
          >
            <span className={[labelBase, labelSize].join(" ")}>{item.label}</span>

            <Button
              type="button"
              variant="ghost"
              size={size}
              pill={pill}
              className={[stepperButtonClass({ size, variant, pill }), "min-w-6"].join(
                " ",
              )}
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
                className={[stepperInputClass(size), "min-w-8"].join(" ")}
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
              <span className={stepperValueClass(size)}>{item.value}</span>
            )}

            <Button
              type="button"
              variant="ghost"
              size={size}
              pill={pill}
              className={[stepperButtonClass({ size, variant, pill }), "min-w-6"].join(
                " ",
              )}
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
