import * as React from "react";
import { cn } from "../../lib/utils";

type ExpandableSelectorProps = {
  value: string;
  onChange: (value: string) => void;
  selected?: boolean;
  readOnly?: boolean;
  placeholder?: string;
  maxLength?: number;
  minHeightClassName?: string;
  maxHeightClassName?: string;
  className?: string;
  textareaClassName?: string;
  onSelect?: () => void;
};

export function ExpandableSelector({
  value,
  onChange,
  selected = false,
  readOnly = false,
  placeholder = "Type here...",
  maxLength,
  minHeightClassName = "min-h-[46px]",
  maxHeightClassName = "max-h-[200px]",
  className,
  textareaClassName,
  onSelect,
}: ExpandableSelectorProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const isWholeSelectorClickable = readOnly && Boolean(onSelect);
  const maxHeightPx = 200;

  const autoResize = React.useCallback((element: HTMLTextAreaElement) => {
    element.style.height = "0px";
    const nextHeight = element.scrollHeight;
    const clampedHeight = Math.min(nextHeight, maxHeightPx);

    element.style.height = `${clampedHeight}px`;
    element.style.overflowY = nextHeight > maxHeightPx ? "auto" : "hidden";
  }, []);

  function handleSelect() {
    onSelect?.();
  }

  React.useEffect(() => {
    if (textareaRef.current) {
      autoResize(textareaRef.current);
    }
  }, [value, autoResize]);

  return (
    <div
      onClick={isWholeSelectorClickable ? handleSelect : undefined}
      className={cn(
        "flex w-full items-stretch overflow-hidden rounded-2xl border bg-input text-foreground transition",
        selected
          ? "border-primary shadow-sm"
          : "border-border hover:border-muted-foreground/40",
        isWholeSelectorClickable ? "cursor-pointer" : "",
        className
      )}
    >
      <button
        type="button"
        aria-pressed={selected}
        onClick={(event) => {
          event.stopPropagation();
          handleSelect();
        }}
        className="flex w-14 shrink-0 items-center justify-center rounded-l-full"
      >
        <span
          className={cn(
            "block h-4 w-4 rounded-full border transition",
            selected
              ? "border-primary bg-primary"
              : "border-muted-foreground/50 bg-background"
          )}
        />
      </button>

      <div className="min-w-0 flex-1 pr-0.5">
        <textarea
          ref={textareaRef}
          value={value}
          readOnly={readOnly}
          rows={1}
          maxLength={maxLength}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onInput={(event) => autoResize(event.currentTarget)}
          className={cn(
            "block w-full resize-none overflow-y-hidden border-0 bg-transparent px-4 py-3 text-[1.04rem] leading-snug text-foreground outline-none focus:ring-0 focus:outline-none",
            isWholeSelectorClickable ? "cursor-pointer" : "",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName
          )}
        />
      </div>
    </div>
  );
}
