import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface TooltipProps {
  title: string;
  size?: "sm" | "md" | "lg";
  children: ReactNode;
  className?: string;
}

const sizeClasses: Record<NonNullable<TooltipProps["size"]>, string> = {
  sm: "px-2 py-1 text-[0.72rem]",
  md: "px-2.5 py-1.5 text-[0.78rem]",
  lg: "px-3 py-2 text-[0.84rem]",
};

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
      className={["relative inline-flex w-fit", className].filter(Boolean).join(" ")}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      onFocus={() => setIsOpen(true)}
      onBlur={() => setIsOpen(false)}
    >
      <span
        className="inline-flex"
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
          className={[
            "pointer-events-none fixed z-9999 -translate-x-1/2 whitespace-nowrap rounded-sm border border-border bg-popover text-popover-foreground shadow-sm transition-opacity duration-150",
            sizeClasses[size],
            position ? "opacity-100" : "opacity-0",
          ].join(" ")}
          style={position ? { top: position.top, left: position.left } : { top: 0, left: 0 }}
        >
          {title}
        </span>,
        document.body,
      )}
    </span>
  );
}
