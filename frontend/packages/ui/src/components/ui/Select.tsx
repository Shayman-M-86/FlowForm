import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { cn, useFieldId } from "../../lib/utils";
import { controlSizeClasses, type ControlSize } from "../../lib/sizes";
import {
  controlBaseClass,
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  getSurfaceClassName,
  type InputVariant,
} from "../../lib/formFieldStyles";

interface SelectOption {
  value: string;
  label: string;
}

export type SelectChangeEvent = {
  target: { value: string; name?: string };
  currentTarget: { value: string; name?: string };
};

interface SelectProps {
  label?: string;
  options: SelectOption[];
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: ControlSize;
  pill?: boolean;
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  onChange?: (event: SelectChangeEvent) => void;
  onValueChange?: (value: string) => void;
  id?: string;
  name?: string;
  className?: string;
  disabled?: boolean;
  required?: boolean;
  "aria-label"?: string;
  "aria-describedby"?: string;
}

const chevronClass = "pr-10";

export function Select({
  label,
  options,
  hint,
  error,
  id,
  name,
  className = "",
  variant = "secondary",
  size = "md",
  pill = false,
  disabled,
  value,
  defaultValue,
  placeholder,
  onChange,
  onValueChange,
  required,
  "aria-label": ariaLabel,
  "aria-describedby": ariaDescribedBy,
}: SelectProps) {
  const selectId = useFieldId(id, label);
  const listboxId = `${selectId}-listbox`;

  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState<string>(defaultValue ?? "");
  const currentValue = isControlled ? value ?? "" : internalValue;

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(() => {
    const index = options.findIndex((option) => option.value === currentValue);
    return index >= 0 ? index : 0;
  });

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);

  const selectedOption = useMemo(
    () => options.find((option) => option.value === currentValue) ?? null,
    [currentValue, options],
  );

  const emitChange = useCallback(
    (nextValue: string) => {
      if (!isControlled) setInternalValue(nextValue);
      onValueChange?.(nextValue);

      if (onChange) {
        const target = { value: nextValue, name };
        onChange({ target, currentTarget: target });
      }
    },
    [isControlled, name, onChange, onValueChange],
  );

  const closeAndFocus = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  const commit = useCallback(
    (index: number) => {
      const option = options[index];
      if (!option) return;

      emitChange(option.value);
      closeAndFocus();
    },
    [closeAndFocus, emitChange, options],
  );

  useEffect(() => {
    if (!open) return;

    function onDocumentMouseDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }

    document.addEventListener("mousedown", onDocumentMouseDown);
    return () => document.removeEventListener("mousedown", onDocumentMouseDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;

    const selectedIndex = options.findIndex((option) => option.value === currentValue);
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
  }, [currentValue, open, options]);

  useEffect(() => {
    if (!open || !listRef.current) return;

    const activeOption = listRef.current.querySelector<HTMLLIElement>(
      `[data-index="${activeIndex}"]`,
    );
    activeOption?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  function onTriggerKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (disabled) return;

    if (!open) {
      if (
        event.key === "ArrowDown" ||
        event.key === "ArrowUp" ||
        event.key === "Enter" ||
        event.key === " "
      ) {
        event.preventDefault();
        setOpen(true);
      }
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeAndFocus();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((currentIndex) => Math.min(options.length - 1, currentIndex + 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((currentIndex) => Math.max(0, currentIndex - 1));
    } else if (event.key === "Home") {
      event.preventDefault();
      setActiveIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActiveIndex(options.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      commit(activeIndex);
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  const triggerClassName = cn(
    controlBaseClass,
    controlSizeClasses[size],
    getSurfaceClassName({ variant, focusMode: "focus", pill, error: Boolean(error) }),
    chevronClass,
    "relative flex cursor-pointer items-center text-left",
    !selectedOption && "text-muted-foreground",
  );

  return (
    <div ref={rootRef} className={cn(formFieldClass, "relative", className)}>
      {label ? (
        <label className={formLabelClass} htmlFor={selectId}>
          {label}
        </label>
      ) : null}

      {name ? <input type="hidden" name={name} value={currentValue} required={required} /> : null}

      <button
        ref={triggerRef}
        type="button"
        id={selectId}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-invalid={error ? true : undefined}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        disabled={disabled}
        className={triggerClassName}
        onClick={() => !disabled && setOpen((currentOpen) => !currentOpen)}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="truncate">{selectedOption?.label ?? placeholder ?? " "}</span>
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute right-3.5 top-1/2 h-2 w-3 -translate-y-1/2 text-muted-foreground"
          viewBox="0 0 12 8"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="1,1.5 6,6.5 11,1.5" />
        </svg>
      </button>

      {open ? (
        <ul
          ref={listRef}
          id={listboxId}
          role="listbox"
          tabIndex={-1}
          aria-activedescendant={
            options[activeIndex] ? `${listboxId}-opt-${activeIndex}` : undefined
          }
          className="ui-popover-panel absolute left-0 right-0 top-full z-50 mt-1.5 max-h-64 overflow-y-auto p-1"
        >
          {options.map((option, index) => {
            const isSelected = option.value === currentValue;
            const isActive = index === activeIndex;

            return (
              <li
                key={option.value}
                id={`${listboxId}-opt-${index}`}
                data-index={index}
                role="option"
                aria-selected={isSelected}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => {
                  event.preventDefault();
                  commit(index);
                }}
                className={cn(
                  "cursor-pointer rounded-sm px-3 py-1.5 text-sm transition-colors",
                  isActive && "bg-muted",
                  isSelected ? "font-medium text-foreground" : "text-foreground",
                )}
              >
                {option.label}
              </li>
            );
          })}
          {options.length === 0 ? (
            <li className="px-3 py-1.5 text-sm text-muted-foreground">No options</li>
          ) : null}
        </ul>
      ) : null}

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}
