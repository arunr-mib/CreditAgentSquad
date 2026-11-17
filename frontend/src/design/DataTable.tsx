import { createSortedRowModel, rowSortingFeature, tableFeatures, useTable, type ColumnDef, type RowData, type SortingState } from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';
import { useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { cx } from '@/lib/cx';

const features = tableFeatures({ rowSortingFeature, sortedRowModel: createSortedRowModel() });
type Features = typeof features;

type SortValue = string | number | null;

export interface DataColumn<T> {
  id: string;
  header: string;
  /** Extra words for the column head, for example the unit: "USD thousands". */
  headerNote?: string;
  cell: (row: T) => ReactNode;
  /** Makes the column sortable. Null sorts last in both directions. */
  sortValue?: (row: T) => SortValue;
  /** Figures are right-aligned; everything else is left-aligned. */
  align?: 'left' | 'right';
  /** Preferred CSS width, for example "120px". Columns grow to fit their content; nothing is clipped. */
  width?: string;
  /** The first column usually names the row: render it as a row header. */
  rowHeader?: boolean;
  /** Let long text wrap onto a second line. Nothing is ever clipped; other columns do not wrap. */
  wrap?: boolean;
}

export interface DataTableProps<T> {
  /** Accessible name of the table. */
  caption: string;
  data: T[];
  columns: DataColumn<T>[];
  getRowId: (row: T) => string;
  initialSort?: { id: string; desc?: boolean };
  /** Called on click, Enter or Space. Rows become focusable when set. */
  onRowActivate?: (row: T) => void;
  selectedRowId?: string | null;
  /** Distance from the top of the scrolling area at which the header sticks (CSS length). */
  stickyTop?: string;
  /** 34 px rows by default; 'compact' is 32 px. */
  density?: 'dense' | 'compact';
  empty?: ReactNode;
  className?: string;
}

function compareValues(a: SortValue, b: SortValue): number {
  if (a === b) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), 'en', { numeric: true });
}

/**
 * Dense, sortable table. Sticky header, 34 px rows, right-aligned figures,
 * and keyboard row focus: Up, Down, Home and End move; Enter or Space activates.
 */
