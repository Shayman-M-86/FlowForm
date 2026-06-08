import type { CSSProperties, ReactNode } from "react";

interface BuilderToolbarProps {
  /** Content aligned to the start (left) of the bar. */
  start?: ReactNode;
  /** Content aligned to the end (right) of the bar. */
  end?: ReactNode;
  /**
   * When true (default) the bar sticks to the top of its scroll container.
   * Consumers that render the bar in normal flow can pass `sticky={false}`
   * instead of overriding the sticky positioning with `!important` CSS.
   */
  sticky?: boolean;
  /**
   * Caps how far apart the start/end content can spread. The bar chrome
   * (border, background, blur) still runs full width; only the inner row is
   * constrained and centered. Defaults to the node-page content width.
   */
  maxWidth?: number | string;
  /** Extra classes appended to the outer bar. */
  className?: string;
}

// A touch wider than the node-page content so the toolbar actions can spread
// out a bit more before they stop drifting apart.
const DEFAULT_MAX_WIDTH = 1120;

const BAR_CLASS =
  "box-border flex w-full border-b border-border bg-(--toolbar-bg) backdrop-blur-[14px]";

const INNER_CLASS =
  "mx-auto flex w-full items-center justify-between gap-2.5 px-6 py-[14px] ";

/**
 * The builder's top bar. Owns the container chrome (layout, border, blur,
 * background) so consumers only wire up the actions they want via `start`
 * and `end` — no need to repeat the container styling at each call site.
 */
export function BuilderToolbar({
  start,
  end,
  sticky = true,
  maxWidth = DEFAULT_MAX_WIDTH,
  className,
}: BuilderToolbarProps) {
  const positioning = sticky ? "sticky top-0 z-20" : "relative";
  const innerStyle: CSSProperties = {
    maxWidth: typeof maxWidth === "number" ? `${maxWidth}px` : maxWidth,
  };

  return (
    <div
      className={`node-page__toolbar ${positioning} ${BAR_CLASS}${className ? ` ${className}` : ""}`}
    >
      <div className={`node-page__toolbar-inner ${INNER_CLASS}`} style={innerStyle}>
        <div className="flex items-center gap-2.5">{start}</div>
        <div className="flex items-center gap-2.5">{end}</div>
      </div>
    </div>
  );
}
