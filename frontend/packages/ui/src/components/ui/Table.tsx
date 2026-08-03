import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "../../lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

export type TableCellMode = "full" | "compact" | "icon";

export interface TableColumn<TRow> {
  key: string;
  header: ReactNode | ((mode: TableCellMode) => ReactNode);
  /** Hard floor in px. The table scrolls if its required columns cannot fit. */
  minWidth: number;
  /** Preferred starting width in px. Defaults to targetWidth, then minWidth. */
  idealWidth?: number;
  /** Legacy alias for idealWidth. */
  targetWidth?: number;
  /** Maximum width in px. When omitted, the column may keep growing. */
  maxWidth?: number;
  /** Share of extra width received by this column. Defaults to 1. */
  growWeight?: number;
  /** Lower priorities shrink toward minWidth first. Defaults to 0. */
  shrinkPriority?: number;
  /** Lower priorities disappear first after every column reaches minWidth. */
  visibilityPriority?: number;
  /** Allow the resolver to hide this column as a last step before scrolling. */
  hideable?: boolean;
  /** Render the compact cell variant below this resolved width. */
  compactBelow?: number;
  /** Render the icon cell variant below this resolved width. */
  iconOnlyBelow?: number;
  /** When false the column is always hidden. Defaults to true. */
  visible?: boolean;
  /** Render a cell for this column given the row, row index, and resolved mode. */
  cell: (row: TRow, index: number, mode: TableCellMode) => ReactNode;
  /** Optional className for the content wrapper inside cells in this column. */
  cellClassName?: string;
  /** Optional className for the content wrapper inside this header cell. */
  headerClassName?: string;
}

export interface ResolvedTableColumn<TRow> {
  definition: TableColumn<TRow>;
  width: number;
  mode: TableCellMode;
}

