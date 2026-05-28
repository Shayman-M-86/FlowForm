import { type ReactNode } from "react";
import { cn } from "../../lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TableColumn<TRow> {
  key: string;
  header: ReactNode;
  /** Minimum width in px. Hard floor — the column never shrinks below this.
   *  When the container is narrower than the sum of all minWidths, the table
   *  overflows horizontally with a scroll bar. */
  minWidth: number;
  /** Target width in px. When set, the column grows toward this value and
   *  receives available space before regular column growth starts. After target
   *  growth, it can continue growing up to maxWidth. */
  targetWidth?: number;
  /** Maximum width in px. When omitted, the column can keep growing. */
  maxWidth?: number;
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
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

function px(value: number): string {
  return Number.isInteger(value) ? `${value}px` : `${value.toFixed(2)}px`;
}

function trackForColumn<TRow>(
  c: TableColumn<TRow>,
  targetGrowthShare: string,
  regularGrowthShare: string,
): string {
  const minWidth = px(c.minWidth);
  const maxWidth = maxWidthForColumn(c);
  const targetWidth = targetWidthForColumn(c);
  const baseWidth =
    targetWidth === undefined
      ? minWidth
      : `clamp(${minWidth}, calc(${minWidth} + ${targetGrowthShare}), ${px(
        targetWidth,
      )})`;
  const preferredWidth = `calc(${baseWidth} + ${regularGrowthShare})`;

  if (maxWidth === Number.POSITIVE_INFINITY) {
    return `minmax(${minWidth}, ${preferredWidth})`;
  }

  return `clamp(${minWidth}, ${preferredWidth}, ${px(maxWidth)})`;
}

function maxWidthForColumn<TRow>(c: TableColumn<TRow>): number {
  if (c.maxWidth === undefined) {
    return Number.POSITIVE_INFINITY;
  }

  return Math.max(c.minWidth, c.maxWidth);
}

function targetWidthForColumn<TRow>(c: TableColumn<TRow>): number | undefined {
  if (c.targetWidth === undefined) {
    return undefined;
  }

  return Math.min(Math.max(c.minWidth, c.targetWidth), maxWidthForColumn(c));
}

function hasRegularGrowth<TRow>(c: TableColumn<TRow>): boolean {
  return maxWidthForColumn(c) > (targetWidthForColumn(c) ?? c.minWidth);
}

function gridTemplateForColumns<TRow>(columns: TableColumn<TRow>[]): string {
  if (columns.length === 0) {
    return "";
  }

  const minTotalWidth = columns.reduce((sum, c) => sum + c.minWidth, 0);
  const targetGrowthTotal = columns.reduce((sum, c) => {
    const targetWidth = targetWidthForColumn(c);

    if (targetWidth === undefined) {
      return sum;
    }

    return sum + targetWidth - c.minWidth;
  }, 0);
  const targetColumnCount = columns.filter(
    (c) => targetWidthForColumn(c) !== undefined,
  ).length;
  const regularGrowthColumnCount = columns.filter(hasRegularGrowth).length;
  const targetGrowthShare =
    targetColumnCount === 0
      ? "0px"
      : `calc(max(0px, calc(100% - ${px(minTotalWidth)})) / ${targetColumnCount})`;
  const regularGrowthShare =
    regularGrowthColumnCount === 0
      ? "0px"
      : `calc(max(0px, calc(100% - ${px(
        minTotalWidth + targetGrowthTotal,
      )})) / ${regularGrowthColumnCount})`;

  return columns
    .map((c) => trackForColumn(c, targetGrowthShare, regularGrowthShare))
    .join(" ");
}

export function Table<TRow>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  striped = false,
  hideHeader = false,
  emptyState,
  className,
}: TableProps<TRow>) {
  const visibleColumns = columns.filter((c) => c.visible !== false);

  const minTotalWidth = visibleColumns.reduce((sum, c) => sum + c.minWidth, 0);

  const gridTemplateColumns = gridTemplateForColumns(visibleColumns);

  return (
    <div className={cn("ui-table-container", className)}>
      <div
        className="ui-table"
        role="table"
        aria-rowcount={rows.length + 1}
        style={{ minWidth: `${minTotalWidth}px` }}
      >
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
              >
                {col.header}
              </div>
            ))}
          </div>
        )}

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
  );
}
