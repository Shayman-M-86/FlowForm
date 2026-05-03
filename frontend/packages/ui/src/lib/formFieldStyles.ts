import { cn } from "./utils";
import { controlSizeClasses, type ControlSize } from "./sizes";

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
  secondary: "ui-surface-secondary",
  ghost: "ui-surface-ghost",
  quiet: "ui-surface-quiet",
};

const variantInteractive: Record<InputVariant, Record<FocusMode, string>> = {
  secondary: {
    focus: "ui-surface-secondary-focus",
    "focus-within": "ui-surface-secondary-focus-within",
  },
  ghost: {
    focus: "ui-surface-ghost-focus",
    "focus-within": "ui-surface-ghost-focus-within",
  },
  quiet: {
    focus: "ui-surface-quiet-focus",
    "focus-within": "ui-surface-quiet-focus-within",
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
