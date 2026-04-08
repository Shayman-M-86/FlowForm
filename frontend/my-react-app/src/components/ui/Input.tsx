import type { InputHTMLAttributes } from "react";
import "./Input.css";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export function Input({ label, hint, error, id, className = "", ...props }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={`input-field ${className}`}>
      {label && <label className="input-label" htmlFor={inputId}>{label}</label>}
      <input id={inputId} className={`input-control ${error ? "input-control--error" : ""}`} {...props} />
      {hint && !error && <p className="input-hint">{hint}</p>}
      {error && <p className="input-error">{error}</p>}
    </div>
  );
}
