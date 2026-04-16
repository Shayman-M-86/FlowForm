import type { InputHTMLAttributes } from "react";
import "./Input.css";

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: "secondary" | "ghost" | "quiet";
  size?: "sm" | "md" | "xs";
  pill?: boolean;
}

export function Input({
  label,
  hint,
  error,
  variant = "secondary",
  size = "md",
  pill = false,
  id,
  className = "",
  disabled,
  ...props
}: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className={`input-field ${className}`}>
      {label && (
        <label className="input-label" htmlFor={inputId}>
          {label}
        </label>
      )}

      <input
        id={inputId}
        disabled={disabled}
        className={[
          "input-control",
          `input-control--${variant}`,
          `input-control--${size}`,
          pill ? "input-control--pill" : "",
          error ? "input-control--error" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        {...props}
      />

      {hint && !error && <p className="input-hint">{hint}</p>}
      {error && <p className="input-error">{error}</p>}
    </div>
  );
}
