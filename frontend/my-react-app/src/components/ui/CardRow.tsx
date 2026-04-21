import type { ReactNode } from "react";

interface CardRowProps {
  children: ReactNode;
  gap?: "xs" | "sm" | "md" | "lg" | "xl";
  wrap?: boolean;
  className?: string;
}

const gapClasses = {
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-5",
    lg: "gap-6",
    xl: "gap-8",
};

export function CardRow({
  children,
  gap = "md",
  wrap = true,
  className = "",
}: CardRowProps) {
  return (
    <div
      className={[
        "flex items-center",
        wrap ? "flex-wrap" : "",
        gapClasses[gap],
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}