export function DataTable<T extends RowData>({
  caption,
  data,
  columns,
  getRowId,
  initialSort,
  onRowActivate,
  selectedRowId,
  stickyTop = '0px',
  density = 'dense',
  empty,
  className,
}: DataTableProps<T>) {
  const columnDefs = useMemo<Array<ColumnDef<Features, T, unknown>>>(
    () =>
      columns.map((column) => ({
        id: column.id,
        header: column.header,
        accessorFn: (row: T) => (column.sortValue ? column.sortValue(row) : null),
        enableSorting: Boolean(column.sortValue),
        sortUndefined: 'last' as const,
        sortDescFirst: false,
        sortFn: (rowA, rowB, columnId) => compareValues(rowA.getValue(columnId) as SortValue, rowB.getValue(columnId) as SortValue),
      })),
    [columns],
  );

  const [sorting, setSorting] = useState<SortingState>(initialSort ? [{ id: initialSort.id, desc: initialSort.desc ?? false }] : []);

  const table = useTable({
    features,
    data,
    columns: columnDefs,
    getRowId,
    state: { sorting },
    onSortingChange: setSorting,
    enableSortingRemoval: true,
  });

  const byId = useMemo(() => new Map(columns.map((column) => [column.id, column])), [columns]);
  const rows = table.getRowModel().rows;
  const bodyRef = useRef<HTMLTableSectionElement>(null);
  const [focusIndex, setFocusIndex] = useState(0);
  const interactive = Boolean(onRowActivate);
  const rowHeight = density === 'dense' ? 'h-[34px]' : 'h-8';
  const tabStop = Math.min(focusIndex, Math.max(rows.length - 1, 0));

  function focusRow(index: number) {
    const clamped = Math.max(0, Math.min(rows.length - 1, index));
    setFocusIndex(clamped);
    bodyRef.current?.querySelectorAll<HTMLTableRowElement>('tr[data-row]')[clamped]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTableSectionElement>) {
    if (!interactive || !(event.target instanceof HTMLTableRowElement)) return;
    const index = Number(event.target.dataset.index);
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        focusRow(index + 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        focusRow(index - 1);
        break;
      case 'Home':
        event.preventDefault();
        focusRow(0);
        break;
      case 'End':
        event.preventDefault();
        focusRow(rows.length - 1);
        break;
      case 'Enter':
      case ' ': {
        event.preventDefault();
        const row = rows[index];
        if (row) onRowActivate?.(row.original);
        break;
      }
    }
  }

  return (
    <div className={cx('rounded-md border border-hairline-strong bg-surface', className)}>
      <table className="w-full border-separate border-spacing-0 text-body">
        <caption className="sr-only">{caption}</caption>
        <colgroup>
          {columns.map((column) => (
            <col key={column.id} style={column.width ? { width: column.width } : undefined} />
          ))}
        </colgroup>
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header, index) => {
                const column = byId.get(header.column.id);
                const sorted = header.column.getIsSorted();
                const canSort = header.column.getCanSort();
                const right = column?.align === 'right';
                const label = (
                  <>
                    {column?.header}
                    {column?.headerNote ? <span className="font-medium tracking-normal normal-case text-ink-500"> {column.headerNote}</span> : null}
                  </>
                );
                return (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={canSort ? (sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none') : undefined}
                    style={{ top: stickyTop }}
                    className={cx(
                      'eyebrow sticky z-10 h-8 border-b border-ink bg-surface px-2 whitespace-nowrap first:pl-4 last:pr-4',
                      right ? 'text-right' : 'text-left',
                      index === 0 && 'rounded-tl-md',
                      index === group.headers.length - 1 && 'rounded-tr-md',
                    )}
                  >
                    {canSort ? (
                      <button
                        type="button"
                        onClick={header.column.getToggleSortingHandler()}
                        className={cx(
                          'eyebrow -mx-1 inline-flex h-6 items-center gap-1 rounded-xs px-1 t-colors hover:text-ink',
                          right && 'flex-row-reverse',
                          sorted && 'text-ink',
                        )}
                      >
                        {label}
                        {sorted === 'asc' ? (
                          <ArrowUp size={11} aria-hidden />
                        ) : sorted === 'desc' ? (
                          <ArrowDown size={11} aria-hidden />
                        ) : (
                          <ChevronsUpDown size={11} aria-hidden className="text-ink-400" />
                        )}
                      </button>
                    ) : (
                      label
                    )}
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        {/* Rows take focus so the queue can be worked from the keyboard; the handler ignores events from cell controls. */}
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
        <tbody ref={bodyRef} onKeyDown={onKeyDown}>
          {rows.map((row, index) => {
            const selected = selectedRowId === row.id;
            const last = index === rows.length - 1;
            return (
              <tr
                key={row.id}
                data-row
                data-index={index}
                aria-selected={interactive ? selected : undefined}
                tabIndex={interactive ? (index === tabStop ? 0 : -1) : undefined}
                onClick={interactive ? () => onRowActivate?.(row.original) : undefined}
                onFocus={interactive ? () => setFocusIndex(index) : undefined}
                className={cx(
                  'group/row t-colors',
                  interactive && 'cursor-pointer focus-visible:-outline-offset-2',
                  selected ? 'bg-cobalt-bg' : interactive && 'hover:bg-hover',
                )}
              >
                {columns.map((column, columnIndex) => {
                  const Cell = column.rowHeader ? 'th' : 'td';
                  return (
                    <Cell
                      key={column.id}
                      scope={column.rowHeader ? 'row' : undefined}
                      className={cx(
                        rowHeight,
                        'px-2 font-regular first:pl-4 last:pr-4',
                        column.wrap ? 'py-1.5 text-pretty' : 'py-0 whitespace-nowrap',
                        column.align === 'right' ? 'text-right' : 'text-left',
                        !last && 'border-b border-hairline',
                        last && columnIndex === 0 && 'rounded-bl-md',
                        last && columnIndex === columns.length - 1 && 'rounded-br-md',
                      )}
                    >
                      {column.cell(row.original)}
                    </Cell>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      {rows.length === 0 ? empty : null}
    </div>
  );
}
