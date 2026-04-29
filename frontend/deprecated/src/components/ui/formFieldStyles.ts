import { type ControlSize, controlSizeClasses } from "../../index.optimized";

const inputMinWidthClasses: Record<ControlSize, string> = {
  xxs: "min-w-16",
  xs:  "min-w-20",
  sm:  "min-w-24",
  md:  "min-w-32",
  lg:  "min-w-40",
  xl:  "min-w-48",
};

export type InputVariant = "secondary" | "ghost" | "quiet";
export type FocusMode = "focus" | "focus-within";

export const formFieldClass = "flex flex-col gap-1.5";
export const formLabelClass = "text-[0.82rem] font-medium text-muted-foreground";
export const formHintClass = "text-[0.8rem] text-muted-foreground";
export const formErrorClass = "text-[0.8rem] text-destructive";

export const controlBaseClass =
  "w-full outline-none transition-colors placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60";

const surfaceRoundedClass = "w-full text-foreground transition-colors";

const variantSurface: Record<InputVariant, string> = {
  secondary: "border border-border bg-input",
  ghost: "border border-transparent bg-transparent",
  quiet: "border border-border bg-transparent",
};

const variantInteractive: Record<InputVariant, Record<FocusMode, string>> = {
  secondary: {
    focus: " focus:border-accent focus:bg-secondary ",
    "focus-within":
      " focus-within:border-accent focus-within:bg-secondary ",
  },
  ghost: {
    focus: " focus:bg-muted focus:border-transparent ",
    "focus-within":
      " focus-within:bg-muted focus-within:border-transparent ",
  },
  quiet: {
    focus:
      " focus:bg-muted focus:border-ring/80 read-only:bg-transparent read-only:text-foreground read-only:border-border",
    "focus-within":
      " focus-within:bg-muted focus-within:border-ring/80 read-only:bg-transparent read-only:text-foreground read-only:border-border",
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
  return [
    surfaceRoundedClass,
    variantSurface[variant],
    variantInteractive[variant][focusMode],
    pill ? "rounded-full" : "rounded-sm",
    error ? "border-destructive/50" : "",
    extra,
  ]
    .filter(Boolean)
    .join(" ");
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
  return [
    controlBaseClass,
    controlSizeClasses[size],
    inputMinWidthClasses[size],
    getSurfaceClassName({ variant, focusMode: "focus", pill, error }),
    className,
  ]
    .filter(Boolean)
    .join(" ");
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