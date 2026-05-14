import {
  type ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { cn } from "../../lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TableColumn<TRow> {
  key: string;
  header: ReactNode;
  /** Minimum width in px. Columns stretch equally beyond this to fill the table.
   *  When the container is narrower than the sum of all minWidths, the table
   *  scales down proportionally. */
  minWidth: number;
  /** Preferred column width in px. The column can shrink to minWidth when needed. */
  width?: number;
  /** When false the column is completely hidden. Defaults to true. */
  visible?: boolean;
  /** Render a cell for this column given the row data and its index. */
  cell: (row: TRow, index: number) => ReactNode;
  /** Optional className for cells in this column. */
  cellClassName?: string;
  /** Optional className for the header cell of this column. */
  headerClassName?: string;
}

export interface TableProps<TRow> {
  columns: TableColumn<TRow>[];
  rows: TRow[];
  /** Key extractor for rows. Defaults to the row index. */
  getRowKey?: (row: TRow, index: number) => string | number;
  /** Called when a row is clicked. */
  onRowClick?: (row: TRow, index: number) => void;
  /** Alternate even rows with a subtle background tint. */
  striped?: boolean;
  /** Hide the header row. */
  hideHeader?: boolean;
  /** Shown when rows is empty. */
  emptyState?: ReactNode;
  /** Use "content" to size the table to preferred column widths instead of filling its container. */
  fit?: "container" | "content";
  /** Maximum table width. Accepts px when number, or any CSS width string. */
  maxWidth?: number | string;
  className?: string;
}

// ── Hook: proportional scale-to-fit ──────────────────────────────────────────

function useScaleToFit(minTotalWidth: number) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scalerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [scaledHeight, setScaledHeight] = useState<number | undefined>(undefined);

  const measure = useCallback(() => {
    const container = containerRef.current;
    const scaler = scalerRef.current;
    if (!container || minTotalWidth === 0) return;

    const available = container.getBoundingClientRect().width;
    const nextScale = available >= minTotalWidth ? 1 : available / minTotalWidth;
    setScale(nextScale);

    // When scaled down, compensate the container height so it doesn't collapse.
    // We read the scaler's natural (pre-transform) height and multiply by scale.
    if (nextScale < 1 && scaler) {
      const naturalHeight = scaler.scrollHeight;
      setScaledHeight(naturalHeight * nextScale);
    } else {
      setScaledHeight(undefined);
    }
  }, [minTotalWidth]);

  useLayoutEffect(() => {
    measure();
  }, [measure]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [measure]);

  return { containerRef, scalerRef, scale, scaledHeight };
}

// ── Component ─────────────────────────────────────────────────────────────────

export function Table<TRow>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  striped = false,
  hideHeader = false,
  emptyState,
  fit = "container",
  maxWidth,
  className,
}: TableProps<TRow>) {
  const visibleColumns = columns.filter((c) => c.visible !== false);

  const minTotalWidth = visibleColumns.reduce(
    (sum, c) => sum + c.minWidth,
    0,
  );

  const { containerRef, scalerRef, scale, scaledHeight } = useScaleToFit(minTotalWidth);
  const preferredTotalWidth = visibleColumns.reduce(
    (sum, c) => sum + (c.width ?? c.minWidth),
    0,
  );

  // Preferred-width columns can shrink to minWidth. Other columns get at least minWidth, then stretch equally.
  const gridTemplateColumns = visibleColumns
    .map((c) =>
      c.width !== undefined
        ? `minmax(${c.minWidth}px, ${Math.max(c.width, c.minWidth)}px)`
        : `minmax(${c.minWidth}px, 1fr)`,
    )
    .join(" ");

  // naturalWidth is still needed for the scale-to-fit scaler width.
  const naturalWidth = minTotalWidth;
  const resolvedMaxWidth = typeof maxWidth === "number" ? `${maxWidth}px` : maxWidth;

  return (
    <div
      ref={containerRef}
      className={cn(
        "ui-table-container",
        fit === "content" && "w-fit! max-w-full",
        className,
      )}
      style={{
        ...(scaledHeight !== undefined && { height: `${scaledHeight}px` }),
        ...(fit === "content" && { width: `${preferredTotalWidth}px` }),
        ...(resolvedMaxWidth !== undefined && { maxWidth: resolvedMaxWidth }),
      }}
    >
      <div
        ref={scalerRef}
        className="ui-table-scaler"
        style={
          scale < 1
            ? {
                width: `${naturalWidth}px`,
                transformOrigin: "top left",
                transform: `scale(${scale})`,
              }
            : { width: "100%" }
        }
      >
        <div className="ui-table" role="table" aria-rowcount={rows.length + 1}>
          {/* Header */}
          {!hideHeader && (
            <div
              className="ui-table-header"
              role="row"
              style={{ gridTemplateColumns }}
            >
              {visibleColumns.map((col) => (
                <div
                  key={col.key}
                  role="columnheader"
                  className={cn("ui-table-th", col.headerClassName)}
                  style={{ minWidth: `${col.minWidth}px` }}
                >
                  {col.header}
                </div>
              ))}
            </div>
          )}

          {/* Body */}
          <div className="ui-table-body" role="rowgroup">
            {rows.length === 0 ? (
              <div className="ui-table-empty" role="row">
                <div role="cell">
                  {emptyState ?? (
                    <p className="text-sm text-muted-foreground">No results.</p>
                  )}
                </div>
              </div>
            ) : (
              rows.map((row, rowIndex) => {
                const key = getRowKey ? getRowKey(row, rowIndex) : rowIndex;
                return (
                  <div
                    key={key}
                    role="row"
                    aria-rowindex={rowIndex + 2}
                    className={cn(
                      "ui-table-row",
                      striped && "ui-table-row--striped",
                      onRowClick && "ui-table-row--clickable",
                    )}
                    style={{ gridTemplateColumns }}
                    onClick={onRowClick ? () => onRowClick(row, rowIndex) : undefined}
                    tabIndex={onRowClick ? 0 : undefined}
                    onKeyDown={
                      onRowClick
                        ? (e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              onRowClick(row, rowIndex);
                            }
                          }
                        : undefined
                    }
                  >
                    {visibleColumns.map((col) => (
                      <div
                        key={col.key}
                        role="cell"
                        className={cn("ui-table-td", col.cellClassName)}
                        style={{ minWidth: `${col.minWidth}px` }}
                      >
                        {col.cell(row, rowIndex)}
                      </div>
                    ))}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
