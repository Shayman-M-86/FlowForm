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
  variant?: "primary" | "secondary" | "danger" | "destructive" | "ghost" | "text";
  className?: string;
}

export interface ButtonGroupTrigger {
  variant?: "primary" | "secondary" | "danger" | "destructive" | "ghost" | "text" | "icon";
  className?: string;
}

export type ButtonGroupGap = 0 | 0.5 | 1 | 1.5 | 2 | 3 | 4;

const gapClassMap: Record<ButtonGroupGap, string> = {
  0: "gap-0",
  0.5: "gap-0.5",
  1: "gap-1",
  1.5: "gap-1.5",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
};

interface ButtonGroupProps {
  items: ButtonGroupItem[];
  size?: ControlSize;
  gap?: ButtonGroupGap;
  overflow?: "auto" | "always";
  trigger?: ButtonGroupTrigger;
  className?: string;
}

export function ButtonGroup({
  items,
  size = "sm",
  gap = 1,
  overflow = "auto",
  trigger,
  className,
}: ButtonGroupProps) {
  const gapClass = gapClassMap[gap];
  const containerRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [open, setOpen] = useState(false);

  useLayoutEffect(() => {
    if (overflow === "always") {
      setCollapsed(true);
      return;
    }

    const container = containerRef.current;
    const measure = measureRef.current;
    if (!container || !measure) return;

    const check = () => setCollapsed(measure.scrollWidth > container.clientWidth);

    check();
    const ro = new ResizeObserver(check);
    ro.observe(container);
    ro.observe(measure);
    return () => ro.disconnect();
  }, [items, overflow]);

  return (
    <div ref={containerRef} className={cn("ui-button-group-wrapper", className)}>
      {/* Hidden measuring row — renders all buttons at natural width to detect overflow */}
      <div ref={measureRef} aria-hidden="true" className={cn("ui-button-group-measure", gapClass)}>
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
        <div className={cn("ui-button-group", gapClass)}>
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
            variant={trigger?.variant ?? "icon"}
            size={size}
            icon="ellipsis"
            aria-haspopup="menu"
            aria-expanded={open}
            aria-label="More actions"
            onClick={() => setOpen((o) => !o)}
            className={trigger?.className}
          />

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
