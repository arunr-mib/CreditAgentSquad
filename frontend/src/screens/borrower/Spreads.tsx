import { Link, useNavigate, useSearch } from '@tanstack/react-router';
import { Fragment, useMemo, useState, type KeyboardEvent } from 'react';
import { useFactsById, useSpread } from '@/api/hooks';
import type { FactSummary, Spread, SpreadLineApi } from '@/api/schema';
import { formatDate, Select } from '@/design';
import { quarterLabel } from '@/domain/labels';
import { cx } from '@/lib/cx';
import { useWorkspaceDrawer } from '@/drawer/context';
import { useSource } from '@/source/context';
import { Absent, FactFigure, ProvenanceLegend } from '@/source/figures';
import { EmptyCard, Load, SectionHead } from '../parts';
import { useCurrentBorrower } from './BorrowerLayout';

const STATEMENTS: Array<{ id: string; title: string; basis: string }> = [
  { id: 'is', title: 'Income statement', basis: 'fiscal year to date' },
  { id: 'bs', title: 'Balance sheet', basis: 'at the period end' },
  { id: 'cf', title: 'Cash flow', basis: 'fiscal year to date' },
  { id: 'sup', title: 'Supplemental', basis: 'from the notes' },
];
/** Totals carry a double rule below, as on a statement. */
const TOTALS = new Set(['is.net_income', 'bs.total_assets', 'bs.total_liabilities_and_equity', 'cf.net_change_in_cash']);

type Period = Spread['periods'][number];

function periodHead(period: Period): { top: string; bottom: string } {
  return {
    top: period.months === 12 ? `FY ${period.period_end.slice(0, 4)}` : quarterLabel(period.period_end),
    bottom: period.months === 12 ? '12 months' : `${period.months} months`,
  };
}

