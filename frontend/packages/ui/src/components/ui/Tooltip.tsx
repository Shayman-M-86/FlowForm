import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cn, isBrowser, clampNumber } from "../../lib/utils";

interface TooltipProps {
  title?: string;
  content?: ReactNode;
  size?: "sm" | "md" | "lg";
  placement?: "top" | "right";
  pinOnClick?: boolean;
  children: ReactNode;
  className?: string;
}

const tooltipSizeClasses: Record<NonNullable<TooltipProps["size"]>, string> = {
  sm: "px-2 py-1 text-[0.72rem]",
  md: "px-2.5 py-1.5 text-[0.78rem]",
  lg: "px-3 py-2 text-[0.84rem]",
};

const tooltipPinnedEventName = "ui-tooltip:pinned";

export function Tooltip({
  title,
  content,
  size = "md",
  placement = "top",
  pinOnClick = false,
  children,
  className = "",
}: TooltipProps) {
  const tooltipId = useId();
  const triggerRef = useRef<HTMLSpanElement | null>(null);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!isOpen) {
      setPosition(null);
      return;
    }

    const trigger = triggerRef.current;
    const content = contentRef.current;
    if (!trigger || !content) return;

    const viewportPadding = 8;

    const update = () => {
      const gap = 8;
      const triggerRect = trigger.getBoundingClientRect();
      const contentRect = content.getBoundingClientRect();

      let top: number;
      let left: number;

      if (placement === "right") {
        left = clampNumber(
          triggerRect.right + 24,
          viewportPadding,
          window.innerWidth - contentRect.width - viewportPadding,
        );
        top = clampNumber(
          triggerRect.top - contentRect.height / 1.2,
          viewportPadding,
          window.innerHeight - contentRect.height - viewportPadding,
        );
      } else {
        const fitsAbove = triggerRect.top >= contentRect.height + gap + viewportPadding;
        const fitsBelow = window.innerHeight - triggerRect.bottom >= contentRect.height + gap + viewportPadding;
        const shouldPlaceAbove = fitsAbove || !fitsBelow;
        top = clampNumber(
          shouldPlaceAbove ? triggerRect.top - contentRect.height - gap : triggerRect.bottom + gap,
          viewportPadding,
          window.innerHeight - contentRect.height - viewportPadding,
        );
        left = clampNumber(
          triggerRect.left + triggerRect.width / 2 - contentRect.width / 2,
          viewportPadding,
          window.innerWidth - contentRect.width - viewportPadding,
        );
      }

      setPosition({ top, left });
    };

    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);

    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [isOpen, title, content]);

  const tooltipContent = content ?? title;
  const close = () => {
    setIsOpen(false);
    setIsPinned(false);
  };

  useEffect(() => {
    if (!pinOnClick || !isBrowser) return;

    const onPinned = (event: Event) => {
      const pinnedTooltipId = (event as CustomEvent<{ id: string }>).detail?.id;
      if (pinnedTooltipId !== tooltipId) {
        close();
      }
    };

    document.addEventListener(tooltipPinnedEventName, onPinned);
    return () => document.removeEventListener(tooltipPinnedEventName, onPinned);
  }, [pinOnClick, tooltipId]);

  useLayoutEffect(() => {
    if (!isOpen || !isPinned) return;

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
      }
    };

    const onMouseDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        contentRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }

      close();
    };

    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onMouseDown);

    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [isOpen, isPinned]);

  return (
    <span
      className={cn("relative inline-flex w-fit", className)}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => {
        if (!isPinned) {
          setIsOpen(false);
        }
      }}
      onFocus={() => setIsOpen(true)}
      onBlur={() => {
        if (!isPinned) {
          setIsOpen(false);
        }
      }}
    >
      <span
        className="inline-flex"
        aria-describedby={tooltipId}
        ref={triggerRef}
        onMouseDown={
          pinOnClick
            ? (event) => {
                event.preventDefault();
                event.stopPropagation();
                setIsPinned((current) => {
                  const next = !current;
                  setIsOpen(next);
                  if (next) {
                    document.dispatchEvent(
                      new CustomEvent(tooltipPinnedEventName, { detail: { id: tooltipId } }),
                    );
                  }
                  return next;
                });
              }
            : undefined
        }
      >
        {children}
      </span>

      {isOpen && isBrowser && tooltipContent
        ? createPortal(
            <div
              id={tooltipId}
              role="tooltip"
              ref={contentRef}
              className={cn(
                "ui-tooltip",
                isPinned && "pointer-events-auto select-text",
                tooltipSizeClasses[size],
                position ? "opacity-100" : "opacity-0",
              )}
              style={{
                ...(position ? { top: position.top, left: position.left } : { top: 0, left: 0 }),
                ...(isPinned ? { pointerEvents: "auto" } : undefined),
                transform: "none",
              }}
            >
              {tooltipContent}
            </div>,
            document.body,
          )
        : null}
    </span>
  );
}
