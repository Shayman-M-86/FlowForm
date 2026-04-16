import "./Badge.css";

type BadgeVariant = "default" | "success" | "danger" | "warning" | "accent" | "muted";
type BadgeSize = "sm" | "md" | "lg" | "xl";

interface BadgeProps {
  children: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
}

export function Badge({ children, variant = "default", size = "md" }: BadgeProps) {
  return <span className={`badge badge--${variant} badge--${size}`}>{children}</span>;
}
