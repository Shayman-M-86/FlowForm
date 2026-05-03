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
import { cn, isBrowser } from "../../lib/utils.ts";
import { Button } from "./Button.tsx";

export interface DropdownMenuAction {
  key: string;
  content: ReactNode;
  onSelect?: () => void;
  closeOnSelect?: boolean;
}

export interface DropdownMenuSection {
  label?: ReactNode;
  actions: DropdownMenuAction[];
}

type DropdownMenuSize = "sm" | "md" | "lg" | "xl";
type DropdownMenuFullscreenAt = "never" | number;

interface DropdownMenuProps {
  open: boolean;
  onClose: () => void;
  trigger: React.RefObject<HTMLElement | null>;
  sections: DropdownMenuSection[];
  align?: "left" | "right";
  size?: DropdownMenuSize;
  fullscreenAt?: DropdownMenuFullscreenAt;
}

const dropdownMenuSizeClasses: Record<DropdownMenuSize, string> = {
  sm: "w-[220px]",
  md: "w-[280px]",
  lg: "w-[360px]",
  xl: "w-[440px]",
};

export function DropdownMenu({
  open,
  onClose,
  trigger,
  sections,
  align = "right",
  size = "sm",
  fullscreenAt = 640,
}: DropdownMenuProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!open || !isBrowser) return;

    const el = trigger.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const gap = 6;
    const top = rect.bottom + gap;
    const left = align === "right" ? rect.right : rect.left;

    setPosition({ top, left });
  }, [open, align, trigger]);

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

    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onMouse);

    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onMouse);
    };
  }, [open, onClose, trigger]);

  if (!open || !isBrowser) return null;

  const isFullscreenViewport =
    fullscreenAt !== "never" && window.innerWidth <= fullscreenAt;

  const panelStyle: React.CSSProperties = position
    ? isFullscreenViewport
      ? {
          inset: 0,
        }
      : {
          top: position.top,
          [align === "right" ? "right" : "left"]:
            align === "right" ? window.innerWidth - position.left : position.left,
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
        variant="ghost"
        size="sm"
        onClick={handleSelect}
        className="ui-dropdown-action-button"
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
        dropdownMenuSizeClasses[size],
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

          <div className="ui-dropdown-actions">
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
