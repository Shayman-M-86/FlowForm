import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "quiet" | "dark";
  size?: "xs" | "sm" | "md";
  pill?: boolean;
  borderStyle?: "solid" | "dotted";
  children: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  pill = false,
  borderStyle = "solid",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={[
        "btn",
        `btn--${variant}`,
        `btn--${size}`,
        `btn--border-${borderStyle}`,
        pill ? "btn--pill" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
