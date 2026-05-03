import { cn, useAutoResizingTextarea } from "../../lib/utils";

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

const expandableSelectionButtonClass = "ui-expandable-selection-button";
const expandableIndicatorClass = "ui-expandable-indicator";

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
  const { ref, resize } = useAutoResizingTextarea({ value, maxHeight: 200 });
  const isWholeSelectorClickable = readOnly && Boolean(onSelect);

  return (
    <div
      onClick={isWholeSelectorClickable ? onSelect : undefined}
      className={cn(
        "ui-expandable-shell ui-expandable-shell--interactive",
        selected && "ui-expandable-shell--selected",
        isWholeSelectorClickable && "cursor-pointer",
        className,
      )}
    >
      <button
        type="button"
        aria-pressed={selected}
        onClick={(event) => {
          event.stopPropagation();
          onSelect?.();
        }}
        className={expandableSelectionButtonClass}
      >
        <span
          className={cn(
            expandableIndicatorClass,
            selected ? "border-primary bg-primary" : "border-muted-foreground/50 bg-background",
          )}
        />
      </button>

      <div className="min-w-0 flex-1 pr-0.5">
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
            "ui-expandable-textarea",
            isWholeSelectorClickable && "cursor-pointer",
            minHeightClassName,
            maxHeightClassName,
            textareaClassName,
          )}
        />
      </div>
    </div>
  );
}
