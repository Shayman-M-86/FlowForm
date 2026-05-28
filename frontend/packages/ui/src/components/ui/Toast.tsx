import { useEffect, useRef, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "../../lib/utils";
import { Button } from "./Button";

export type ToastVariant = "success" | "error" | "warning";

interface ToastProps {
  variant: ToastVariant;
  children: ReactNode;
  className?: string;
  onClose?: () => void;
}

const toastVariantClasses: Record<ToastVariant, string> = {
  success: "ui-badge-success",
  error: "ui-badge-danger",
  warning: "ui-badge-warning",
};

const toastIcons: Record<ToastVariant, ReactNode> = {
  success: <CheckCircle2 size={20} aria-hidden="true" />,
  error: <XCircle size={20} aria-hidden="true" />,
  warning: <AlertTriangle size={20} aria-hidden="true" />,
};

const toastRoles: Record<ToastVariant, "status" | "alert"> = {
  success: "status",
  error: "alert",
  warning: "alert",
};

const AUTO_DISMISS_MS = 20_000;

export function Toast({ variant, children, className, onClose }: ToastProps) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!onCloseRef.current) return;
    const timer = setTimeout(() => onCloseRef.current?.(), AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      role={toastRoles[variant]}
      className={cn(
        "ui-badge inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
        toastVariantClasses[variant],
        className,
      )}
    >
      <span className="mt-0.5 shrink-0">{toastIcons[variant]}</span>
      <span className="flex-1 whitespace-normal leading-snug mt-0.5">{children}</span>
      {onClose && (
        <Button
          variant="icon"
          size="xxs"
          icon="close"
          bare
          aria-label="Dismiss"
          onClick={onClose}
        />
      )}
    </div>
  );
}
