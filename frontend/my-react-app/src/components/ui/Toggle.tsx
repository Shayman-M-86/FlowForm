import {
  formFieldClass,
  formHintClass,
} from "./formFieldStyles";

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
      <label
        className={[
          "flex cursor-pointer select-none items-center gap-3",
          disabled ? "cursor-not-allowed opacity-60" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <input
          type="checkbox"
          className="peer sr-only"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span
          aria-hidden="true"
          className={[
            "relative h-6 w-[42px] flex-shrink-0 rounded-full border transition-colors",
            checked ? "border-accent bg-accent/30" : "border-border bg-input",
            "peer-focus-visible:ring-2 peer-focus-visible:ring-accent/50",
          ].join(" ")}
        >
          <span
            className={[
              "absolute left-0.5 top-0.5 h-[18px] w-[18px] rounded-full transition-all",
              checked ? "translate-x-4.5 bg-accent" : "bg-muted-foreground",
            ].join(" ")}
          />
        </span>
        <span className="text-sm text-foreground">{label}</span>
      </label>
      {hint ? <p className={[formHintClass, "ml-[54px]"].join(" ")}>{hint}</p> : null}
    </div>
  );
}
