import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import {
  type ControlSize,
  controlSizeClasses,
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  controlBaseClass,
  getSurfaceClassName,
  type InputVariant,
} from "../../index.optimized";

interface SelectOption {
  value: string;
  label: string;
}

type SelectChangeEvent = {
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

const chevronClass =
  "bg-no-repeat bg-[position:right_0.875rem_center] bg-[length:0.7rem_auto] " +
  "bg-[image:url(\"data:image/svg+xml;utf8,<svg_xmlns='http://www.w3.org/2000/svg'_width='12'_height='8'_viewBox='0_0_12_8'_fill='none'_stroke='%23737373'_stroke-width='1.75'_stroke-linecap='round'_stroke-linejoin='round'><polyline_points='1,1.5_6,6.5_11,1.5'/></svg>\")]";

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
  const reactId = useId();
  const selectId = id ?? label?.toLowerCase().trim().replace(/\s+/g, "-") ?? reactId;
  const listboxId = `${selectId}-listbox`;

  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState<string>(
    defaultValue ?? "",
  );
  const currentValue = isControlled ? (value as string) : internalValue;

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(() => {
    const i = options.findIndex((o) => o.value === currentValue);
    return i >= 0 ? i : 0;
  });

  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);

  const selectedOption = useMemo(
    () => options.find((o) => o.value === currentValue) ?? null,
    [options, currentValue],
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
      const opt = options[index];
      if (!opt) return;
      emitChange(opt.value);
      closeAndFocus();
    },
    [options, emitChange, closeAndFocus],
  );

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const selectedIdx = options.findIndex((o) => o.value === currentValue);
    setActiveIndex(selectedIdx >= 0 ? selectedIdx : 0);
  }, [open, options, currentValue]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLLIElement>(
      `[data-index="${activeIndex}"]`,
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  function onTriggerKeyDown(e: KeyboardEvent<HTMLButtonElement>) {
    if (disabled) return;
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      closeAndFocus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(options.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(0, i - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      setActiveIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActiveIndex(options.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      commit(activeIndex);
    } else if (e.key === "Tab") {
      setOpen(false);
    }
  }

  const triggerClassName = [
    controlBaseClass,
    controlSizeClasses[size],
    getSurfaceClassName({ variant, focusMode: "focus", pill, error: Boolean(error) }),
    chevronClass,
    "cursor-pointer pr-10 text-left flex items-center",
    !selectedOption ? "text-muted-foreground" : "text-foreground",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={rootRef}
      className={[formFieldClass, "relative", className].filter(Boolean).join(" ")}
    >
      {label ? (
        <label className={formLabelClass} htmlFor={selectId}>
          {label}
        </label>
      ) : null}

      {name ? (
        <input
          type="hidden"
          name={name}
          value={currentValue}
          required={required}
        />
      ) : null}

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
        onClick={() => !disabled && setOpen((o) => !o)}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="truncate">
          {selectedOption?.label ?? placeholder ?? "\u00A0"}
        </span>
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
          className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-64 overflow-y-auto rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-lg"
        >
          {options.map((opt, index) => {
            const isSelected = opt.value === currentValue;
            const isActive = index === activeIndex;
            return (
              <li
                key={opt.value}
                id={`${listboxId}-opt-${index}`}
                data-index={index}
                role="option"
                aria-selected={isSelected}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(index);
                }}
                className={[
                  "cursor-pointer rounded-sm px-3 py-1.5 text-sm transition-colors",
                  isActive ? "bg-muted" : "",
                  isSelected ? "font-medium text-foreground" : "text-foreground",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {opt.label}
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

export type { SelectChangeEvent };
