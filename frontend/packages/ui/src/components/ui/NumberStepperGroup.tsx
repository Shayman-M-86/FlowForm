import { useEffect, useState } from "react";
import { cn, clampNumber, parseNumericValue } from "../../lib/utils.ts";
import {
  stepperShellClass,
  stepperButtonClass,
  stepperValueClass,
  stepperInputClass,
  type StepperSize,
  type StepperVariant,
} from "../../lib/stepperStyles.ts";
import { Button } from "./Button.tsx";
import { Input } from "./Input.tsx";

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
    setDraftValues(Object.fromEntries(items.map((item) => [item.key, String(item.value)])));
  }, [items]);

  function commitDraft(item: NumberStepperItem, rawValue: string) {
    const parsedValue = parseNumericValue(rawValue);

    if (parsedValue === null) {
      setDraftValues((current) => ({ ...current, [item.key]: String(item.value) }));
      return;
    }

    const nextValue = clampNumber(parsedValue, item.min, item.max);
    setDraftValues((current) => ({ ...current, [item.key]: String(nextValue) }));
    onChange(item.key, nextValue);
  }

  const segmentBase = "ui-stepper-segment";
  const segmentSize = size === "xs" ? "min-h-[34px] px-[5px]" : "min-h-10 pl-2.5 pr-1.5";
  const segmentBorderOverride = variant === "ghost" ? "[&+&]:border-l-transparent" : "";
  const labelSize = size === "xs" ? "text-[0.82rem]" : "text-[0.86rem]";

  return (
    <div
      className={cn(stepperShellClass({ size, variant, pill }), "overflow-hidden", className)}
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
            className={cn(segmentBase, segmentSize, segmentBorderOverride)}
          >
            <span className={cn("whitespace-nowrap pr-1 text-muted-foreground", labelSize)}>
              {item.label}
            </span>

            <Button
              type="button"
              variant="ghost"
              size={size}
              pill={pill}
              className={cn(stepperButtonClass({ size, variant, pill }), "min-w-6")}
              disabled={!canDecrement}
              aria-label={`Decrease ${item.label}`}
              onClick={() => onChange(item.key, clampNumber(item.value - step, item.min, item.max))}
            >
              −
            </Button>

            {allowInput ? (
              <Input
                className={cn(stepperInputClass(size), "min-w-8")}
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
              className={cn(stepperButtonClass({ size, variant, pill }), "min-w-6")}
              disabled={!canIncrement}
              aria-label={`Increase ${item.label}`}
              onClick={() => onChange(item.key, clampNumber(item.value + step, item.min, item.max))}
            >
              +
            </Button>
          </div>
        );
      })}
    </div>
  );
}
