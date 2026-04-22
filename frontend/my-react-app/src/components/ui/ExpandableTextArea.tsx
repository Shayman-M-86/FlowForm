import * as React from "react";
import { cn } from "../../lib/utils";

type ExpandableTextAreaProps = {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  placeholder?: string;
  maxLength?: number;
  minHeightClassName?: string;
  maxHeightClassName?: string;
  maxHeightPx?: number;
  className?: string;
  textareaClassName?: string;
};

export function ExpandableTextArea({
  value,
  onChange,
  readOnly = false,
  placeholder = "Type here...",
  maxLength,
  minHeightClassName = "min-h-[46px]",
  maxHeightClassName = "max-h-[200px]",
  maxHeightPx = 200,
  className,
  textareaClassName,
}: ExpandableTextAreaProps) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  const autoResize = React.useCallback((element: HTMLTextAreaElement) => {
    element.style.height = "0px";
    const nextHeight = element.scrollHeight;
    const clampedHeight = Math.min(nextHeight, maxHeightPx);
    element.style.height = `${clampedHeight}px`;
    element.style.overflowY = nextHeight > maxHeightPx ? "auto" : "hidden";
  }, [maxHeightPx]);

  React.useEffect(() => {
    if (textareaRef.current) {
      autoResize(textareaRef.current);
    }
  }, [value, autoResize]);

  return (
    <div
      className={cn(
        "flex w-full items-stretch overflow-hidden rounded-2xl border bg-input text-foreground transition",
        "border-border hover:border-muted-foreground/40",
        className
      )}
    >
      <div className="min-w-0 flex-1 ">
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
            "block w-full resize-none overflow-y-hidden border-0 bg-transparent px-3 py-2 text-[1.04rem] leading-snug text-foreground outline-none focus:ring-0 focus:outline-none",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName
          )}
        />
      </div>
    </div>
  );
}
