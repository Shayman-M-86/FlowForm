import type { InputHTMLAttributes } from "react";
import type { ControlSize } from "./uiSizes";
import {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  getInputControlClassName,
  type InputVariant,
} from "./formFieldStyles";

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  hint?: string;
  error?: string;
  variant?: InputVariant;
  size?: ControlSize;
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
  const inputId = id ?? label?.toLowerCase().trim().replace(/\s+/g, "-");

  const controlClassName = getInputControlClassName({
    size,
    variant,
    pill,
    error: Boolean(error),
  });

  return (
    <div className={[formFieldClass, className].filter(Boolean).join(" ")}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <input
        id={inputId}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={controlClassName}
        {...props}
      />

      {error ? (
        <p className={formErrorClass}>{error}</p>
      ) : hint ? (
        <p className={formHintClass}>{hint}</p>
      ) : null}
    </div>
  );
}