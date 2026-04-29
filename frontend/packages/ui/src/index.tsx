import * as React from "react";
import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";
import { createPortal } from "react-dom";

type ClassValue = string | false | null | undefined;

function cn(...values: ClassValue[]) {
  return values.filter(Boolean).join(" ");
}

const isBrowser = typeof window !== "undefined";

function slugifyId(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function useFieldId(id?: string, label?: string) {
  const reactId = useId();

  return useMemo(() => {
    if (id) return id;
    if (label) return `${slugifyId(label)}-${reactId.replace(/:/g, "")}`;
    return reactId;
  }, [id, label, reactId]);
}

function clampNumber(value: number, min?: number, max?: number) {
  if (min !== undefined && value < min) return min;
  if (max !== undefined && value > max) return max;
  return value;
}

function parseNumericValue(rawValue: string) {
  const trimmed = rawValue.trim();
  if (!trimmed) return null;

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function resizeTextareaElement({
  textarea,
  minHeight = 0,
  maxHeight,
}: {
  textarea: HTMLTextAreaElement;
  minHeight?: number;
  maxHeight?: number;
}) {
  textarea.style.height = "auto";

  const nextHeight = Math.max(minHeight, textarea.scrollHeight);
  const clampedHeight = maxHeight ? Math.min(nextHeight, maxHeight) : nextHeight;

  textarea.style.height = `${clampedHeight}px`;
  textarea.style.overflowY = maxHeight && nextHeight > maxHeight ? "auto" : "hidden";
}

function useAutoResizingTextarea({
  value,
  minHeight,
  maxHeight,
}: {
  value: string;
  minHeight?: number;
  maxHeight?: number;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  const resize = useCallback(
    (textarea: HTMLTextAreaElement) => {
      resizeTextareaElement({ textarea, minHeight, maxHeight });
    },
    [minHeight, maxHeight],
  );

  useLayoutEffect(() => {
    if (ref.current) resize(ref.current);
  }, [resize, value]);

  return { ref, resize };
}

/* =========================
   ThemeContext.tsx
========================= */

export type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "flowform.theme";

function isTheme(value: unknown): value is Theme {
  return value === "light" || value === "dark";
}

function resolveTheme(): Theme {
  if (!isBrowser) return "light";

  try {
    const storedTheme = window.localStorage.getItem(STORAGE_KEY);
    if (isTheme(storedTheme)) return storedTheme;
  } catch {
    // Ignore storage access failures.
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  if (!isBrowser) return;

  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => resolveTheme());

  useEffect(() => {
    applyTheme(theme);

    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Ignore storage access failures.
    }
  }, [theme]);

  useEffect(() => {
    if (!isBrowser) return;

    const handleStorage = (event: StorageEvent) => {
      if (event.key && event.key !== STORAGE_KEY) return;
      if (isTheme(event.newValue)) setTheme(event.newValue);
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }, []);

  const value = useMemo(
    () => ({ theme, toggleTheme }),
    [theme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}

/* =========================
   uiSizes.ts
========================= */

export type ControlSize = "xxs" | "xs" | "sm" | "md" | "lg" | "xl";
export type TextareaSize = "sm" | "md" | "lg";

export const controlSizeClasses: Record<ControlSize, string> = {
  xxs: "min-h-[26px] px-2 text-[0.75rem] leading-none",
  xs: "min-h-[30px] px-2.5 text-[0.8rem] leading-none",
  sm: "min-h-[34px] px-3 text-[0.86rem] leading-[1.2]",
  md: "min-h-10 px-4 text-sm leading-normal",
  lg: "min-h-11 px-5 text-base leading-normal",
  xl: "min-h-12 px-6 text-[1.05rem] leading-normal",
};

export const badgeSizeClasses: Record<ControlSize, string> = {
  xxs: "px-1.5 py-0.5 text-[0.65rem] leading-none",
  xs: "px-2 py-1 text-[0.72rem] leading-none",
  sm: "px-2.5 py-1 text-[0.8rem] leading-none",
  md: "px-3 py-1.5 text-xs leading-none",
  lg: "px-3.5 py-2 text-sm leading-none",
  xl: "px-4 py-2.5 text-sm leading-none",
};

export const cardPaddingClasses: Record<ControlSize, string> = {
  xxs: "p-1",
  xs: "p-2",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
  xl: "p-8",
};

export const stackGapClasses: Record<ControlSize, string> = {
  xxs: "gap-1",
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-4",
  lg: "gap-6",
  xl: "gap-8",
};

export const textareaBodySizeClasses: Record<TextareaSize, string> = {
  sm: "px-3 py-2 text-[0.86rem] leading-6",
  md: "px-4 py-3 text-sm leading-6",
  lg: "px-4 py-3 text-base leading-7",
};

export const textareaSizeClasses: Record<TextareaSize, string> = {
  sm: `min-h-[88px] max-h-[88px] ${textareaBodySizeClasses.sm}`,
  md: `min-h-[120px] max-h-[120px] ${textareaBodySizeClasses.md}`,
  lg: `min-h-[168px] max-h-[168px] ${textareaBodySizeClasses.lg}`,
};

export const textareaMinHeights: Record<TextareaSize, number> = {
  sm: 88,
  md: 120,
  lg: 168,
};

const layoutGapClasses = {
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-5",
  lg: "gap-6",
  xl: "gap-8",
} as const;

type LayoutGap = keyof typeof layoutGapClasses;

/* =========================
   formFieldStyles.ts
========================= */

const inputMinWidthClasses: Record<ControlSize, string> = {
  xxs: "min-w-16",
  xs: "min-w-20",
  sm: "min-w-24",
  md: "min-w-32",
  lg: "min-w-40",
  xl: "min-w-48",
};

export type InputVariant = "secondary" | "ghost" | "quiet";
export type FocusMode = "focus" | "focus-within";

export const formFieldClass = "ui-field";
export const formLabelClass = "ui-label";
export const formHintClass = "ui-hint";
export const formErrorClass = "ui-error";

export const controlBaseClass = "ui-control-base";

const surfaceRoundedClass = "ui-surface";

const variantSurface: Record<InputVariant, string> = {
  secondary: "border border-border bg-input",
  ghost: "border border-transparent bg-transparent",
  quiet: "border border-border bg-transparent",
};

const variantInteractive: Record<InputVariant, Record<FocusMode, string>> = {
  secondary: {
    focus: "focus:border-accent focus:bg-secondary",
    "focus-within": "focus-within:border-accent focus-within:bg-secondary",
  },
  ghost: {
    focus: "focus:border-transparent focus:bg-muted",
    "focus-within": "focus-within:border-transparent focus-within:bg-muted",
  },
  quiet: {
    focus:
      "focus:border-ring/80 focus:bg-muted read-only:border-border read-only:bg-transparent read-only:text-foreground",
    "focus-within":
      "focus-within:border-ring/80 focus-within:bg-muted read-only:border-border read-only:bg-transparent read-only:text-foreground",
  },
};

export function getSurfaceClassName({
  variant,
  focusMode,
  pill = false,
  error = false,
  extra = "",
}: {
  variant: InputVariant;
  focusMode: FocusMode;
  pill?: boolean;
  error?: boolean;
  extra?: string;
}) {
  return cn(
    surfaceRoundedClass,
    variantSurface[variant],
    variantInteractive[variant][focusMode],
    pill ? "rounded-full" : "rounded-sm",
    error && "border-destructive/50",
    extra,
  );
}

export function getInputControlClassName({
  size,
  variant,
  pill,
  error,
  className = "",
}: {
  size: ControlSize;
  variant: InputVariant;
  pill: boolean;
  error: boolean;
  className?: string;
}) {
  return cn(
    controlBaseClass,
    controlSizeClasses[size],
    inputMinWidthClasses[size],
    getSurfaceClassName({ variant, focusMode: "focus", pill, error }),
    className,
  );
}

export function getTextareaShellClassName({
  variant,
  error,
}: {
  variant: InputVariant;
  error: boolean;
}) {
  return getSurfaceClassName({
    variant,
    focusMode: "focus-within",
    error,
    extra: "overflow-hidden",
  });
}

/* =========================
   stepperStyles.ts
========================= */

export type StepperSize = "xs" | "sm";
export type StepperVariant = "primary" | "secondary" | "ghost";

const shellBase = "inline-flex w-fit items-center self-start border transition-colors";

const shellVariant: Record<StepperVariant, string> = {
  primary: "border-primary/60 bg-primary/10",
  secondary: "border-secondary/10 bg-input",
  ghost: "border-transparent bg-transparent",
};

function shellRadius(size: StepperSize, pill: boolean) {
  if (pill) return "rounded-full";
  return size === "xs" ? "rounded-md" : "rounded-sm";
}

export function stepperShellClass({
  size,
  variant,
  pill,
}: {
  size: StepperSize;
  variant: StepperVariant;
  pill: boolean;
}) {
  return cn(shellBase, shellVariant[variant], shellRadius(size, pill));
}

const buttonBase = "border-transparent bg-transparent p-0 shadow-none hover:bg-muted";
const valueBase = "select-none text-center font-medium tabular-nums text-foreground";

function buttonMinWidth(size: StepperSize) {
  return size === "xs" ? "min-w-[22px]" : "min-w-[28px]";
}

function buttonRadius(pill: boolean) {
  return pill ? "rounded-full" : "rounded-md";
}

function buttonColor(variant: StepperVariant) {
  return variant === "ghost"
    ? "text-muted-foreground hover:text-foreground"
    : "text-foreground";
}

export function stepperButtonClass({
  size,
  variant,
  pill,
}: {
  size: StepperSize;
  variant: StepperVariant;
  pill: boolean;
}) {
  return cn(
    buttonBase,
    buttonMinWidth(size),
    buttonRadius(pill),
    buttonColor(variant),
  );
}

export function stepperValueClass(size: StepperSize) {
  return cn(valueBase, size === "xs" ? "min-w-[22px] text-[0.82rem]" : "min-w-[28px]");
}

export function stepperInputClass(size: StepperSize) {
  return cn("w-[42px] text-center tabular-nums", size === "xs" && "text-[0.82rem]");
}

/* =========================
   Button.tsx
========================= */

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonBorderStyle = "solid" | "dotted";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: ButtonBorderStyle;
  children: ReactNode;
}

const buttonBaseClasses = "cursor-pointer border";
const activeClasses = "active:scale-95 active:opacity-80";
const disabledClasses = "disabled:cursor-not-allowed disabled:opacity-50";

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-transparent bg-primary font-semibold text-primary-foreground shadow-sm hover:bg-accent",
  secondary:
    "border-border/80 bg-input font-semibold text-secondary-foreground shadow-sm hover:border-ring/80 hover:bg-hover-highlight",
  danger:
    "border-destructive/30 bg-transparent font-semibold text-destructive shadow-sm hover:bg-destructive/10",
  ghost:
    "border-transparent bg-transparent font-semibold text-accent-foreground shadow-none hover:border-ring/20 hover:bg-muted",
};

const borderStyleClasses: Record<ButtonBorderStyle, string> = {
  solid: "",
  dotted: "border-2 border-dashed",
};

export function Button({
  variant = "secondary",
  size = "md",
  pill = false,
  borderStyle = "solid",
  className = "",
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled}
      className={cn(
        buttonBaseClasses,
        !disabled && activeClasses,
        buttonVariantClasses[variant],
        pill ? "rounded-full" : "rounded-sm",
        borderStyleClasses[borderStyle],
        controlSizeClasses[size],
        disabled && disabledClasses,
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/* =========================
   Card.tsx
========================= */

type CardSize = "xs" | "sm" | "md" | "lg" | "xl";
type CardTone = "default" | "muted" | "ghost";

interface CardProps {
  children: ReactNode;
  size?: CardSize;
  tone?: CardTone;
  className?: string;
}

const cardBaseClass = "rounded-xl border transition-colors";

const cardShadowClasses: Record<CardSize, string> = {
  xs: "shadow-2xs",
  sm: "shadow-xs",
  md: "shadow-sm",
  lg: "shadow-md",
  xl: "shadow-lg",
};

const cardToneClasses: Record<CardTone, string> = {
  default: "border-border/80 bg-card text-card-foreground",
  muted: "border-border/80 bg-muted text-foreground",
  ghost: "border-transparent bg-transparent text-foreground shadow-none",
};

export function Card({
  children,
  size = "md",
  tone = "default",
  className = "",
}: CardProps) {
  return (
    <div
      className={cn(
        cardBaseClass,
        cardPaddingClasses[size],
        cardToneClasses[tone],
        tone !== "ghost" && cardShadowClasses[size],
        className,
      )}
    >
      {children}
    </div>
  );
}

/* =========================
   CardRow.tsx
========================= */

interface CardRowProps {
  children: ReactNode;
  gap?: LayoutGap;
  wrap?: boolean;
  className?: string;
}

export function CardRow({
  children,
  gap = "md",
  wrap = true,
  className = "",
}: CardRowProps) {
  return (
    <div className={cn("flex items-center", wrap && "flex-wrap", layoutGapClasses[gap], className)}>
      {children}
    </div>
  );
}

/* =========================
   CardStack.tsx
========================= */

interface CardStackProps {
  children: ReactNode;
  gap?: LayoutGap;
  className?: string;
}

export function CardStack({
  children,
  gap = "md",
  className = "",
}: CardStackProps) {
  return <div className={cn("flex flex-col", layoutGapClasses[gap], className)}>{children}</div>;
}

/* =========================
   ExpandableSelector.tsx
========================= */

type ExpandableSelectorProps = {
  value: string;
  onChange: (value: string) => void;
  selected?: boolean;
  readOnly?: boolean;
  placeholder?: string;
  maxLength?: number;
  minHeightClassName?: string;
  maxHeightClassName?: string;
  className?: string;
  textareaClassName?: string;
  onSelect?: () => void;
};

const expandableSelectionButtonClass =
  "flex w-14 shrink-0 items-center justify-center rounded-l-full";
const expandableIndicatorClass = "block h-4 w-4 rounded-full border transition-colors";

export function ExpandableSelector({
  value,
  onChange,
  selected = false,
  readOnly = false,
  placeholder = "Type here...",
  maxLength,
  minHeightClassName = "min-h-[46px]",
  maxHeightClassName = "max-h-[200px]",
  className,
  textareaClassName,
  onSelect,
}: ExpandableSelectorProps) {
  const { ref, resize } = useAutoResizingTextarea({ value, maxHeight: 200 });
  const isWholeSelectorClickable = readOnly && Boolean(onSelect);

  return (
    <div
      onClick={isWholeSelectorClickable ? onSelect : undefined}
      className={cn(
        "ui-expandable-shell ui-expandable-shell--interactive",
        selected && "ui-expandable-shell--selected",
        isWholeSelectorClickable && "cursor-pointer",
        className,
      )}
    >
      <button
        type="button"
        aria-pressed={selected}
        onClick={(event) => {
          event.stopPropagation();
          onSelect?.();
        }}
        className={expandableSelectionButtonClass}
      >
        <span
          className={cn(
            expandableIndicatorClass,
            selected ? "border-primary bg-primary" : "border-muted-foreground/50 bg-background",
          )}
        />
      </button>

      <div className="min-w-0 flex-1 pr-0.5">
        <textarea
          ref={ref}
          value={value}
          readOnly={readOnly}
          rows={1}
          maxLength={maxLength}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onInput={(event) => resize(event.currentTarget)}
          className={cn(
            "ui-expandable-textarea",
            isWholeSelectorClickable && "cursor-pointer",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName,
          )}
        />
      </div>
    </div>
  );
}

/* =========================
   ExpandableTextArea.tsx
========================= */

type ExpandableTextAreaProps = {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  placeholder?: string;
  maxLength?: number;
  minHeightClassName?: string;
  maxHeightClassName?: string;
  maxHeightPx?: number;
  className?: string;
  textareaClassName?: string;
};

export function ExpandableTextArea({
  value,
  onChange,
  readOnly = false,
  placeholder = "Type here...",
  maxLength,
  minHeightClassName = "min-h-[46px]",
  maxHeightClassName = "max-h-[200px]",
  maxHeightPx = 200,
  className,
  textareaClassName,
}: ExpandableTextAreaProps) {
  const { ref, resize } = useAutoResizingTextarea({ value, maxHeight: maxHeightPx });

  return (
    <div className={cn("ui-expandable-shell ui-expandable-shell--interactive", className)}>
      <div className="min-w-0 flex-1">
        <textarea
          ref={ref}
          value={value}
          readOnly={readOnly}
          rows={1}
          maxLength={maxLength}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onInput={(event) => resize(event.currentTarget)}
          className={cn(
            "ui-expandable-textarea ui-expandable-textarea--compact",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName,
          )}
        />
      </div>
    </div>
  );
}

/* =========================
   Input.tsx
========================= */

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: ControlSize;
  pill?: boolean;
}

export function Input({
  label,
  hint,
  error,
  variant = "secondary",
  size = "md",
  pill = false,
  id,
  className = "",
  disabled,
  ...props
}: InputProps) {
  const inputId = useFieldId(id, label);

  return (
    <div className={cn(formFieldClass, className)}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <input
        id={inputId}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={getInputControlClassName({
          size,
          variant,
          pill,
          error: Boolean(error),
        })}
        {...props}
      />

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}

/* =========================
   LargeInput.tsx
========================= */

interface LargeInputProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: TextareaSize;
  maxText?: number;
  showCount?: boolean;
  autoGrow?: boolean;
  maxAutoGrowHeight?: number;
  shellClassName?: string;
}

const textareaBaseClass = cn(
  controlBaseClass,
  "block resize-none border-0 bg-transparent text-foreground",
);

function getTextareaMinHeight(textarea: HTMLTextAreaElement, rows: number) {
  const styles = window.getComputedStyle(textarea);

  const lineHeight = parseFloat(styles.lineHeight) || 0;
  const paddingTop = parseFloat(styles.paddingTop) || 0;
  const paddingBottom = parseFloat(styles.paddingBottom) || 0;
  const borderTop = parseFloat(styles.borderTopWidth) || 0;
  const borderBottom = parseFloat(styles.borderBottomWidth) || 0;

  return lineHeight * rows + paddingTop + paddingBottom + borderTop + borderBottom;
}

function resizeLargeTextarea(params: {
  textarea: HTMLTextAreaElement;
  autoGrow: boolean;
  rows: number;
  maxAutoGrowHeight?: number;
}) {
  const { textarea, autoGrow, rows, maxAutoGrowHeight } = params;
  if (!autoGrow) return;

  const minHeight = getTextareaMinHeight(textarea, rows);
  const maxHeight = maxAutoGrowHeight ?? minHeight * 2;

  textarea.style.minHeight = `${minHeight}px`;
  resizeTextareaElement({ textarea, minHeight, maxHeight });
}

export function LargeInput({
  label,
  hint,
  error,
  id,
  className,
  variant = "secondary",
  size = "md",
  maxText,
  showCount = false,
  autoGrow = false,
  maxAutoGrowHeight,
  shellClassName,
  value,
  defaultValue,
  rows = 1,
  onInput,
  ...props
}: LargeInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inputId = useFieldId(id, label);

  const currentValue =
    typeof value === "string" ? value : typeof defaultValue === "string" ? defaultValue : "";
  const currentLength = currentValue.length;
  const showCounter = showCount && typeof maxText === "number";

  useEffect(() => {
    if (!textareaRef.current) return;

    resizeLargeTextarea({
      textarea: textareaRef.current,
      autoGrow,
      rows,
      maxAutoGrowHeight,
    });
  }, [autoGrow, defaultValue, maxAutoGrowHeight, rows, size, value]);

  return (
    <div className={cn(formFieldClass, className)}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <div
        className={cn(
          getTextareaShellClassName({ variant, error: Boolean(error) }),
          shellClassName,
        )}
      >
        <textarea
          ref={textareaRef}
          id={inputId}
          rows={rows}
          maxLength={maxText}
          value={value}
          defaultValue={defaultValue}
          aria-invalid={error ? true : undefined}
          className={cn(
            textareaBaseClass,
            autoGrow ? textareaBodySizeClasses[size] : textareaSizeClasses[size],
            autoGrow && "max-h-none overflow-y-hidden",
          )}
          onInput={(event) => {
            resizeLargeTextarea({
              textarea: event.currentTarget,
              autoGrow,
              rows,
              maxAutoGrowHeight,
            });
            onInput?.(event);
          }}
          {...props}
        />
      </div>

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : showCounter ? (
        <div className="flex items-center justify-between gap-3">
          {hint ? <p className={formHintClass}>{hint}</p> : <span />}
          <p className={cn(formHintClass, "ml-auto whitespace-nowrap")}>
            {currentLength}/{maxText}
          </p>
        </div>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}

/* =========================
   Modal.tsx
========================= */

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}

export function Modal({ open, onClose, title, children, footer, width = 480 }: ModalProps) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;

    const handler = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose, open]);

  if (!open || !isBrowser) return null;

  return createPortal(
    <div
      className="ui-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="ui-modal-panel"
        style={{ maxWidth: width }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="ui-modal-header">
          <h2 id={titleId} className="text-[1.05rem] font-semibold text-foreground">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="ui-icon-button h-8 w-8"
          >
            ✕
          </button>
        </div>
        <div className="ui-modal-body">{children}</div>
        {footer ? <div className="ui-modal-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}

/* =========================
   NumberStepper.tsx
========================= */

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

  const canDecrementValue = !disabled && (canDecrement ?? (min === undefined || value > min));
  const canIncrementValue = !disabled && (canIncrement ?? (max === undefined || value < max));

  function decrement() {
    if (!canDecrementValue) return;
    if (onDecrement) {
      onDecrement();
      return;
    }

    onChange(clampNumber(value - step, min, max));
  }

  function increment() {
    if (!canIncrementValue) return;
    if (onIncrement) {
      onIncrement();
      return;
    }

    onChange(clampNumber(value + step, min, max));
  }

  function commitDraft(rawValue: string) {
    const parsedValue = parseNumericValue(rawValue);

    if (parsedValue === null) {
      setDraftValue(String(value));
      return;
    }

    const nextValue = clampNumber(parsedValue, min, max);
    setDraftValue(String(nextValue));
    onChange(nextValue);
  }

  const shellPadding = size === "xs" ? "gap-0.5 p-0.5" : "gap-1 p-1";

  return (
    <div
      className={cn(stepperShellClass({ size, variant, pill }), shellPadding, className)}
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

/* =========================
   NumberStepperGroup.tsx
========================= */

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

  const segmentBase = "inline-flex items-center gap-0.5 [&+&]:border-l [&+&]:border-border";
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

/* =========================
   Select.tsx
========================= */

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
    "flex cursor-pointer items-center pr-10 text-left",
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
        <span className="truncate">{selectedOption?.label ?? placeholder ?? " "}</span>
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

export type { SelectChangeEvent };

/* =========================
   Spinner.tsx
========================= */

interface SpinnerProps {
  size?: number;
}

export function Spinner({ size = 20 }: SpinnerProps) {
  return (
    <span
      className="inline-block shrink-0 animate-spin rounded-full border-2 border-border border-t-accent"
      style={{ width: size, height: size, animationDuration: "0.7s" }}
      role="status"
      aria-label="Loading"
    />
  );
}

/* =========================
   ThemeToggle.tsx
========================= */

const SunIcon = () => (
  <svg
    width="15"
    height="15"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
  </svg>
);

const MoonIcon = () => (
  <svg
    width="15"
    height="15"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleTheme}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}

/* =========================
   Toggle.tsx
========================= */

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
}

export function Toggle({ label, checked, onChange, disabled, hint }: ToggleProps) {
  return (
    <div className={formFieldClass}>
      <label
        className={cn(
          "flex cursor-pointer select-none items-center gap-3",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <input
          type="checkbox"
          className="peer sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
        <span
          aria-hidden="true"
          className={cn(
            "ui-toggle-track",
            checked ? "border-accent bg-accent/30" : "border-border bg-input",
            "peer-focus-visible:ring-2 peer-focus-visible:ring-accent/50",
          )}
        >
          <span
            className={cn(
              "ui-toggle-thumb",
              checked ? "translate-x-5 bg-accent" : "bg-muted-foreground",
            )}
          />
        </span>
        <span className="text-sm text-foreground">{label}</span>
      </label>
      {hint ? <p className={cn(formHintClass, "ml-54px")}>{hint}</p> : null}
    </div>
  );
}

/* =========================
   Tooltip.tsx
========================= */

interface TooltipProps {
  title: string;
  size?: "sm" | "md" | "lg";
  children: ReactNode;
  className?: string;
}

const tooltipSizeClasses: Record<NonNullable<TooltipProps["size"]>, string> = {
  sm: "px-2 py-1 text-[0.72rem]",
  md: "px-2.5 py-1.5 text-[0.78rem]",
  lg: "px-3 py-2 text-[0.84rem]",
};

export function Tooltip({
  title,
  size = "md",
  children,
  className = "",
}: TooltipProps) {
  const tooltipId = useId();
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const contentRef = useRef<HTMLSpanElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!isOpen) {
      setPosition(null);
      return;
    }

    const trigger = triggerRef.current;
    const content = contentRef.current;
    if (!trigger || !content) return;

    const viewportPadding = 8;

    const update = () => {
      const triggerRect = trigger.getBoundingClientRect();
      const contentRect = content.getBoundingClientRect();
      const top = Math.max(viewportPadding, triggerRect.top - contentRect.height - 8);
      const left = clampNumber(
        triggerRect.left + triggerRect.width / 2,
        contentRect.width / 2 + viewportPadding,
        window.innerWidth - contentRect.width / 2 - viewportPadding,
      );

      setPosition({ top, left });
    };

    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);

    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [isOpen, title]);

  return (
    <span
      className={cn("relative inline-flex w-fit", className)}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={() => setIsOpen(true)}
      onBlur={() => setIsOpen(false)}
    >
      <span className="inline-flex" aria-describedby={tooltipId} ref={triggerRef}>
        {children}
      </span>

      {isOpen && isBrowser
        ? createPortal(
            <span
              id={tooltipId}
              role="tooltip"
              ref={contentRef}
              className={cn(
                "ui-tooltip",
                tooltipSizeClasses[size],
                position ? "opacity-100" : "opacity-0",
              )}
              style={position ? { top: position.top, left: position.left } : { top: 0, left: 0 }}
            >
              {title}
            </span>,
            document.body,
          )
        : null}
    </span>
  );
}

/* =========================
   Badge.tsx
========================= */

type BadgeVariant = "default" | "success" | "danger" | "warning" | "accent" | "muted";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: ControlSize;
}

const badgeBaseClass =
  "inline-flex items-center whitespace-nowrap rounded-md border font-medium leading-none";

const badgeVariantClasses: Record<BadgeVariant, string> = {
  default: "border-primary/30 bg-primary/20 text-primary-saturated",
  muted: "border-border bg-muted text-muted-foreground",
  accent: "border-accent/30 bg-accent/13 text-accent",
  danger: "border-destructive/25 bg-destructive/10 text-destructive",
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
};

export function Badge({ children, variant = "default", size = "xs" }: BadgeProps) {
  return (
    <span className={`${badgeBaseClass} ${badgeSizeClasses[size]} ${badgeVariantClasses[variant]}`}>
      {children}
    </span>
  );
}