function Grid({ spread, periods, scroll }: { spread: Spread; periods: Period[]; scroll: boolean }) {
  const source = useSource();
  const [tabStopId, setTabStopId] = useState<string | null>(null);

  const ids = useMemo(() => spread.lines.flatMap((line) => periods.map((period) => line.cells[period.period_end]?.fact_id)), [spread, periods]);
  // The grid response carries each cell's value and kind; labels come with the facts in bulk.
  const facts = useFactsById(ids);

  const cellFact = (line: SpreadLineApi, period: Period): FactSummary | undefined => {
    const cell = line.cells[period.period_end];
    if (!cell) return undefined;
    return (
      facts.data?.[cell.fact_id] ?? {
        id: cell.fact_id,
        key: line.key,
        label: line.label,
        value: cell.value,
        unit: 'usd',
        kind: cell.kind,
        status: cell.status,
        period_end: period.period_end,
        months: line.statement === 'bs' ? 0 : period.months,
        borrower_id: '',
        document_id: null,
        page: null,
        calc_run_id: null,
      }
    );
  };

  const firstId = spread.lines.map((line) => line.cells[periods[periods.length - 1]?.period_end ?? '']?.fact_id).find(Boolean) ?? null;
  const tabStop = tabStopId ?? (source.current?.type === 'fact' ? source.current.id : firstId);

  function onKeyDown(event: KeyboardEvent<HTMLTableSectionElement>) {
    const button = event.target instanceof HTMLElement ? event.target.closest<HTMLButtonElement>('button[data-fact]') : null;
    const cell = button?.closest('td');
    const row = cell?.closest('tr');
    if (!button || !cell || !row) return;
    const column = cell.cellIndex;
    const inRow = (candidate: Element | null, step: 1 | -1): HTMLButtonElement | null => {
      for (let next = candidate; next; next = step === 1 ? next.nextElementSibling : next.previousElementSibling) {
        const found = next.querySelector<HTMLButtonElement>('button[data-fact]');
        if (found) return found;
      }
      return null;
    };
    const inColumn = (step: 1 | -1): HTMLButtonElement | null => {
      for (
        let next = step === 1 ? row.nextElementSibling : row.previousElementSibling;
        next;
        next = step === 1 ? next.nextElementSibling : next.previousElementSibling
      ) {
        const found = (next as HTMLTableRowElement).cells?.[column]?.querySelector<HTMLButtonElement>('button[data-fact]');
        if (found) return found;
      }
      return null;
    };
    const target =
      event.key === 'ArrowRight'
        ? inRow(cell.nextElementSibling, 1)
        : event.key === 'ArrowLeft'
          ? inRow(cell.previousElementSibling, -1)
          : event.key === 'ArrowDown'
            ? inColumn(1)
            : event.key === 'ArrowUp'
              ? inColumn(-1)
              : null;
    if (target) {
      event.preventDefault();
      target.focus();
    }
  }

  const columnCount = periods.length + 1;
  const sections = STATEMENTS.map((statement) => ({ ...statement, lines: spread.lines.filter((line) => line.statement === statement.id) })).filter(
    (section) => section.lines.length > 0,
  );
  const lastKey = sections[sections.length - 1]?.lines.at(-1)?.key;

  return (
    <div className={cx('rounded-md border border-hairline-strong bg-surface', scroll ? 'relative overflow-x-auto' : 'max-md:relative max-md:overflow-x-auto')}>
      <table className="w-full border-separate border-spacing-0 text-body">
        <caption className="sr-only">Multi-period spread, US dollars in thousands. Each figure opens its source.</caption>
        <colgroup>
          <col className="min-w-[148px] md:min-w-[260px]" />
          {periods.map((period) => (
            <col key={period.period_end} className="w-[112px]" />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th
              scope="col"
              className={cx(
                'eyebrow sticky left-0 z-20 rounded-tl-md border-b border-ink bg-surface px-4 text-left align-bottom',
                scroll ? 'top-0' : 'top-0 md:top-(--topbar-h)',
              )}
            >
              <span className="block pb-1.5">Line</span>
            </th>
            {periods.map((period, index) => {
              const head = periodHead(period);
              return (
                <th
                  key={period.period_end}
                  scope="col"
                  className={cx(
                    'sticky z-10 border-b border-ink bg-surface pt-2 pr-[34px] pl-2 text-right align-bottom',
                    scroll ? 'top-0' : 'top-0 md:top-(--topbar-h)',
                    index === periods.length - 1 && 'rounded-tr-md',
                  )}
                >
                  <span className="block text-body font-semibold whitespace-nowrap text-ink">{head.top}</span>
                  <span className="block text-micro font-medium whitespace-nowrap text-ink-500">{formatDate(period.period_end)}</span>
                  <span className="block pb-1.5 text-micro font-medium whitespace-nowrap text-ink-500">{head.bottom}</span>
                </th>
              );
            })}
          </tr>
        </thead>
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
        <tbody
          onKeyDown={onKeyDown}
          onFocus={(event) => {
            const id = event.target instanceof HTMLElement ? event.target.dataset.fact : undefined;
            if (id) setTabStopId(id);
          }}
        >
          {sections.map((section, sectionIndex) => (
            <Fragment key={section.id}>
              <tr>
                <th
                  scope="colgroup"
                  colSpan={columnCount}
                  className={cx('h-9 border-b border-hairline-strong px-4 text-left align-bottom', sectionIndex > 0 && 'pt-3')}
                >
                  <span className="sticky left-4 inline-block pb-1.5">
                    <span className="text-body font-semibold text-ink">{section.title}</span>
                    <span className="ml-2 text-caption font-regular text-ink-500">{section.basis}</span>
                  </span>
                </th>
              </tr>
              {section.lines.map((line) => {
                const total = TOTALS.has(line.key);
                const isLast = line.key === lastKey;
                return (
                  <tr key={line.key} className={cx(line.computed && 'bg-canvas')}>
                    <th
                      scope="row"
                      className={cx(
                        'sticky left-0 z-[5] h-8 py-1 pr-2 pl-4 text-left text-pretty',
                        line.computed ? 'bg-canvas font-semibold text-ink' : 'bg-surface pl-7 font-regular text-ink-700',
                        !isLast && 'border-b border-hairline',
                      )}
                    >
                      {line.label}
                    </th>
                    {periods.map((period) => {
                      const fact = cellFact(line, period);
                      return (
                        <td
                          key={period.period_end}
                          className={cx(
                            'h-8 pr-3 pl-2 text-right whitespace-nowrap',
                            !isLast && !total && 'border-b border-hairline',
                            line.computed && 'border-t border-t-ink',
                            total && 'border-b-[3px] border-double border-b-ink',
                          )}
                        >
                          {fact ? (
                            <FactFigure
                              fact={fact}
                              scale={1000}
                              unitMark={false}
                              align="column"
                              weight={line.computed ? 'semibold' : 'regular'}
                              tabIndex={fact.id === tabStop ? 0 : -1}
                            />
                          ) : (
                            <Absent align="column" reason="No figure stored for this line and period" />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Spreads() {
  // With a drawer beside it the grid has less room than its periods need, so it scrolls in its own frame.
  const sourceOpen = useSource().current !== null;
  const drawerOpen = useWorkspaceDrawer().open;
  const beside = sourceOpen || drawerOpen;
  const borrower = useCurrentBorrower();
  const spread = useSpread(borrower.id);
  const search = useSearch({ from: '/borrowers/$code/spreads' });
  const navigate = useNavigate({ from: '/borrowers/$code/spreads' });
  const view = search.periods ?? 'recent';

  return (
    <Load query={spread} what="The spread" rows={14}>
      {(data) => {
        const all = [...data.periods].sort((a, b) => a.period_end.localeCompare(b.period_end));
        const filled = all.filter((period) => data.lines.some((line) => line.cells[period.period_end]));
        if (filled.length === 0) {
          return (
            <div data-ready>
              <EmptyCard
                title="Nothing has been spread yet"
                description="Figures appear here once statements are filed and spread. If statements are on file, an open item is holding the spread."
                action={
                  <Link to="/borrowers/$code/documents" params={{ code: borrower.code }} className="link text-body font-medium">
                    Open the documents
                  </Link>
                }
              />
            </div>
          );
        }
        const periods = view === 'all' ? filled : view === 'annual' ? filled.filter((period) => period.months === 12) : filled.slice(-6);
        const latest = filled[filled.length - 1];
        const cycleEnd = borrower.latest_cycle?.period_end;
        const lagging = cycleEnd && latest && cycleEnd > latest.period_end;
        return (
          <div data-ready className="space-y-3">
            <SectionHead
              title="Spread"
              note={
                <>
                  USD thousands, as reported · template <span className="ident">{data.template}</span> · {filled.length} periods on file
                </>
              }
              actions={
                <>
                  <ProvenanceLegend kinds={['seeded', 'extracted', 'calculated', 'manual']} />
                  <Select
                    label="Periods shown"
                    hideLabel
                    size="sm"
                    className="w-44 max-w-full"
                    value={view}
                    onValueChange={(value) => void navigate({ search: value === 'recent' ? {} : { periods: value }, replace: true, resetScroll: false })}
                    options={[
                      { value: 'recent', label: 'Latest six periods' },
                      { value: 'annual', label: 'Fiscal years only' },
                      { value: 'all', label: `All ${filled.length} periods` },
                    ]}
                  />
                </>
              }
            />
            {lagging ? (
              <p className="text-body text-ink-700">
                The period ended {formatDate(cycleEnd)} is not spread yet: an open item is holding it.{' '}
                <Link to="/command-centre" className="link font-medium">
                  Open the work queue
                </Link>
              </p>
            ) : null}
            {periods.length === 0 ? (
              <EmptyCard title="No fiscal year is on file" description="Choose another set of periods." />
            ) : (
              <Grid spread={data} periods={periods} scroll={periods.length > 7 || beside} />
            )}
            <p className="text-caption text-pretty text-ink-500">
              A dash means no figure is stored for that line and period; it is never read as zero. Computed lines carry a rule above; totals carry a double rule
              below. Arrow keys move between figures; Enter opens the source page with the figure outlined.
            </p>
          </div>
        );
      }}
    </Load>
  );
}
