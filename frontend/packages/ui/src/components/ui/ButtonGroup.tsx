import {
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";
import { DropdownMenu } from "./DropdownMenu";
import type { ControlSize } from "../../lib/sizes";

export interface ButtonGroupItem {
  key: string;
  label: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger" | "ghost" | "text";
  className?: string;
}

export interface ButtonGroupTrigger {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "text";
  className?: string;
}

interface ButtonGroupProps {
  items: ButtonGroupItem[];
  size?: ControlSize;
  trigger?: ButtonGroupTrigger;
  className?: string;
}

export function ButtonGroup({
  items,
  size = "sm",
  trigger,
  className,
}: ButtonGroupProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);

  useLayoutEffect(() => {
    const container = containerRef.current;
    const measure = measureRef.current;
    if (!container || !measure) return;

    const check = () => setCollapsed(measure.scrollWidth > container.clientWidth);

    check();
    const ro = new ResizeObserver(check);
    ro.observe(container);
    ro.observe(measure);
    return () => ro.disconnect();
  }, [items]);

  return (
    <div ref={containerRef} className={cn("ui-button-group-wrapper", className)}>
      {/* Hidden measuring row — renders all buttons at natural width to detect overflow */}
      <div ref={measureRef} aria-hidden="true" className="ui-button-group-measure">
        {items.map((item) => (
          <Button
            key={item.key}
            type="button"
            variant={item.variant ?? "secondary"}
            size={size}
            className={item.className}
            tabIndex={-1}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {!collapsed && (
        <div className="ui-button-group">
          {items.map((item) => (
            <Button
              key={item.key}
              type="button"
              variant={item.variant ?? "secondary"}
              size={size}
              disabled={item.disabled}
              onClick={item.onClick}
              className={item.className}
            >
              {item.label}
            </Button>
          ))}
        </div>
      )}

      {collapsed && (
        <>
          <Button
            ref={triggerRef}
            type="button"
            variant={trigger?.variant ?? "secondary"}
            size={size}
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className={trigger?.className}
          >
            • • •
          </Button>

          <DropdownMenu
            open={open}
            onClose={() => setOpen(false)}
            trigger={triggerRef}
            align="auto"
            direction="auto"
            size="auto"
            fullscreenAt="never"
            sections={[{
              actions: items.map((item) => ({
                key: item.key,
                content: item.label,
                variant: item.variant === "text" ? "ghost" : (item.variant ?? "ghost"),
                onSelect: item.onClick,
              })),
            }]}
          />
        </>
      )}
    </div>
  );
}
