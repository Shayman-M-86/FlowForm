import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
}

export function Modal({ open, onClose, title, children, footer, width = 480 }: ModalProps) {
  const mouseDownInsideRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-100 flex items-center justify-center bg-black/40 p-5 backdrop-blur-md"
      onMouseDown={() => {
        mouseDownInsideRef.current = false;
      }}
      onMouseUp={() => {
        if (!mouseDownInsideRef.current) onClose();
      }}
    >
      <div
        className="flex max-h-[min(90vh,760px)] w-full min-w-0 flex-col rounded-2xl border border-border bg-card shadow-lg"
        style={{ maxWidth: width }}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(e) => {
          mouseDownInsideRef.current = true;
          e.stopPropagation();
        }}
        onMouseUp={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 pb-3.5 pt-4.5">
          <h2 className="text-[1.05rem] font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-sm border border-transparent bg-transparent text-muted-foreground transition-colors hover:border-border hover:bg-muted hover:text-foreground"
          >
            ✕
          </button>
        </div>
        <div className="flex flex-1 flex-col gap-4.5 overflow-y-auto p-5">{children}</div>
        {footer ? (
          <div className="flex justify-end gap-2.5 border-t border-border px-5 pb-5 pt-3.5">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  );
}
