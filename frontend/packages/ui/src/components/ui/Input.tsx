import { type InputHTMLAttributes } from "react";
import { cn, useFieldId } from "../../lib/utils";
import { type ControlSize } from "../../lib/sizes";
import {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  getInputControlClassName,
  type InputVariant,
} from "../../lib/formFieldStyles";

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
  const inputId = useFieldId(id, label);

  return (
    <div className={cn(formFieldClass, className)}>
      {label ? (
        <label className={formLabelClass} htmlFor={inputId}>
          {label}
        </label>
      ) : null}

      <input
        id={inputId}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={getInputControlClassName({
          size,
          variant,
          pill,
          error: Boolean(error),
        })}
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
