import "./Toggle.css";

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  hint?: string;
}

export function Toggle({ label, checked, onChange, disabled, hint }: ToggleProps) {
  return (
    <div className="toggle-field">
      <label className="toggle-label">
        <input
          type="checkbox"
          className="toggle-input"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="toggle-track" aria-hidden="true">
          <span className="toggle-thumb" />
        </span>
        <span className="toggle-text">{label}</span>
      </label>
      {hint && <p className="toggle-hint">{hint}</p>}
    </div>
  );
}