export interface ResolvedTableLayout<TRow> {
  columns: ResolvedTableColumn<TRow>[];
  hiddenColumns: TableColumn<TRow>[];
  totalWidth: number;
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

type WorkingColumn<TRow> = {
  definition: TableColumn<TRow>;
  sourceIndex: number;
  minWidth: number;
  idealWidth: number;
  maxWidth: number;
  width: number;
};

// ── Layout resolver ───────────────────────────────────────────────────────────

function finiteWidth(value: number | undefined, fallback: number): number {
  return value === undefined || !Number.isFinite(value)
    ? fallback
    : Math.max(0, value);
}

function workingColumn<TRow>(
  definition: TableColumn<TRow>,
  sourceIndex: number,
): WorkingColumn<TRow> {
  const minWidth = finiteWidth(definition.minWidth, 0);
  const maxWidth =
    definition.maxWidth === undefined
      ? Number.POSITIVE_INFINITY
      : Math.max(minWidth, finiteWidth(definition.maxWidth, minWidth));
  const preferredWidth =
    definition.idealWidth ?? definition.targetWidth ?? minWidth;
  const idealWidth = Math.min(
    Math.max(minWidth, finiteWidth(preferredWidth, minWidth)),
    maxWidth,
  );

  return {
    definition,
    sourceIndex,
    minWidth,
    idealWidth,
    maxWidth,
    width: idealWidth,
  };
}

function totalWidth<TRow>(columns: WorkingColumn<TRow>[]): number {
  return columns.reduce((sum, column) => sum + column.width, 0);
}

function shrinkColumns<TRow>(
  columns: WorkingColumn<TRow>[],
  deficit: number,
): void {
  const priorities = [
    ...new Set(
      columns.map((column) => column.definition.shrinkPriority ?? 0),
    ),
  ].sort((a, b) => a - b);

  let remaining = deficit;

  for (const priority of priorities) {
    if (remaining <= 0) break;

    const group = columns.filter(
      (column) =>
        (column.definition.shrinkPriority ?? 0) === priority &&
        column.width > column.minWidth,
    );
    const capacity = group.reduce(
      (sum, column) => sum + column.width - column.minWidth,
      0,
    );
    if (capacity <= 0) continue;

    const reduction = Math.min(remaining, capacity);
    let applied = 0;

    group.forEach((column, index) => {
      const columnCapacity = column.width - column.minWidth;
      const share =
        index === group.length - 1
          ? reduction - applied
          : Math.min(reduction - applied, reduction * (columnCapacity / capacity));
      column.width = Math.max(column.minWidth, column.width - share);
      applied += share;
    });

    remaining -= reduction;
  }
}

function growColumnsTo<TRow>(
  columns: WorkingColumn<TRow>[],
  extraWidth: number,
  limitFor: (column: WorkingColumn<TRow>) => number,
): number {
  let remaining = extraWidth;
  let growable = columns.filter((column) => {
    const weight = Math.max(0, column.definition.growWeight ?? 1);
    return weight > 0 && column.width < limitFor(column);
  });

  while (remaining > 0.01 && growable.length > 0) {
    const totalWeight = growable.reduce(
      (sum, column) => sum + Math.max(0, column.definition.growWeight ?? 1),
      0,
    );
    if (totalWeight <= 0) break;

    let distributed = 0;

    for (const column of growable) {
      const weight = Math.max(0, column.definition.growWeight ?? 1);
      const capacity = limitFor(column) - column.width;
      const share = Math.min(capacity, remaining * (weight / totalWeight));
      column.width += share;
      distributed += share;
    }

    if (distributed <= 0.01) break;
    remaining -= distributed;
    growable = growable.filter(
      (column) => column.width + 0.01 < limitFor(column),
    );
  }

  return remaining;
}

function modeForColumn<TRow>(column: WorkingColumn<TRow>): TableCellMode {
  const { iconOnlyBelow, compactBelow } = column.definition;

  if (iconOnlyBelow !== undefined && column.width < iconOnlyBelow) {
    return "icon";
  }
  if (compactBelow !== undefined && column.width < compactBelow) {
    return "compact";
  }
  return "full";
}

/**
 * Resolve a predictable column layout for the measured table container.
 *
 * Columns start at ideal width, shrink by priority, become compact as their
 * resolved width crosses policy thresholds, hide only when explicitly allowed,
 * and use horizontal scrolling when required columns still cannot fit.
 */
export function resolveTableLayout<TRow>(
  definitions: TableColumn<TRow>[],
  containerWidth?: number,
): ResolvedTableLayout<TRow> {
  const allVisible = definitions
    .filter((column) => column.visible !== false)
    .map(workingColumn);
  const hiddenColumns: TableColumn<TRow>[] = definitions.filter(
    (column) => column.visible === false,
  );
  const availableWidth =
    containerWidth !== undefined &&
    Number.isFinite(containerWidth) &&
    containerWidth > 0
      ? containerWidth
      : undefined;

  if (availableWidth !== undefined) {
    const idealTotal = totalWidth(allVisible);

    if (idealTotal > availableWidth) {
      shrinkColumns(allVisible, idealTotal - availableWidth);
    }

    if (totalWidth(allVisible) > availableWidth) {
      const hideable = allVisible
        .filter((column) => column.definition.hideable)
        .sort((a, b) => {
          const priorityDifference =
            (a.definition.visibilityPriority ?? 0) -
            (b.definition.visibilityPriority ?? 0);
          return priorityDifference || a.sourceIndex - b.sourceIndex;
        });

      for (const column of hideable) {
        if (totalWidth(allVisible) <= availableWidth) break;
        const index = allVisible.indexOf(column);
        if (index === -1) continue;
        allVisible.splice(index, 1);
        hiddenColumns.push(column.definition);
      }
    }

    let extraWidth = Math.max(0, availableWidth - totalWidth(allVisible));
    extraWidth = growColumnsTo(
      allVisible,
      extraWidth,
      (column) => column.idealWidth,
    );
    growColumnsTo(allVisible, extraWidth, (column) => column.maxWidth);
  }

  const columns = allVisible
    .sort((a, b) => a.sourceIndex - b.sourceIndex)
    .map((column) => ({
      definition: column.definition,
      width: Math.round(column.width * 100) / 100,
      mode: modeForColumn(column),
    }));

  return {
    columns,
    hiddenColumns,
    totalWidth:
      Math.round(
        columns.reduce((sum, column) => sum + column.width, 0) * 100,
      ) / 100,
  };
}

// ── Component ─────────────────────────────────────────────────────────────────

function headerContent<TRow>(
  column: ResolvedTableColumn<TRow>,
): ReactNode {
  return typeof column.definition.header === "function"
    ? column.definition.header(column.mode)
    : column.definition.header;
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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number>();

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateWidth = () => {
      const width = element.clientWidth;
      if (width > 0) {
        setContainerWidth((current) =>
          current !== undefined && Math.abs(current - width) < 0.5
            ? current
            : width,
        );
      }
    };

    updateWidth();

    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(updateWidth);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const layout = useMemo(
    () => resolveTableLayout(columns, containerWidth),
    [columns, containerWidth],
  );

  return (
    <div ref={containerRef} className={cn("ui-table-container", className)}>
      <table
        className="ui-table"
        style={{ width: `${layout.totalWidth}px` }}
      >
        <colgroup>
          {layout.columns.map((column) => (
            <col
              key={column.definition.key}
              style={{ width: `${column.width}px` }}
            />
          ))}
        </colgroup>

        {!hideHeader && (
          <thead className="ui-table-header">
            <tr>
              {layout.columns.map((column) => (
                <th
                  key={column.definition.key}
                  scope="col"
                  className="ui-table-th"
                >
                  <div
                    className={cn(
                      "ui-table-th-content",
                      column.definition.headerClassName,
                    )}
                  >
                    {headerContent(column)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
        )}

        <tbody className="ui-table-body">
          {rows.length === 0 ? (
            <tr className="ui-table-empty">
              <td colSpan={Math.max(1, layout.columns.length)}>
                <div>
                  {emptyState ?? (
                    <p className="text-sm text-muted-foreground">No results.</p>
                  )}
                </div>
              </td>
            </tr>
          ) : (
            rows.map((row, rowIndex) => {
              const key = getRowKey ? getRowKey(row, rowIndex) : rowIndex;
              return (
                <tr
                  key={key}
                  className={cn(
                    "ui-table-row",
                    striped && "ui-table-row--striped",
                    onRowClick && "ui-table-row--clickable",
                  )}
                  onClick={
                    onRowClick ? () => onRowClick(row, rowIndex) : undefined
                  }
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={
                    onRowClick
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onRowClick(row, rowIndex);
                          }
                        }
                      : undefined
                  }
                >
                  {layout.columns.map((column) => (
                    <td
                      key={column.definition.key}
                      className="ui-table-td"
                    >
                      <div
                        className={cn(
                          "ui-table-cell-content",
                          column.definition.cellClassName,
                        )}
                      >
                        {column.definition.cell(row, rowIndex, column.mode)}
                      </div>
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
