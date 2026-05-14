import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { controlSizeClasses, type ControlSize } from "../../lib/sizes";
import { Ellipsis, Pencil, Plus, Trash2, X } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "danger"  | "destructive" | "ghost" | "text" | "icon";
type ButtonBorderStyle = "solid" | "dotted";
export type ButtonIcon = "plus" | "edit" | "delete" | "close" | "ellipsis";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: ButtonBorderStyle;
  icon?: ButtonIcon;
  bare?: boolean;
  children?: ReactNode;
}

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "ui-button-primary",
  secondary: "ui-button-secondary",
  danger: "ui-button-danger",
  destructive: "ui-button-destructive",
  ghost: "ui-button-ghost",
  text: "ui-button-text",
  icon: "ui-button-transparent-icon",
};

const buttonVariantBareClasses: Partial<Record<ButtonVariant, string>> = {
  ghost: "ui-button-ghost-bare",
};

const iconSizeMap: Record<ControlSize, number> = {
  xxs: 18,
  xs: 20,
  sm: 22,
  md: 24,
  lg: 26,
  xl: 28,
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
  edit: (size) => <Pencil size={size} />,
  delete: (size) => <Trash2 size={size} />,
  close: (size) => <X size={size} />,
  ellipsis: (size) => <Ellipsis size={size} />,
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button({
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
}, ref) {
  const variantClass = bare
    ? (buttonVariantBareClasses[variant] ?? buttonVariantClasses[variant])
    : buttonVariantClasses[variant]
  const hasChildren = children !== undefined && children !== null && children !== false;

  return (
    <button
      ref={ref}
      disabled={disabled}
      className={cn(
        variantClass,
        pill ? "rounded-full" : "rounded-sm",
        borderStyle === "dotted" && "border-2 border-dashed border-border",
        controlSizeClasses[size],
        icon && hasChildren && iconPaddingMap[size],
        icon && !hasChildren && "aspect-square items-center justify-center p-0",
        className,
      )}
      {...props}
    >
      {icon && icons[icon](iconSizeMap[size])}
      {children}
    </button>
  );
});
