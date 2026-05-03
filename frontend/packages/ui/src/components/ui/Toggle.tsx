import { cn } from "../../lib/utils";
import { formFieldClass, formHintClass } from "../../lib/formFieldStyles";

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
}

export function Toggle({ label, checked, onChange, disabled, hint }: ToggleProps) {
  return (
    <div className={formFieldClass}>
      <label className={cn("ui-toggle-label", disabled && "cursor-not-allowed opacity-60")}>
        <input
          type="checkbox"
          className="ui-toggle-input"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />

        <span
          aria-hidden="true"
          className={cn(
            "ui-toggle-track",
            checked ? "border-accent bg-accent/30" : "border-border bg-input",
          )}
        >
          <span
            className={cn(
              "ui-toggle-thumb",
              checked ? "translate-x-5 bg-accent" : "bg-muted-foreground",
            )}
          />
        </span>

        <span className="text-sm text-foreground">{label}</span>
      </label>

      {hint ? <p className={cn(formHintClass, "ml-54px")}>{hint}</p> : null}
    </div>
  );
}
