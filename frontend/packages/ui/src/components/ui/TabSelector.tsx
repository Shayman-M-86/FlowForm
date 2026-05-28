import {
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { cn } from "../../lib/utils";
import { Tooltip } from "./Tooltip";

export interface TabSelectorItem {
  id: string;
  label: ReactNode;
  disabled?: boolean;
  tooltip?: ReactNode;
}

interface TabSelectorProps {
  items: TabSelectorItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}

const SCROLL_AMOUNT = 220;

export function TabSelector({ items, activeId, onChange, className }: TabSelectorProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 1);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    updateScrollState();
    el.addEventListener("scroll", updateScrollState, { passive: true });
    const ro = new ResizeObserver(updateScrollState);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", updateScrollState);
      ro.disconnect();
    };
  }, [updateScrollState]);

  const scrollToButton = useCallback((id: string) => {
    const btn = buttonRefs.current.get(id);
    const el = scrollRef.current;
    if (!btn || !el) return;
    const elRect = el.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    const overflowRight = btnRect.right - elRect.right;
    const overflowLeft = elRect.left - btnRect.left;
    if (overflowRight > 0) {
      el.scrollBy({ left: overflowRight, behavior: "smooth" });
    } else if (overflowLeft > 0) {
      el.scrollBy({ left: -overflowLeft, behavior: "smooth" });
    }
  }, []);

  const scroll = (direction: "left" | "right") => {
    const el = scrollRef.current;
    if (!el) return;

    const elRect = el.getBoundingClientRect();
    const buttons = [...buttonRefs.current.values()];
    if (!buttons.length) return;

    const rawTarget = el.scrollLeft + (direction === "left" ? -SCROLL_AMOUNT : SCROLL_AMOUNT);

    // Find the button whose left edge will be closest to the container's left
    // edge after scrolling, and align to it exactly.
    const snapped = buttons.reduce<{ btn: HTMLButtonElement; dist: number } | null>((best, btn) => {
      const btnScrollLeft = btn.getBoundingClientRect().left - elRect.left + el.scrollLeft;
      const dist = Math.abs(btnScrollLeft - rawTarget);
      return !best || dist < best.dist ? { btn, dist } : best;
    }, null);

    const finalTarget = snapped
      ? snapped.btn.getBoundingClientRect().left - elRect.left + el.scrollLeft
      : rawTarget;

    el.scrollTo({ left: finalTarget, behavior: "smooth" });
  };

  const showArrows = canScrollLeft || canScrollRight;

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Tab row: all buttons in one flex container so they share the same height */}
      <div className="flex items-stretch">
        {/* Left scroll button */}
        {showArrows && (
          <button
            type="button"
            aria-label="Scroll tabs left"
            onClick={() => scroll("left")}
            className={cn(
              "ui-button-ghost",
              "p-2 rounded-none rounded-l-sm border-0",
              !canScrollLeft && "pointer-events-none opacity-30",
            )}
            style={canScrollLeft ? { boxShadow: "4px 0 8px 0 rgb(0 0 0 / 0.1)", clipPath: "inset(0 -12px 0 0)" } : undefined}
          >
            ‹
          </button>
        )}

        {/* Clip only horizontally so the indicator can escape downward */}
        <div
          className="min-w-0 flex-1"
          style={{ clipPath: "inset(0 0 -10px 0)" }}
        >
          <div
            ref={scrollRef}
            className="flex h-full scrollbar-none"
            style={{ overflowX: "auto", overflowY: "visible", scrollbarWidth: "none", msOverflowStyle: "none" } as React.CSSProperties}
          >
            {items.map((item, index) => {
              const isActive = item.id === activeId;
              return (
                <div key={item.id} className="relative flex items-center overflow-visible">
                  {index > 0 && (
                    <div aria-hidden="true" className="w-px self-stretch my-2 bg-border" />
                  )}
                  <Tooltip content={item.disabled ? item.tooltip : undefined}>
                    <button
                      ref={(el) => {
                        if (el) buttonRefs.current.set(item.id, el);
                        else buttonRefs.current.delete(item.id);
                      }}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      disabled={item.disabled}
                      onClick={() => { if (!item.disabled) { onChange(item.id); scrollToButton(item.id); } }}
                      className={cn(
                        "ui-button-ghost",
                        "h-full px-4 py-2 text-sm font-medium whitespace-nowrap border-0",
                        isActive ? "text-foreground" : "text-muted-foreground",
                        item.disabled && "opacity-40 cursor-not-allowed",
                      )}
                    >
                      {item.label}
                    </button>
                  </Tooltip>
                  <span
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-x-0 bottom-0 h-[10px] overflow-hidden"
                  >
                    <span
                      className={cn(
                        "absolute inset-x-0 bottom-[-1px] h-[4px] rounded-full bg-primary",
                        "transition-transform duration-140 ease-out will-change-transform",
                        isActive
                          ? "translate-y-0"
                          : "translate-y-[8px]",
                      )}
                    />
                  </span>
                </div>
              );
            })}
          </div>
            <div className="h-px bg-border" />
        </div>

        {/* Right scroll button */}
        {showArrows && (
          <button
            type="button"
            aria-label="Scroll tabs right"
            onClick={() => scroll("right")}
            className={cn(
              "ui-button-ghost",
              "p-2 rounded-none rounded-r-sm border-0",
              !canScrollRight && "pointer-events-none opacity-30",
            )}
            style={canScrollRight ? { boxShadow: "-4px 0 8px 0 rgb(0 0 0 / 0.1)", clipPath: "inset(0 0 0 -12px)" } : undefined}
          >
            ›
          </button>
        )}
      </div>

      {/* Separator line */}

    </div>
  );
}
