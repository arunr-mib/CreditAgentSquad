import { Bell, Download, FileSearch, Filter, MoreHorizontal, Search } from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import type { CovenantTest, Fact } from '@/api/types';
import {
  AgentMark,
  AgentNote,
  Button,
  Card,
  CardBody,
  CardHeader,
  CommandPalette,
  DataTable,
  Dialog,
  DialogClose,
  EmptyState,
  FactsProvider,
  Figure,
  GuardrailNotes,
  IconButton,
  Input,
  Kbd,
  MetaItem,
  PageHeader,
  Popover,
  provenance,
  ProvenanceGlyph,
  Segmented,
  Select,
  Skeleton,
  SkeletonRows,
  StatusDot,
  Stepper,
  Tabs,
  Tooltip,
  useToast,
  WorkItemCard,
  type DataColumn,
} from '@/design';
import { covenants, cycle, facts, fccrRecommendation, fccrWorkItem, named } from '@/fixtures/brightwater';
import { workItemTypeLabel } from '@/fixtures/workItems';
import { Mark } from '@/shell/Wordmark';

function Section({ id, title, lead, children }: { id: string; title: string; lead?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="border-t border-ink pt-4">
      <div className="mb-5 grid gap-x-8 xl:grid-cols-[220px_minmax(0,1fr)]">
        <h2 id={id} className="text-heading font-semibold tracking-[-0.01em] text-ink">
          {title}
        </h2>
        {lead ? <p className="max-w-[72ch] text-prose text-ink-700">{lead}</p> : null}
      </div>
      <div className="divide-y divide-hairline-strong">{children}</div>
    </section>
  );
}

