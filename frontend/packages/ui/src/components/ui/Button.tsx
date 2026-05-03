import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { controlSizeClasses, type ControlSize } from "../../lib/sizes";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonBorderStyle = "solid" | "dotted";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: ButtonBorderStyle;
  children: ReactNode;
}

const buttonBaseClasses = "ui-button";
const activeClasses = "ui-button-active";
const disabledClasses = "ui-button-disabled";

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "ui-button-primary",
  secondary: "ui-button-secondary",
  danger: "ui-button-danger",
  ghost: "ui-button-ghost",
};

const borderStyleClasses: Record<ButtonBorderStyle, string> = {
  solid: "ui-button-border-solid",
  dotted: "ui-button-border-dotted",
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
