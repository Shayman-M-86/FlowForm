import type { ReactNode } from "react";
import { badgeSizeClasses, type ControlSize } from "./uiSizes";

type BadgeVariant =
  | "default"
  | "success"
  | "danger"
  | "warning"
  | "accent"
  | "muted";

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: ControlSize;
}

const baseClass =
  "inline-flex items-center whitespace-nowrap rounded-md border font-medium leading-none";

const variantClasses: Record<BadgeVariant, string> = {
  default: "border-primary/30 bg-primary/20 text-primary-saturated",
  muted: "border-border bg-muted text-muted-foreground",
  accent: "border-accent/30 bg-accent/13 text-accent",
  danger: "border-destructive/25 bg-destructive/10 text-destructive",
  success: "border-success/25 bg-success/10 text-success",
  warning: "border-warning/25 bg-warning/10 text-warning",
};

export function Badge({
  children,
  variant = "default",
  size = "xs",
}: BadgeProps) {
  return (
    <span className={`${baseClass} ${badgeSizeClasses[size]} ${variantClasses[variant]}`}>
      {children}
    </span>
  );
}