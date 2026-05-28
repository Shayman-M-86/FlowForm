import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { badgeSizeClasses, type ControlSize } from "../../lib/sizes";

type BadgeVariant = "default" | "success" | "danger" | "warning" | "accent" | "muted";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: ControlSize;
  className?: string;
  onClick?: ButtonHTMLAttributes<HTMLButtonElement>["onClick"];
}

const badgeVariantClasses: Record<BadgeVariant, string> = {
  default: "ui-badge-default",
  muted: "ui-badge-muted",
  accent: "ui-badge-accent",
  danger: "ui-badge-danger",
  success: "ui-badge-success",
  warning: "ui-badge-warning",
};

export function Badge({ children, variant = "default", size = "xs", className, onClick }: BadgeProps) {
  const classes = cn("ui-badge", badgeSizeClasses[size], badgeVariantClasses[variant], className);

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(classes, "ui-badge-action")}>
        {children}
      </button>
    );
  }

  return <span className={classes}>{children}</span>;
}
