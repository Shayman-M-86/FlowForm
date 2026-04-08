import type { SelectHTMLAttributes } from "react";
import "./Select.css";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  hint?: string;
}

export function Select({ label, options, hint, id, className = "", ...props }: SelectProps) {
  const selectId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={`select-field ${className}`}>
      {label && <label className="select-label" htmlFor={selectId}>{label}</label>}
      <select id={selectId} className="select-control" {...props}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {hint && <p className="select-hint">{hint}</p>}
    </div>
  );
}
