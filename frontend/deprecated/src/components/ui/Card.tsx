import type { ReactNode } from "react";

type CardSize = "xs" | "sm" | "md" | "lg" | "xl";
type CardTone = "default" | "muted" | "ghost";

interface CardProps {
  children: ReactNode;
  size?: CardSize;
  tone?: CardTone;
  className?: string;
}

const baseClass =
  "rounded-xl border transition-colors";

const sizeClasses: Record<CardSize, string> = {
  xs: "p-2",
  sm: "p-3",
  md: "p-5",
    lg: "p-6",
    xl: "p-8",
};

const shadowClasses: Record<CardSize, string> = {
  xs: "shadow-2xs",
  sm: "shadow-xs",
  md: "shadow-sm",
  lg: "shadow-md",
  xl: "shadow-lg",
};

const toneClasses: Record<CardTone, string> = {
  default: "border-border/80 bg-card text-card-foreground",
  muted: "border-border/80 bg-muted text-foreground",
  ghost: "border-transparent bg-transparent text-foreground shadow-none",
};

export function Card({
  children,
  size = "md",
  tone = "default",
  className = "",
}: CardProps) {
  const shadow = tone === "ghost" ? "" : shadowClasses[size];
  return (
    <div
      className={[baseClass, sizeClasses[size], toneClasses[tone], shadow, className].join(" ")}
    >
      {children}
    </div>
  );
}