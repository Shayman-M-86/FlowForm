import { type ReactNode } from "react";
import { cn } from "../../lib/utils.ts";
import { badgeSizeClasses, type ControlSize } from "../../lib/sizes.ts";

type BadgeVariant = "default" | "success" | "danger" | "warning" | "accent" | "muted";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: ControlSize;
}

const badgeBaseClass = "ui-badge";

const badgeVariantClasses: Record<BadgeVariant, string> = {
  default: "ui-badge-default",
  muted: "ui-badge-muted",
  accent: "ui-badge-accent",
  danger: "ui-badge-danger",
  success: "ui-badge-success",
  warning: "ui-badge-warning",
};

export function Badge({ children, variant = "default", size = "xs" }: BadgeProps) {
  return (
    <span className={cn(badgeBaseClass, badgeSizeClasses[size], badgeVariantClasses[variant])}>
      {children}
    </span>
  );
}
