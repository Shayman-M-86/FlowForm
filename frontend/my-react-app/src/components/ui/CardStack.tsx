import type { ReactNode } from "react";

interface CardStackProps {
  children: ReactNode;
  gap?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
}

const gapClasses = {
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-5",
    lg: "gap-6",
    xl: "gap-8",
};

export function CardStack({
  children,
  gap = "md",
  className = "",
}: CardStackProps) {
  return (
    <div className={["flex flex-col", gapClasses[gap], className].join(" ")}>
      {children}
    </div>
  );
}