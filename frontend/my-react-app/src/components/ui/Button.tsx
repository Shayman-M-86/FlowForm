import type { ButtonHTMLAttributes, ReactNode } from "react";
import { controlSizeClasses, type ControlSize } from "./uiSizes";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonBorderStyle = "solid" | "dotted";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: ButtonBorderStyle;
  children: ReactNode;
}

const baseClasses =
  "cursor-pointer border";

const activeClasses = "active:scale-95 active:opacity-80 ";

const disabledClasses =
  "disabled:cursor-not-allowed disabled:opacity-50 ";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-transparent bg-primary text-primary-foreground font-semibold hover:bg-accent shadow-sm",
  secondary:
    "border-border/80 bg-input text-secondary-foreground font-semibold hover:bg-hover-highlight hover:border-ring/80 shadow-sm",
  danger:
    "border-destructive/30 bg-transparent text-destructive font-semibold hover:bg-destructive/10 shadow-sm",
  ghost:
    "border-transparent bg-transparent text-accent-foreground font-semibold hover:bg-muted hover:border-ring/20 shadow-none",
};

const borderStyleClasses: Record<ButtonBorderStyle, string> = {
  solid: "",
  dotted: "border-dashed border-2",
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
      className={[
        baseClasses,
        disabled ? "" : activeClasses,
        variantClasses[variant],
        pill ? "rounded-full" : "rounded-sm",
        borderStyleClasses[borderStyle],
        controlSizeClasses[size],
        disabled ? disabledClasses : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
