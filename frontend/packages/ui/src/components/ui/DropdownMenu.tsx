import * as React from "react";
import {
  cloneElement,
  isValidElement,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn, isBrowser } from "../../lib/utils";
import { Button } from "./Button";

export interface DropdownMenuAction {
  key: string;
  content: ReactNode;
  variant?: "primary" | "secondary" | "danger" | "destructive" | "ghost";
  onSelect?: () => void;
  closeOnSelect?: boolean;
}

export interface DropdownMenuSection {
  label?: ReactNode;
  actions: DropdownMenuAction[];
}

type DropdownMenuSize = "auto" | "sm" | "md" | "lg" | "xl";
type DropdownMenuWidth = number | string;
type DropdownMenuFullscreenAt = "never" | number;
type DropdownMenuButtonAlign = "left" | "center" | "right";
export type DropdownMenuDirection = "down" | "up" | "auto";
export type DropdownMenuAlign = "left" | "right" | "auto";

interface DropdownMenuProps {
  open: boolean;
  onClose: () => void;
  trigger: React.RefObject<HTMLElement | null>;
  sections: DropdownMenuSection[];
  align?: DropdownMenuAlign;
  direction?: DropdownMenuDirection;
  buttonAlign?: DropdownMenuButtonAlign;
  positioning?: "fixed" | "absolute";
  size?: DropdownMenuSize;
  width?: DropdownMenuWidth;
  fullscreenAt?: DropdownMenuFullscreenAt;
  maxHeight?: string;
}

const dropdownMenuSizeClasses: Record<DropdownMenuSize, string> = {
  auto: "w-max",
  sm: "w-[190px]",
  md: "w-[280px]",
  lg: "w-[360px]",
  xl: "w-[440px]",
};

function resolvePosition(
  rect: DOMRect,
  alignProp: DropdownMenuAlign,
  directionProp: DropdownMenuDirection,
  positioning: "fixed" | "absolute",
  gap: number,
): { top?: number; bottom?: number; left: number; minWidth: number; resolvedAlign: "left" | "right" } {
  const scrollY = positioning === "absolute" ? window.scrollY : 0;
  const scrollX = positioning === "absolute" ? window.scrollX : 0;

  const resolvedAlign: "left" | "right" =
    alignProp === "auto"
      ? rect.left > window.innerWidth / 2 ? "right" : "left"
      : alignProp;

  const resolvedDirection: "up" | "down" =
    directionProp === "auto"
      ? rect.top > window.innerHeight / 2 ? "up" : "down"
      : directionProp;

  const left = (resolvedAlign === "right" ? rect.right : rect.left) + scrollX;

  if (resolvedDirection === "up") {
    return { bottom: (window.innerHeight - rect.top + gap) - scrollY, left, minWidth: rect.width, resolvedAlign };
  } else {
    return { top: rect.bottom + gap + scrollY, left, minWidth: rect.width, resolvedAlign };
  }
}

export function DropdownMenu({
  open,
  onClose,
  trigger,
  sections,
  align = "right",
  direction = "down",
  buttonAlign = "center",
  positioning = "fixed",
  size = "sm",
  width,
  fullscreenAt = 640,
  maxHeight,
}: DropdownMenuProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState<{
    top?: number;
    bottom?: number;
    left: number;
    minWidth: number;
    resolvedAlign: "left" | "right";
  } | null>(null);

  useLayoutEffect(() => {
    if (!open || !isBrowser) return;
    const el = trigger.current;
    if (!el) return;
    setPosition(resolvePosition(el.getBoundingClientRect(), align, direction, positioning, 6));
  }, [open, align, direction, positioning, trigger]);

  useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    const onMouse = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        !trigger.current?.contains(e.target as Node)
      ) {
        onClose();
      }
    };

    const reposition = () => {
      const el = trigger.current;
      if (!el) return;
      setPosition(resolvePosition(el.getBoundingClientRect(), align, direction, positioning, 6));
    };

    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onMouse);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, { capture: true, passive: true });

    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onMouse);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, { capture: true });
    };
  }, [open, onClose, trigger, align, direction, positioning]);

  if (!open || !isBrowser) return null;

  const isFullscreenViewport =
    fullscreenAt !== "never" && window.innerWidth <= fullscreenAt;

  const resolvedAlign = position?.resolvedAlign ?? (align === "auto" ? "right" : align);

  const panelStyle: React.CSSProperties = position
    ? isFullscreenViewport
      ? { inset: 0 }
      : {
          top: position.top,
          bottom: position.bottom,
          left: position.left,
          width,
          minWidth: size === "auto" ? position.minWidth : undefined,
          transform: resolvedAlign === "right" ? "translateX(-100%)" : undefined,
        }
    : { visibility: "hidden" };

  const renderAction = (action: DropdownMenuAction) => {
    const content = action.content;
    const closeOnSelect = action.closeOnSelect ?? true;

    const handleSelect = () => {
      action.onSelect?.();

      if (closeOnSelect) {
        onClose();
      }
    };

    if (isValidElement<{ onClick?: React.MouseEventHandler }>(content)) {
      return cloneElement(content, {
        onClick: (event) => {
          content.props.onClick?.(event);
          handleSelect();
        },
      });
    }

    return (
      <Button
        type="button"
        role="menuitem"
        variant={action.variant ?? "ghost"}
        size="sm"
        onClick={handleSelect}
        className={cn(
          "ui-dropdown-action-button",
          buttonAlign === "left" && "justify-start text-left",
          buttonAlign === "center" && "justify-center text-center",
          buttonAlign === "right" && "justify-end text-right",
        )}
      >
        {content}
      </Button>
    );
  };

  const panel = (
    <div
      ref={panelRef}
      role="menu"
      aria-orientation="vertical"
      style={panelStyle}
      tabIndex={-1}
      className={cn(
        "ui-dropdown-panel",
        positioning === "absolute" && "ui-dropdown-panel-absolute",
        width === undefined && dropdownMenuSizeClasses[size],
        isFullscreenViewport && "ui-dropdown-panel-fullscreen",
      )}
    >
      {isFullscreenViewport ? (
        <div className="ui-dropdown-close-row">
          <button
            type="button"
            aria-label="Close menu"
            onClick={onClose}
            className="ui-dropdown-close-button"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
      ) : null}

      {sections.map((section, si) => (
        <div
          key={si}
          role="group"
          aria-label={typeof section.label === "string" ? section.label : undefined}
        >
          {si > 0 ? <div className="ui-dropdown-separator" role="separator" /> : null}

          {section.label ? (
            <div className="ui-dropdown-section-label">
              {section.label}
            </div>
          ) : null}

          <div
            className="ui-dropdown-actions"
            style={maxHeight ? { maxHeight, overflowY: "auto" } : undefined}
          >
            {section.actions.map((action) => (
              <div key={action.key}>{renderAction(action)}</div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  return createPortal(
    <>
      <div
        onClick={onClose}
        aria-hidden="true"
        className={cn("hidden", isFullscreenViewport && "ui-dropdown-overlay")}
      />
      {panel}
    </>,
    document.body,
  );
}
