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

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "ui-button-primary",
  secondary: "ui-button-secondary",
  danger: "ui-button-danger",
  ghost: "ui-button-ghost",
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
        buttonVariantClasses[variant],
        pill ? "rounded-full" : "rounded-sm",
        borderStyle === "dotted" && "border-2 border-dashed border-border",
        controlSizeClasses[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
