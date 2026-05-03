import { type ReactNode } from "react";
import { cn } from "../../lib/utils.ts";
import { cardPaddingClasses, layoutGapClasses, type LayoutGap } from "../../lib/sizes.ts";

type CardSize = "xs" | "sm" | "md" | "lg" | "xl";
type CardTone = "default" | "muted" | "ghost";

interface CardProps {
  children: ReactNode;
  size?: CardSize;
  tone?: CardTone;
  className?: string;
}

const cardBaseClass = "ui-card";

const cardShadowClasses: Record<CardSize, string> = {
  xs: "shadow-2xs",
  sm: "shadow-xs",
  md: "shadow-sm",
  lg: "shadow-md",
  xl: "shadow-lg",
};

const cardToneClasses: Record<CardTone, string> = {
  default: "ui-card-default",
  muted: "ui-card-muted",
  ghost: "ui-card-ghost",
};

export function Card({
  children,
  size = "md",
  tone = "default",
  className = "",
}: CardProps) {
  return (
    <div
      className={cn(
        cardBaseClass,
        cardPaddingClasses[size],
        cardToneClasses[tone],
        tone !== "ghost" && cardShadowClasses[size],
        className,
      )}
    >
      {children}
    </div>
  );
}

interface CardRowProps {
  children: ReactNode;
  gap?: LayoutGap;
  wrap?: boolean;
  className?: string;
}

export function CardRow({
  children,
  gap = "md",
  wrap = true,
  className = "",
}: CardRowProps) {
  return (
    <div className={cn("flex items-center", wrap && "flex-wrap", layoutGapClasses[gap], className)}>
      {children}
    </div>
  );
}

interface CardStackProps {
  children: ReactNode;
  gap?: LayoutGap;
  className?: string;
}

export function CardStack({
  children,
  gap = "md",
  className = "",
}: CardStackProps) {
  return <div className={cn("flex flex-col", layoutGapClasses[gap], className)}>{children}</div>;
}
