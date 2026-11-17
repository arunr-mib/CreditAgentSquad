import { useNavigate, useSearch } from '@tanstack/react-router';
import { Fragment, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useSpread } from '@/api/queries';
import type { Fact, FootingCheck, SourcePage, SpreadLine, SpreadPeriod } from '@/api/types';
import {
  Card,
  FactSource,
  FactsProvider,
  Figure,
  formatFigure,
  NOT_MEASURED,
  provenance,
  ProvenanceGlyph,
  SkeletonRows,
  StatusDot,
  type StatusTone,
} from '@/design';
import { cx } from '@/lib/cx';
import { BorrowerHeader } from './BorrowerHeader';

const QUALITY: Record<SpreadPeriod['quality'], string> = { audited: 'Audited', reviewed: 'Reviewed', compiled: 'Compiled', internal: 'Internal' };
const CHECK_TONE: Record<FootingCheck['result'], StatusTone> = { pass: 'pass', attention: 'attention', info: 'neutral' };

/** A facsimile of the source page with the quoted figure highlighted. Stands in for the document viewer. */
function SourcePageView({ page, factId, notice }: { page: SourcePage; factId: string; notice: string }) {
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = scroller.current;
    const target = container?.querySelector<HTMLElement>('[data-quoted]');
    if (container && target) container.scrollTop = Math.max(0, target.offsetTop - container.clientHeight / 2);
  }, [factId, page]);

  return (
    <figure>
      {/* The page facsimile scrolls, so it takes focus for keyboard scrolling. */}
      <div
        ref={scroller}
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
        tabIndex={0}
        role="group"
        aria-label={`${page.documentTitle}, page ${page.page}`}
        className="relative max-h-[304px] overflow-y-auto rounded-sm border border-hairline-strong bg-white px-4 py-3.5"
      >
        <p className="text-center text-[9px] font-semibold tracking-[0.12em] text-ink-500">{notice}</p>
        <p className="mt-2 text-center text-caption font-semibold text-ink">{page.heading}</p>
        <p className="text-center text-[10px] leading-4 text-ink-700">{page.subheading}</p>
        <table className="mt-3 w-full border-separate border-spacing-0 text-[11px] leading-[18px] text-ink">
          <thead>
            <tr>
              <th scope="col" className="sr-only">
                Line
              </th>
              {page.columnHeads.map((head) => (
                <th key={head} scope="col" className="tnum w-[52px] border-b border-ink pb-0.5 text-right font-semibold">
                  {head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {page.rows.map((row, rowIndex) => {
              const quoted = row.factIds.includes(factId);
              return (
                <tr key={`${row.label}-${rowIndex}`} data-quoted={quoted ? '' : undefined}>
                  <th
                    scope="row"
                    colSpan={row.values.length === 0 ? page.columnHeads.length + 1 : 1}
                    className={cx('text-left', row.strong ? 'font-semibold' : 'font-regular', row.indent && 'pl-3', row.gapBefore && 'pt-2')}
                  >
                    {quoted ? <mark className="rounded-xs bg-cobalt-bg px-0.5 text-ink ring-1 ring-cobalt-border">{row.label}</mark> : row.label}
                  </th>
                  {row.values.map((value, index) => {
                    const hit = row.factIds[index] === factId;
                    return (
                      <td key={index} className={cx('tnum text-right', row.strong && 'border-t border-ink font-semibold')}>
                        {hit ? <mark className="rounded-xs bg-cobalt-bg px-0.5 font-semibold text-ink ring-1 ring-cobalt">{value}</mark> : value}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-1.5 flex items-baseline justify-between gap-3 text-caption text-ink-500">
        <span className="truncate">{page.documentTitle}</span>
        <span className="tnum shrink-0">Page {page.page}</span>
      </figcaption>
    </figure>
  );
}

function SourcePanel({ fact, pages, stated, notice }: { fact: Fact; pages: Record<string, SourcePage>; stated: Fact | null; notice: string }) {
  const pageFact = fact.provenance.kind === 'extracted' ? fact : stated;
  const page = pageFact?.provenance.kind === 'extracted' ? pages[`${pageFact.provenance.documentId}:${pageFact.provenance.page}`] : undefined;
  const { text } = formatFigure(fact.value, fact.unit, { scale: 1000, unitMark: false });
  const foots = stated ? stated.value === fact.value : null;

  return (
    <Card>
      <div className="flex items-start justify-between gap-4 px-4 pt-3.5 pb-3">
        <div className="min-w-0">
          <div className="eyebrow flex items-center gap-1.5">
            <ProvenanceGlyph kind={fact.provenance.kind} />
            {provenance[fact.provenance.kind].phrase}
          </div>
          <h2 className="mt-1 text-title font-semibold text-pretty text-ink">{fact.label}</h2>
          <p className="text-caption text-ink-500">{fact.periodLabel}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="tnum text-heading font-semibold text-ink">{text}</p>
          <p className="text-caption text-ink-500">USD thousands</p>
        </div>
      </div>
      <div className="space-y-3.5 px-4 pb-4">
        {page && pageFact ? <SourcePageView page={page} factId={pageFact.id} notice={notice} /> : null}
        {stated ? (
          <div className="flex items-center justify-between gap-3 rounded-sm border border-hairline bg-canvas px-3 py-2 text-body">
            <span className="text-ink-700">
              Stated on the page <Figure fact={stated} scale={1000} unitMark={false} weight="medium" className="ml-1" />
            </span>
            {foots ? <StatusDot tone="pass">Foots to the stated total</StatusDot> : <StatusDot tone="attention">Does not foot</StatusDot>}
          </div>
        ) : null}
        <FactSource fact={fact} bare besidePage={Boolean(page)} />
      </div>
    </Card>
  );
}

function Legend() {
  return (
    <ul aria-label="Provenance glyphs" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-700">
      {(['extracted', 'calculated', 'system', 'manual'] as const).map((kind) => (
        <li key={kind} className="inline-flex items-center gap-1.5">
          <ProvenanceGlyph kind={kind} />
          {provenance[kind].label}
        </li>
      ))}
    </ul>
  );
}

export function SpreadGrid() {
  const { data, isPending } = useSpread('BRW-0417');
  const search = useSearch({ strict: false }) as { cell?: string };
  const navigate = useNavigate();
  // One tab stop for the whole grid; arrow keys move between figures.
  const [tabStopId, setTabStopId] = useState<string | null>(null);

  if (isPending || !data) return <SkeletonRows rows={12} label="Loading the spread" />;

  const { borrower, periods, sections, facts, footingChecks, sourcePages, notice } = data;
  const lastPeriod = periods[periods.length - 1];
  const defaultId = sections[0]?.groups[0]?.lines.find((line) => line.key === 'is.nonrecurring_expense')?.cells[lastPeriod?.id ?? ''] ?? null;
  const selectedId = search.cell && facts[search.cell] ? search.cell : defaultId;
  const selected = selectedId ? facts[selectedId] : undefined;

  // The stated total that belongs to the selected computed cell, if any.
  let stated: Fact | null = null;
  if (selected?.provenance.kind === 'calculated') {
    for (const section of sections) {
      for (const group of section.groups) {
        for (const line of group.lines) {
          for (const period of periods) {
            if (line.cells[period.id] === selected.id) stated = facts[line.stated?.[period.id] ?? ''] ?? null;
          }
        }
      }
    }
  }

  const tabStop = tabStopId ?? selectedId;

  function onGridKeyDown(event: KeyboardEvent<HTMLTableSectionElement>) {
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

  const select = (fact: Fact) => void navigate({ to: '/showcase/spread', search: { cell: fact.id }, replace: true, resetScroll: false });
  const columnCount = periods.length + 1;

  const renderLine = (line: SpreadLine, isLast: boolean) => {
    const total = line.emphasis === 'total';
    return (
      <tr key={line.key} className={cx(line.computed && 'bg-canvas')}>
        <th
          scope="row"
          className={cx(
            'h-8 py-1 pr-2 pl-4 text-left text-pretty',
            !isLast && 'border-b border-hairline',
            line.computed ? 'font-semibold text-ink' : 'pl-7 font-regular text-ink-700',
          )}
        >
          {line.label}
        </th>
        {periods.map((period) => {
          const factId = line.cells[period.id];
          const fact = factId ? facts[factId] : undefined;
          return (
            <td
              key={period.id}
              className={cx(
                'h-8 pr-3 pl-2 text-right whitespace-nowrap',
                !isLast && !total && 'border-b border-hairline',
                line.computed && 'border-t border-t-ink',
                total && 'border-b-[3px] border-double border-b-ink',
              )}
            >
              {fact ? (
                <Figure
                  fact={fact}
                  scale={1000}
                  unitMark={false}
                  align="column"
                  weight={line.computed ? 'semibold' : 'regular'}
                  onSelect={select}
                  selected={fact.id === selectedId}
                  tabIndex={fact.id === tabStop ? 0 : -1}
                />
              ) : (
                <span className="pr-[21px] text-ink-500" title="No such line on the statement; recorded as absent">
                  <span aria-hidden>{NOT_MEASURED}</span>
                  <span className="sr-only">Absent from the statement</span>
                </span>
              )}
            </td>
          );
        })}
      </tr>
    );
  };

  return (
    <FactsProvider facts={facts}>
      <div data-ready className="space-y-5">
        <BorrowerHeader borrower={borrower} facts={facts} current="Spreads" />

        <section aria-labelledby="footing-heading">
          <h2 id="footing-heading" className="eyebrow mb-1.5">
            Footing checks <span className="font-medium tracking-normal normal-case">run by code on every period</span>
          </h2>
          <ul className="grid grid-cols-3 border-t border-b border-t-ink border-b-hairline-strong xl:grid-cols-6 xl:divide-x xl:divide-hairline-strong">
            {footingChecks.map((check) => (
              <li key={check.id} className="px-4 py-2.5 xl:first:pl-0">
                <StatusDot tone={CHECK_TONE[check.result]} className="text-body font-semibold">
                  {check.resultLabel}
                </StatusDot>
                <p className="mt-0.5 text-caption text-pretty text-ink-700">{check.label}</p>
              </li>
            ))}
          </ul>
        </section>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <section aria-labelledby="spread-heading" className="min-w-0">
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <div className="flex items-baseline gap-3">
                <h2 id="spread-heading" className="text-title font-semibold text-ink">
                  Spread
                </h2>
                <p className="text-caption text-ink-500">
                  USD thousands, as reported · template <span className="ident">ci-1</span>
                </p>
              </div>
              <Legend />
            </div>

            <div className="rounded-md border border-hairline-strong bg-surface">
              <table className="w-full border-separate border-spacing-0 text-body">
                <caption className="sr-only">Multi-period spread: income statement and balance sheet, US dollars in thousands</caption>
                <colgroup>
                  <col />
                  {periods.map((period) => (
                    <col key={period.id} className="w-[112px]" />
                  ))}
                </colgroup>
                <thead>
                  <tr>
                    <th scope="col" className="eyebrow sticky top-(--topbar-h) z-10 rounded-tl-md border-b border-ink bg-surface px-4 text-left align-bottom">
                      <span className="block pb-1.5">Line</span>
                    </th>
                    {periods.map((period, index) => (
                      <th
                        key={period.id}
                        scope="col"
                        className={cx(
                          'sticky top-(--topbar-h) z-10 border-b border-ink bg-surface pt-2 pr-[34px] pl-2 text-right align-bottom',
                          index === periods.length - 1 && 'rounded-tr-md',
                        )}
                      >
                        <span className="block text-body font-semibold whitespace-nowrap text-ink">{period.label}</span>
                        <span className="block text-micro font-medium whitespace-nowrap text-ink-500">{QUALITY[period.quality]}</span>
                        <span className="block pb-1.5 text-micro font-medium whitespace-nowrap text-ink-500">
                          {period.spreadStatus === 'confirmed' ? 'Confirmed' : 'Verified'}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
                <tbody
                  onKeyDown={onGridKeyDown}
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
                          <span className="inline-block pb-1.5 text-body font-semibold text-ink">{section.title}</span>
                          <span className="ml-2 text-caption font-regular text-ink-500">{section.basis}</span>
                        </th>
                      </tr>
                      {section.groups.map((group, groupIndex) => (
                        <Fragment key={group.title ?? groupIndex}>
                          {group.title ? (
                            <tr>
                              <th scope="colgroup" colSpan={columnCount} className="eyebrow h-7 border-b border-hairline px-4 text-left align-bottom">
                                <span className="inline-block pb-1">{group.title}</span>
                              </th>
                            </tr>
                          ) : null}
                          {group.lines.map((line, lineIndex) =>
                            renderLine(
                              line,
                              sectionIndex === sections.length - 1 && groupIndex === section.groups.length - 1 && lineIndex === group.lines.length - 1,
                            ),
                          )}
                        </Fragment>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-caption text-ink-500">
              {NOT_MEASURED} No such line on the statement. Recorded as absent, not as zero, because the section foots. Computed lines are calculated by code
              and carry a rule above; totals carry a double rule below. Arrow keys move between figures; Enter shows the source.
            </p>
          </section>

          <aside aria-label="Source of the selected figure" className="xl:sticky xl:top-[68px]">
            {selected ? <SourcePanel fact={selected} pages={sourcePages} stated={stated} notice={notice} /> : null}
          </aside>
        </div>
      </div>
    </FactsProvider>
  );
}
