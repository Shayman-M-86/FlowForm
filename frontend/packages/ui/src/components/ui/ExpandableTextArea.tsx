import { cn, useAutoResizingTextarea } from "../../lib/utils";

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
  const { ref, resize } = useAutoResizingTextarea({ value, maxHeight: maxHeightPx });

  return (
    <div className={cn("ui-expandable-shell ui-expandable-shell--interactive", className)}>
      <div className="min-w-0 flex-1">
        <textarea
          ref={ref}
          value={value}
          readOnly={readOnly}
          rows={1}
          maxLength={maxLength}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          onInput={(event) => resize(event.currentTarget)}
          className={cn(
            "ui-expandable-textarea ui-expandable-textarea--compact",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName,
          )}
        />
      </div>
    </div>
  );
}
