import type { ButtonHTMLAttributes, ReactNode } from "react";
import { controlSizeClasses, type ControlSize } from "./uiSizes";


interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: ControlSize;
  pill?: boolean;
  borderStyle?: "solid" | "dotted";
  children: ReactNode;
}

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-primary text-primary-foreground border-transparent font-semibold hover:bg-accent",
  secondary:
    "bg-input text-secondary-foreground border-border/40 font-semibold hover:bg-hover-highlight hover:border-ring/80",
  danger:
    "bg-transparent text-destructive border-destructive/30 font-semibold hover:bg-destructive/10",
  ghost:
    "bg-transparent text-accent-foreground border-transparent font-semibold shadow-none hover:bg-muted hover:border-ring/20",
};

export function Button({
  variant = "secondary",
  size = "md",
  pill = false,
  borderStyle = "solid",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={[
        "inline-flex items-center justify-center gap-1.5",
        "border cursor-pointer whitespace-nowrap transition-colors duration-150",
        "active:scale-95 active:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed",
        borderStyle === "dotted" ? "border-dashed border-2" : "",
        pill ? "rounded-full" : "rounded-sm",
        variant !== "ghost" ? "shadow-sm" : "shadow-none",
        variantClasses[variant],
        controlSizeClasses[size],
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