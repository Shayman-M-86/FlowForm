import { useEffect, useId, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { isBrowser } from "../../lib/utils";
import { Button } from "./Button";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
  height?: number;
  /** Blocks all passive dismissal — no backdrop click, no Escape, no X button. */
  required?: boolean;
}

export function Modal({ open, onClose, title, children, footer, width = 480, height, required = false }: ModalProps) {
  const titleId = useId();

  useEffect(() => {
    if (!open || required) return;

    const handler = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose, open, required]);

  if (!open || !isBrowser) return null;

  return createPortal(
    <div
      className="ui-modal-backdrop"
      onMouseDown={(event) => {
        if (!required && event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="ui-modal-panel"
        style={{ maxWidth: width, ...(height !== undefined && { height }) }}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="ui-modal-header">
          <h2 id={titleId} className="m-0 border-b-0 p-0 text-xl font-semibold leading-8 text-foreground">
            {title}
          </h2>
          {!required && (
            <Button
              type="button"
              variant="icon"
              icon="close"
              onClick={onClose}
              aria-label="Close"
            />
          )}
        </div>
        <div className="ui-modal-body">{children}</div>
        {footer ? <div className="ui-modal-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
