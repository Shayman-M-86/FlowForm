import { useId, type ReactNode } from "react";
import "./Tooltip.css";

interface TooltipProps {
  title: string;
  size?: "sm" | "md" | "lg";
  children: ReactNode;
  className?: string;
}

export function Tooltip({
  title,
  size = "md",
  children,
  className = "",
}: TooltipProps) {
  const tooltipId = useId();

  return (
    <span className={`tooltip ${className}`}>
      <span className="tooltip__trigger" aria-describedby={tooltipId}>
        {children}
      </span>

      <span
        id={tooltipId}
        role="tooltip"
        className={`tooltip__content tooltip__content--${size}`}
      >
        {title}
      </span>
    </span>
  );
}