function Story({ name, rule, children }: { name: string; rule: string; children: ReactNode }) {
  return (
    <div className="grid gap-x-8 gap-y-3 py-5 first:pt-0 xl:grid-cols-[220px_minmax(0,1fr)]">
      <div>
        <h3 className="text-body font-semibold text-ink">{name}</h3>
        <p className="mt-0.5 text-caption text-pretty text-ink-500">{rule}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

const COLOUR_ROLES: Array<{ role: string; meaning: string; tokens: Array<{ name: string; use: string; border?: boolean }> }> = [
  {
    role: 'Neutrals',
    meaning: 'Ink on a warm off-white canvas. Everything that is not a meaning.',
    tokens: [
      { name: '--canvas', use: 'Page', border: true },
      { name: '--surface', use: 'Cards, tables', border: true },
      { name: '--surface-sunken', use: 'Wells, current nav', border: true },
      { name: '--hairline', use: 'Row rules', border: true },
      { name: '--hairline-strong', use: 'Card borders' },
      { name: '--ink-400', use: 'Control borders' },
      { name: '--ink-500', use: 'Labels, glyphs' },
      { name: '--ink-700', use: 'Secondary text' },
      { name: '--ink-900', use: 'Text, strong rules' },
    ],
  },
  {
    role: 'Cobalt',
    meaning: 'Interactive: links, the primary action, focus, the current selection.',
    tokens: [
      { name: '--cobalt', use: 'Text, fill' },
      { name: '--cobalt-strong', use: 'Hover' },
      { name: '--cobalt-bg', use: 'Selected', border: true },
      { name: '--cobalt-border', use: 'Border' },
    ],
  },
  {
    role: 'Iris',
    meaning: 'Written by an agent.',
    tokens: [
      { name: '--iris', use: 'Text' },
      { name: '--iris-mark', use: 'Agent mark' },
      { name: '--iris-bg', use: 'Note ground', border: true },
      { name: '--iris-border', use: 'Border' },
    ],
  },
  {
    role: 'Red',
    meaning: 'Covenant breach. Nothing else is red.',
    tokens: [
      { name: '--red', use: 'Text' },
      { name: '--red-mark', use: 'Dot' },
      { name: '--red-bg', use: 'Ground', border: true },
      { name: '--red-border', use: 'Border' },
    ],
  },
  {
    role: 'Amber',
    meaning: 'Needs attention from a person.',
    tokens: [
      { name: '--amber', use: 'Text' },
      { name: '--amber-mark', use: 'Dot' },
      { name: '--amber-bg', use: 'Ground', border: true },
      { name: '--amber-border', use: 'Border' },
    ],
  },
  {
    role: 'Green',
    meaning: 'Verified pass or recorded resolution. Never a screen state.',
    tokens: [
      { name: '--green', use: 'Text' },
      { name: '--green-mark', use: 'Dot' },
      { name: '--green-bg', use: 'Ground', border: true },
      { name: '--green-border', use: 'Border' },
    ],
  },
];

const TYPE_SCALE: Array<{ token: string; className: string; spec: string; sample: string }> = [
  { token: 'display', className: 'text-display font-semibold tracking-[-0.02em]', spec: '34 / 40 · 600', sample: 'Command centre' },
  { token: 'page', className: 'text-page font-semibold tracking-[-0.018em]', spec: '26 / 32 · 600', sample: 'Brightwater Fastener Co.' },
  { token: 'heading', className: 'text-heading font-semibold tracking-[-0.01em]', spec: '20 / 28 · 600', sample: 'Covenant tests' },
  { token: 'title', className: 'text-title font-semibold', spec: '16 / 24 · 600', sample: 'Fixed charge coverage ratio' },
  { token: 'prose', className: 'text-prose', spec: '14 / 22 · 400', sample: 'The credit agreement caps that add-back in any four-quarter period.' },
  { token: 'body', className: 'text-body', spec: '13 / 20 · 400', sample: 'Trailing twelve months, tested quarterly' },
  { token: 'caption', className: 'text-caption text-ink-700', spec: '12 / 16 · 400', sample: 'Terms in force: version 2, approved 9 Jan 2025' },
  { token: 'micro', className: 'eyebrow', spec: '11 / 16 · 600 · caps', sample: 'Cycles in progress' },
];

export function DesignPage() {
  const toast = useToast();
  const [segment, setSegment] = useState('all');
  const [stage, setStage] = useState('covenant_testing');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState('fccr');

  const manualFact = useMemo(() => Object.values(facts).find((fact) => fact.provenance.kind === 'manual') as Fact, []);
  const systemFact = useMemo(() => Object.values(facts).find((fact) => fact.provenance.kind === 'system') as Fact, []);
  const specimen = useMemo(() => {
    const line = (key: string) => Object.values(facts).find((fact) => fact.key === key && fact.periodLabel === 'Nine months ended 30 Sep 2026') as Fact;
    return [line('is.revenue'), line('is.cogs'), line('is.gross_profit')];
  }, []);
  const documentFact = useMemo(() => Object.values(facts).find((fact) => fact.key === 'is.revenue' && fact.periodLabel.includes('2026')) as Fact, []);

  const columns = useMemo<Array<DataColumn<CovenantTest>>>(() => {
    const cell = (id: string | null) => (id && facts[id] ? <Figure fact={facts[id]} /> : null);
    return [
      { id: 'name', header: 'Covenant', rowHeader: true, sortValue: (row) => row.name, cell: (row) => <span className="font-medium">{row.name}</span> },
      { id: 'calculated', header: 'Calculated', align: 'right', width: '150px', cell: (row) => cell(row.calculatedFactId) },
      {
        id: 'headroom',
        header: 'Headroom',
        align: 'right',
        width: '130px',
        sortValue: (row) => Number(facts[row.headroomFactId ?? '']?.value ?? 0),
        cell: (row) => cell(row.headroomFactId),
      },
      {
        id: 'outcome',
        header: 'Outcome',
        width: '230px',
        cell: (row) =>
          row.outcome.startsWith('breach') ? (
            <StatusDot tone="breach" emphasis>
              Breach, reported compliant
            </StatusDot>
          ) : row.outcome === 'compliant_variance' ? (
            <StatusDot tone="attention">Compliant, variance</StatusDot>
          ) : (
            <StatusDot tone="pass">Compliant</StatusDot>
          ),
      },
    ];
  }, []);

  return (
    <FactsProvider facts={facts}>
      <div data-ready className="space-y-10">
        <PageHeader
          eyebrow="Credit Agent Squad"
          title="Design system"
          meta={
            <>
              <MetaItem label="Tokens">
                <span className="ident">src/design/tokens.css</span>
              </MetaItem>
              <MetaItem label="Rules">
                <span className="ident">frontend/DESIGN.md</span>
              </MetaItem>
              <MetaItem label="Components">
                <span className="ident">src/design/</span>
              </MetaItem>
            </>
          }
        />

        <Section
          id="identity"
          title="Identity"
          lead="A research terminal’s calm, not a dashboard’s noise. Quiet warm surfaces, ink type, hairline rules, and five colours that each mean one thing. Agents appear as a colleague’s annotations; people decide."
        >
          <Story name="Mark and wordmark" rule="Three units in formation. The wordmark is Inter semibold; there is no second typeface.">
            <div className="flex flex-wrap items-center gap-10">
              <span className="inline-flex items-center gap-3">
                <Mark size={32} />
                <span className="text-heading font-semibold tracking-[-0.015em] text-ink">Credit Agent Squad</span>
              </span>
              <span className="inline-flex items-center gap-2.5">
                <Mark />
                <span className="text-prose font-semibold tracking-[-0.012em] text-ink">Credit Agent Squad</span>
              </span>
              <Mark size={20} />
            </div>
          </Story>
          <Story name="Principle" rule="The line every screen is checked against.">
            <p className="max-w-[40ch] text-page font-semibold tracking-[-0.018em] text-ink">
              Agents reason. Code calculates. Guardrails verify. People decide.
            </p>
          </Story>
        </Section>

        <Section
          id="colour"
          title="Colour"
          lead="Colour carries meaning only. If a colour appears and none of these meanings applies, it is a defect. Text, ground and border variants pass WCAG AA on every surface they are used on; a test enforces it."
        >
          {COLOUR_ROLES.map((group) => (
            <Story key={group.role} name={group.role} rule={group.meaning}>
              <ul className="grid grid-cols-3 gap-x-6 gap-y-3 md:grid-cols-5">
                {group.tokens.map((token) => (
                  <li key={token.name} className="min-w-0">
                    <span
                      aria-hidden
                      className={`block h-9 rounded-sm ${token.border ? 'border border-hairline-strong' : ''}`}
                      style={{ background: `var(${token.name})` }}
                    />
                    <span className="ident mt-1.5 block truncate text-caption text-ink">{token.name}</span>
                    <span className="block text-caption text-ink-500">{token.use}</span>
                  </li>
                ))}
              </ul>
            </Story>
          ))}
        </Section>

        <Section
          id="type"
          title="Type"
          lead="One typeface, Inter, at eight sizes. Figures use tabular lining numerals and are never monospace. JetBrains Mono is for identifiers only. A quoted clause is prose."
        >
          <Story name="Scale" rule="Hierarchy comes from size and weight, not colour.">
            <ul>
              {TYPE_SCALE.map((row) => (
                <li key={row.token} className="grid grid-cols-[88px_150px_minmax(0,1fr)] items-baseline gap-4 border-b border-hairline py-2 last:border-b-0">
                  <span className="ident text-caption text-ink">{row.token}</span>
                  <span className="tnum text-caption text-ink-500">{row.spec}</span>
                  <span className={`truncate ${row.className}`}>{row.sample}</span>
                </li>
              ))}
            </ul>
          </Story>
          <Story name="Figures and identifiers" rule="Tabular numerals align in columns. Mono marks an identifier, nothing else.">
            <div className="flex flex-wrap items-start gap-12">
              <div className="w-40 text-right text-body">
                {specimen.map((fact, index) => (
                  <div key={fact.id} className={index === specimen.length - 1 ? 'border-t border-ink py-1' : 'border-b border-hairline py-1'}>
                    <Figure fact={fact} scale={1000} unitMark={false} align="column" weight={index === specimen.length - 1 ? 'semibold' : 'regular'} />
                  </div>
                ))}
              </div>
              <dl className="space-y-1 text-body">
                <div className="flex gap-3">
                  <dt className="w-28 text-ink-500">Fact</dt>
                  <dd className="ident">{named.fccr.id}</dd>
                </div>
                <div className="flex gap-3">
                  <dt className="w-28 text-ink-500">Calculation</dt>
                  <dd className="ident">{named.fccr.provenance.kind === 'calculated' ? named.fccr.provenance.calcId : ''}</dd>
                </div>
                <div className="flex gap-3">
                  <dt className="w-28 text-ink-500">Quoted clause</dt>
                  <dd className="max-w-[46ch] text-ink-700">“…shall not exceed $250,000 in any period of four consecutive fiscal quarters.”</dd>
                </div>
              </dl>
            </div>
          </Story>
        </Section>

        <Section
          id="foundations"
          title="Space, shape, depth, motion"
          lead="A 4 px grid. Small radii and no pills. Two shadow steps, both for things that float. Nothing moves for longer than 240 ms."
        >
          <Story name="Spacing" rule="4 px scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.">
            <div className="flex flex-wrap items-end gap-3">
              {[4, 8, 12, 16, 20, 24, 32, 40, 48, 64].map((size) => (
                <div key={size} className="text-center">
                  <span aria-hidden className="block bg-ink" style={{ width: size, height: size }} />
                  <span className="tnum mt-1 block text-caption text-ink-500">{size}</span>
                </div>
              ))}
            </div>
          </Story>
          <Story name="Radius and shadow" rule="2 px marks, 4 px controls, 6 px cards. Cards sit flat; only overlays cast a shadow.">
            <div className="flex flex-wrap items-center gap-6 text-caption text-ink-700">
              <span className="flex h-14 w-24 items-center justify-center rounded-xs border border-hairline-strong bg-surface">2 px</span>
              <span className="flex h-14 w-24 items-center justify-center rounded-sm border border-hairline-strong bg-surface">4 px</span>
              <span className="flex h-14 w-24 items-center justify-center rounded-md border border-hairline-strong bg-surface">6 px</span>
              <span className="flex h-14 w-28 items-center justify-center rounded-md border border-hairline-strong bg-surface shadow-raised">Raised</span>
              <span className="flex h-14 w-28 items-center justify-center rounded-md border border-hairline-strong bg-surface shadow-overlay">Overlay</span>
            </div>
          </Story>
          <Story name="Motion" rule="80 ms for hover and press, 140 ms for popovers, 200 ms for dialogs. 240 ms is the ceiling.">
            <ul className="flex flex-wrap gap-x-8 gap-y-1 text-body">
              {[
                ['--motion-instant', '80 ms'],
                ['--motion-fast', '140 ms'],
                ['--motion-base', '200 ms'],
                ['--motion-max', '240 ms'],
              ].map(([token, value]) => (
                <li key={token}>
                  <span className="ident text-caption">{token}</span> <span className="tnum text-ink-500">{value}</span>
                </li>
              ))}
            </ul>
          </Story>
        </Section>

        <Section
          id="meaning"
          title="Status, figures and agents"
          lead="The three devices that make the product legible: a dot and a word for status, a glyph and a source for every figure, and an iris mark for anything an agent wrote."
        >
          <Story
            name="StatusDot"
            rule="A small dot plus a word. Never a pill, never colour alone. Emphasis colours the word for outcomes that must not be missed."
          >
            <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-body">
              <StatusDot tone="breach" emphasis>
                Breach, reported compliant
              </StatusDot>
              <StatusDot tone="attention">Needs a person</StatusDot>
              <StatusDot tone="pass">Compliant</StatusDot>
              <StatusDot tone="agent">Written by an agent</StatusDot>
              <StatusDot tone="neutral">Running</StatusDot>
              <StatusDot tone="muted">Not started</StatusDot>
            </div>
          </Story>
          <Story name="Provenance glyphs" rule="Where a figure came from is a glyph beside it, not a colour.">
            <ul className="flex flex-wrap gap-x-8 gap-y-2 text-body">
              {(['extracted', 'calculated', 'system', 'manual'] as const).map((kind) => (
                <li key={kind} className="inline-flex items-center gap-2">
                  <ProvenanceGlyph kind={kind} size={14} />
                  <span className="font-medium">{provenance[kind].label}</span>
                  <span className="text-ink-500">{provenance[kind].phrase}</span>
                </li>
              ))}
            </ul>
          </Story>
          <Story
            name="Figure"
            rule="A formatted number, its unit and glyph. Select it to open the source: document, page and quote; or formula and inputs. No figure is shown any other way."
          >
            <dl className="grid max-w-[640px] grid-cols-[minmax(0,1fr)_auto] gap-x-8 text-body">
              {[
                ['Net revenue, nine months ended 30 Sep 2026', <Figure key="a" fact={documentFact} />],
                ['Fixed charge coverage ratio', <Figure key="b" fact={named.fccr} weight="semibold" />],
                ['Headroom against the minimum', <Figure key="c" fact={named.fccrHeadroom} />],
                ['Line of credit commitment', <Figure key="d" fact={systemFact} />],
                ['Other income (expense), net', <Figure key="e" fact={manualFact} />],
              ].map(([label, figure], index) => (
                <div key={index} className="col-span-2 grid grid-cols-subgrid border-b border-hairline py-1.5 last:border-b-0">
                  <dt className="text-ink-700">{label}</dt>
                  <dd className="text-right">{figure}</dd>
                </div>
              ))}
            </dl>
          </Story>
          <Story
            name="AgentNote"
            rule="Iris ground, a hairline on all four sides and the agent mark. A draft until a person approves. The agent writes fact references; code renders the figures."
          >
            <div className="grid items-start gap-5 xl:grid-cols-2">
              <AgentNote
                agent={fccrRecommendation.agent}
                headline={fccrRecommendation.headline}
                body={fccrRecommendation.body.split('\n\n').slice(0, 2).join('\n\n')}
                state="draft"
                runId={fccrRecommendation.runId}
                writtenAt={fccrRecommendation.writtenAt}
              />
              <div className="space-y-5">
                <AgentNote
                  agent="Covenant Agent"
                  headline="Recommends resolve"
                  body={`Total leverage calculates to {{fact:${named.leverage.id}}} and passes. The certificate reports {{fact:${named.leverageCert.id}}}; the gap is the capped add-back, which the terms on file explain.`}
                  state="approved"
                  approvedBy="Maya Okafor"
                  runId="RUN-88214"
                  writtenAt="11 Nov 2026, 09:16"
                />
                <GuardrailNotes notes={fccrRecommendation.guardrailNotes.slice(1)} />
              </div>
            </div>
          </Story>
          <Story name="Agent mark" rule="The iris lozenge marks agent-written text inline, in tables and in headers.">
            <span className="inline-flex items-center gap-1.5 text-body">
              <AgentMark /> Recommends escalate
            </span>
          </Story>
        </Section>

        <Section
          id="controls"
          title="Controls"
          lead="Cobalt means it can be acted on. One primary action per card or dialog; everything else is secondary or ghost. Every control has a visible 2 px cobalt focus ring."
        >
          <Story name="Button" rule="Primary, secondary, ghost. Two sizes: 32 and 28 px.">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary">Escalate to credit officer</Button>
              <Button>Request a document</Button>
              <Button variant="ghost">Decide otherwise</Button>
              <Button iconLeft={<Download size={14} aria-hidden />}>Export</Button>
              <Button disabled>Unavailable</Button>
              <Button variant="primary" size="sm">
                Approve
              </Button>
              <Button size="sm">Edit first</Button>
            </div>
          </Story>
          <Story name="IconButton" rule="Always named: the label is the accessible name and the tooltip.">
            <div className="flex items-center gap-2">
              <IconButton label="Filter" icon={<Filter size={16} aria-hidden />} />
              <IconButton label="Notifications" icon={<Bell size={16} aria-hidden />} />
              <IconButton label="More actions" icon={<MoreHorizontal size={16} aria-hidden />} />
              <IconButton label="Open document" size="sm" icon={<FileSearch size={14} aria-hidden />} />
            </div>
          </Story>
          <Story name="Input and Select" rule="A label always. Validation is amber: red is kept for covenant breaches and critical items.">
            <div className="grid max-w-[720px] grid-cols-1 gap-4 sm:grid-cols-3">
              <Input label="Borrower" placeholder="Search by name" leading={<Search size={14} aria-hidden />} />
              <Input label="Reason for the decision" defaultValue="" error="A reason is required to decide otherwise." />
              <Select
                label="Stage"
                value={stage}
                onValueChange={setStage}
                options={[
                  { value: 'spreading', label: 'Spreading' },
                  { value: 'covenant_testing', label: 'Covenant testing' },
                  { value: 'borrowing_base', label: 'Borrowing base' },
                ]}
              />
            </div>
          </Story>
          <Story name="Tabs and Segmented" rule="Tabs switch views and carry an ink underline. Segmented is a single-choice filter with square shoulders.">
            <div className="space-y-5">
              <Tabs
                label="Borrower sections"
                items={[
                  {
                    value: 'covenants',
                    label: 'Covenants',
                    count: 5,
                    content: <p className="text-body text-ink-700">Five covenants in force for the quarter.</p>,
                  },
                  { value: 'spreads', label: 'Spreads', content: <p className="text-body text-ink-700">Four periods spread on template ci-1.</p> },
                  { value: 'documents', label: 'Documents', count: 6, content: <p className="text-body text-ink-700">Six documents on file.</p> },
                ]}
              />
              <Segmented
                label="Severity"
                value={segment}
                onValueChange={setSegment}
                options={[
                  { value: 'all', label: 'All', count: 13 },
                  { value: 'critical', label: 'Critical', count: 2 },
                  { value: 'high', label: 'High', count: 3 },
                  { value: 'medium', label: 'Medium', count: 6 },
                ]}
              />
            </div>
          </Story>
          <Story
            name="Dialog, Popover, Tooltip, Toast"
            rule="Overlays use the two shadow steps and enter in 140 to 200 ms. A toast confirms; the ledger records."
          >
            <div className="flex flex-wrap items-center gap-3">
              <Dialog
                trigger={<Button>Open dialog</Button>}
                title="Escalate to a credit officer"
                description="The breach, the calculation and the agent’s recommendation go to the credit officer queue. A second person must approve."
                footer={
                  <>
                    <DialogClose asChild>
                      <Button>Cancel</Button>
                    </DialogClose>
                    <DialogClose asChild>
                      <Button variant="primary">Escalate</Button>
                    </DialogClose>
                  </>
                }
              >
                <Input label="Note for the credit officer" placeholder="Optional" />
              </Dialog>
              <Popover label="Terms in force" className="w-72 p-4" trigger={<Button>Open popover</Button>}>
                <p className="eyebrow">Terms in force</p>
                <p className="mt-1 text-body text-ink">Version 2, approved 9 Jan 2025 by a second person. A proposed version never governs a test.</p>
              </Popover>
              <Tooltip content="Calculated by code">
                <Button>Hover for tooltip</Button>
              </Tooltip>
              <Button
                onClick={() => toast({ title: 'Decision recorded', description: 'Escalated to a credit officer and written to the ledger.', tone: 'pass' })}
              >
                Show toast
              </Button>
              <Button onClick={() => setPaletteOpen(true)} iconRight={<Kbd>Ctrl K</Kbd>}>
                Command palette
              </Button>
              <CommandPalette
                open={paletteOpen}
                onOpenChange={setPaletteOpen}
                commands={[
                  { id: 'a', group: 'Go to', label: 'Command centre', hint: 'Work queue', run: () => {} },
                  { id: 'b', group: 'Go to', label: 'Portfolio', hint: 'Exposure and signals', run: () => {} },
                  { id: 'c', group: 'Borrowers', label: 'Brightwater Fastener Co.', hint: 'BRW-0417', run: () => {} },
                  { id: 'd', group: 'Borrowers', label: 'Tessaly Cold Storage LLC', hint: 'BRW-0388', run: () => {} },
                ]}
              />
            </div>
          </Story>
        </Section>

        <Section id="structure" title="Structure" lead="Dense tables with ledger rules, cards that sit flat on the canvas, and one question per work item.">
          <Story name="PageHeader" rule="Eyebrow, title, a line of facts, and actions on the right.">
            <Card className="px-5 py-4">
              <PageHeader
                as="p"
                eyebrow={
                  <>
                    Borrower <span className="ident tracking-normal normal-case">BRW-0417</span>
                  </>
                }
                title="Brightwater Fastener Co."
                meta={
                  <>
                    <span>Industrial fasteners · Dayton, Ohio</span>
                    <MetaItem label="Line of credit commitment">
                      <Figure fact={systemFact} />
                    </MetaItem>
                  </>
                }
                actions={<Button>Open review sheet</Button>}
              />
            </Card>
          </Story>
          <Story name="DataTable" rule="34 px rows, sticky header, sortable columns, right-aligned figures. Up and Down move the row focus; Enter selects.">
            <DataTable
              caption="Covenant tests"
              data={covenants}
              columns={columns}
              getRowId={(row) => row.id}
              selectedRowId={selectedRow}
              onRowActivate={(row) => setSelectedRow(row.id)}
            />
          </Story>
          <Story name="Stepper" rule="The monitoring cycle. Done is ink, not green; amber marks the stage waiting for a person.">
            <Card className="px-4 py-4">
              <Stepper
                label="Monitoring cycle stages"
                steps={[
                  ...cycle.stages.slice(0, 4),
                  { id: 'borrowing_base', label: 'Borrowing base', status: 'skipped' },
                  { id: 'signals', label: 'Signals', status: 'running' },
                  ...cycle.stages.slice(6),
                ]}
              />
            </Card>
          </Story>
          <Story name="WorkItemCard" rule="One specific question, the evidence, and the decisions allowed. Exactly one primary action.">
            <div className="max-w-[440px]">
              <WorkItemCard
                typeLabel={workItemTypeLabel[fccrWorkItem.type]}
                itemId={fccrWorkItem.id}
                severity={{ tone: 'breach', label: 'Critical' }}
                breach
                subject={fccrWorkItem.borrowerName}
                context="Q3 2026 · Covenant testing"
                due={{ text: 'Due today' }}
                question={fccrWorkItem.question}
                evidence={fccrWorkItem.evidence}
                decisions={fccrWorkItem.decisions}
                requiresSecondPerson
              />
            </div>
          </Story>
          <Story name="Card" rule="A surface with a hairline border. No shadow and no coloured edge.">
            <div className="grid max-w-[720px] grid-cols-1 gap-5 sm:grid-cols-2">
              <Card>
                <CardHeader eyebrow="Terms" title="Version 2" meta="Approved 9 Jan 2025" actions={<Button size="sm">Open</Button>} />
                <CardBody>
                  <p className="text-body text-ink-700">Five covenants, one add-back definition, quarterly reporting.</p>
                </CardBody>
              </Card>
              <Card>
                <EmptyState
                  title="No signals this quarter"
                  description="Fourteen rules ran on the confirmed spread. None fired."
                  action={<Button size="sm">See the rules</Button>}
                  className="!py-5"
                />
              </Card>
            </div>
          </Story>
          <Story name="Skeleton" rule="Still placeholders in the shape of what is loading. They do not shimmer.">
            <div className="max-w-[720px] space-y-3">
              <div className="flex items-center gap-4">
                <Skeleton className="h-6 w-56" />
                <Skeleton className="h-3 w-32" />
              </div>
              <SkeletonRows rows={3} />
            </div>
          </Story>
        </Section>
      </div>
    </FactsProvider>
  );
}
