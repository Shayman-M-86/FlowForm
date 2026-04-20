import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
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
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const contentRef = useRef<HTMLSpanElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!isOpen) {
      setPosition(null);
      return;
    }
    const trigger = triggerRef.current;
    const content = contentRef.current;
    if (!trigger || !content) return;

    const update = () => {
      const rect = trigger.getBoundingClientRect();
      const contentRect = content.getBoundingClientRect();
      const top = rect.top - contentRect.height - 8;
      const left = rect.left + rect.width / 2;
      setPosition({ top, left });
    };

    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [isOpen, title]);

  return (
    <span
      className={`tooltip ${className}`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={() => setIsOpen(true)}
      onBlur={() => setIsOpen(false)}
    >
      <span
        className="tooltip__trigger"
        aria-describedby={tooltipId}
        ref={triggerRef}
      >
        {children}
      </span>

      {isOpen && createPortal(
        <span
          id={tooltipId}
          role="tooltip"
          ref={contentRef}
          className={`tooltip__content tooltip__content--portal tooltip__content--${size} ${position ? "tooltip__content--visible" : ""}`}
          style={position ? { top: position.top, left: position.left } : undefined}
        >
          {title}
        </span>,
        document.body,
      )}
    </span>
  );
}
