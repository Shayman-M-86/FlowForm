import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { controlSizeClasses, type ControlSize } from "../../lib/sizes";
import { Plus } from 'lucide-react';

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost" | "text" | "icon";
type ButtonBorderStyle = "solid" | "dotted";
export type ButtonIcon = "plus";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: ButtonBorderStyle;
  icon?: ButtonIcon;
  bare?: boolean;
  children: ReactNode;
}

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "ui-button-primary",
  secondary: "ui-button-secondary",
  danger: "ui-button-danger",
  ghost: "ui-button-ghost",
  text: "ui-button-text",
  icon: "ui-button-transparent-icon",
};

const buttonVariantBareClasses: Partial<Record<ButtonVariant, string>> = {
  ghost: "ui-button-ghost-bare",
};

const iconSizeMap: Record<ControlSize, number> = {
  xxs: 16,
  xs: 18,
  sm: 20,
  md: 22,
  lg: 24,
  xl: 26,
};

const iconPaddingMap: Record<ControlSize, string> = {
  xxs: "pl-1 gap-1",
  xs: "pl-1.5 gap-1",
  sm: "pl-2 gap-1",
  md: "pl-2.5 gap-1",
  lg: "pl-3 gap-1",
  xl: "pl-3.5 gap-1",
};

const icons: Record<ButtonIcon, (size: number) => ReactNode> = {
  plus: (size) => <Plus size={size} />,
};

export function Button({
  variant = "secondary",
  size = "md",
  pill = false,
  borderStyle = "solid",
  icon,
  bare = false,
  className = "",
  children,
  disabled,
  ...props
}: ButtonProps) {
  const variantClass = bare
    ? (buttonVariantBareClasses[variant] ?? buttonVariantClasses[variant])
    : buttonVariantClasses[variant]

  return (
    <button
      disabled={disabled}
      className={cn(
        variantClass,
        pill ? "rounded-full" : "rounded-sm",
        borderStyle === "dotted" && "border-2 border-dashed border-border",
        controlSizeClasses[size],
        icon && iconPaddingMap[size],
        className,
      )}
      {...props}
    >
      {icon && icons[icon](iconSizeMap[size])}
      {children}
    </button>
  );
}
