import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { Fact } from '@/api/types';
import { AgentNote, AgentText, CommandPalette, DataTable, FactsProvider, Figure, StatusDot, Stepper, useCommandPaletteShortcut, WorkItemCard } from '..';

const documentFact: Fact = {
  id: 'F-1',
  key: 'is.revenue',
  label: 'Net revenue',
  value: '29480000',
  unit: 'usd',
  periodLabel: 'Nine months ended 30 Sep 2026',
  status: 'verified',
  provenance: {
    kind: 'extracted',
    documentId: 'DOC-1',
    documentTitle: 'Internal financial statements',
    page: 2,
    quote: 'Net sales  29,480',
    printed: '29,480',
    labelText: 'Net sales',
    scaleAsReported: 1000,
    agentRunId: 'RUN-1',
  },
};

const ratioFact: Fact = {
  id: 'F-2',
  key: 'covenant.fccr',
  label: 'Fixed charge coverage ratio',
  value: '1.12',
  unit: 'ratio',
  periodLabel: 'Twelve months ended 30 Sep 2026',
  status: 'verified',
  provenance: {
    kind: 'calculated',
    calcId: 'C-9',
    formulaKey: 'covenant.coverage',
    formulaVersion: 'metrics-1',
    expression: 'Numerator ÷ Fixed charges',
    inputs: [{ name: 'Net revenue', factId: 'F-1' }],
  },
};

const facts = { [documentFact.id]: documentFact, [ratioFact.id]: ratioFact };

describe('Figure', () => {
  it('shows the formatted number and names its provenance', () => {
    render(<Figure fact={documentFact} scale={1000} unitMark={false} />);
    const button = screen.getByRole('button', { name: /29,480, Net revenue.*Read from a document/ });
    expect(button).toHaveTextContent('29,480');
  });

  it('opens the source of a document figure: document, page and quoted text', async () => {
    render(
      <FactsProvider facts={facts}>
        <Figure fact={documentFact} />
      </FactsProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: /Net revenue/ }));
    const source = await screen.findByRole('dialog', { name: 'Source of Net revenue' });
    expect(within(source).getByText('Internal financial statements')).toBeInTheDocument();
    expect(within(source).getByText('29,480', { selector: 'mark' })).toBeInTheDocument();
    expect(within(source).getByText('F-1')).toHaveClass('ident');
  });

  it('opens the source of a calculated figure: formula and inputs', async () => {
    render(
      <FactsProvider facts={facts}>
        <Figure fact={ratioFact} />
      </FactsProvider>,
    );
    await userEvent.keyboard('{Tab}{Enter}');
    const source = await screen.findByRole('dialog', { name: 'Source of Fixed charge coverage ratio' });
    expect(within(source).getByText('Numerator ÷ Fixed charges')).toBeInTheDocument();
    expect(within(source).getByRole('table', { name: /Inputs/ })).toHaveTextContent('Net revenue');
    expect(within(source).getByText('C-9')).toBeInTheDocument();
  });

  it('pads positive money so digits line up with accounting negatives in a column', () => {
    const { container } = render(<Figure fact={documentFact} align="column" scale={1000} unitMark={false} />);
    expect(container.querySelector('.invisible')).toHaveTextContent(')');
  });

  it('never sets a figure in the mono face', () => {
    const { container } = render(<Figure fact={ratioFact} />);
    expect(container.querySelector('.tnum')).toHaveTextContent('1.12x');
    expect(container.querySelector('.ident')).toBeNull();
  });
});

describe('AgentText and AgentNote', () => {
  it('renders fact references as figures and never prints the reference', () => {
    render(
      <FactsProvider facts={facts}>
        <AgentText text="Coverage calculates to {{fact:F-2}} on revenue of {{fact:F-1}}." />
      </FactsProvider>,
    );
    expect(screen.getByRole('button', { name: /1\.12x/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /\$29,480,000/ })).toBeInTheDocument();
    expect(screen.queryByText(/\{\{fact/)).toBeNull();
  });

  it('shows an unresolved reference instead of hiding it', () => {
    render(<AgentText text="Leverage is {{fact:F-404}}." />);
    expect(screen.getByText(/unresolved F-404/)).toBeInTheDocument();
  });

  it('marks agent writing as a draft until a person approves it', () => {
    const { rerender } = render(<AgentNote agent="Covenant Agent" headline="Recommends escalate" body="Needs a credit officer." state="draft" />);
    expect(screen.getByText('Draft, not yet approved')).toBeInTheDocument();
    rerender(<AgentNote agent="Covenant Agent" headline="Recommends resolve" body="Explained by terms on file." state="approved" approvedBy="Maya Okafor" />);
    expect(screen.getByText('Approved by Maya Okafor')).toBeInTheDocument();
  });
});

describe('StatusDot and Stepper', () => {
  it('always pairs the dot with a word', () => {
    render(<StatusDot tone="breach">Breach</StatusDot>);
    expect(screen.getByText('Breach')).toBeVisible();
  });

  it('marks the stage waiting for a person as the current step', () => {
    render(
      <Stepper
        label="Cycle"
        steps={[
          { id: 'a', label: 'Intake', status: 'done' },
          { id: 'b', label: 'Covenant testing', status: 'needs_person' },
          { id: 'c', label: 'Signals', status: 'pending' },
        ]}
      />,
    );
    const current = screen.getAllByRole('listitem').find((item) => item.getAttribute('aria-current') === 'step');
    expect(current).toHaveTextContent('Covenant testing');
    expect(current).toHaveTextContent('Needs a person');
  });
});

describe('DataTable', () => {
  const rows = [
    { id: 'a', name: 'Total leverage', headroom: 11.4 },
    { id: 'b', name: 'Fixed charge coverage', headroom: -6.7 },
    { id: 'c', name: 'Current ratio', headroom: 20.8 },
  ];
  const columns = [
    { id: 'name', header: 'Covenant', rowHeader: true, sortValue: (row: (typeof rows)[number]) => row.name, cell: (row: (typeof rows)[number]) => row.name },
    {
      id: 'headroom',
      header: 'Headroom',
      align: 'right' as const,
      sortValue: (row: (typeof rows)[number]) => row.headroom,
      cell: (row: (typeof rows)[number]) => `${row.headroom}%`,
    },
  ];
  const names = () => screen.getAllByRole('rowheader').map((cell) => cell.textContent);

  it('sorts when a column head is activated and reports the direction', async () => {
    render(<DataTable caption="Covenants" data={rows} columns={columns} getRowId={(row) => row.id} />);
    expect(names()).toEqual(['Total leverage', 'Fixed charge coverage', 'Current ratio']);
    await userEvent.click(screen.getByRole('button', { name: 'Headroom' }));
    expect(names()).toEqual(['Fixed charge coverage', 'Total leverage', 'Current ratio']);
    expect(screen.getByRole('columnheader', { name: 'Headroom' })).toHaveAttribute('aria-sort', 'ascending');
    await userEvent.click(screen.getByRole('button', { name: 'Headroom' }));
    expect(names()[0]).toBe('Current ratio');
  });

  it('moves row focus with the arrow keys and activates with Enter', async () => {
    const onActivate = vi.fn();
    render(<DataTable caption="Covenants" data={rows} columns={columns} getRowId={(row) => row.id} onRowActivate={onActivate} />);
    const body = screen.getAllByRole('row').slice(1);
    body[0]?.focus();
    await userEvent.keyboard('{ArrowDown}');
    expect(body[1]).toHaveFocus();
    await userEvent.keyboard('{End}');
    expect(body[2]).toHaveFocus();
    await userEvent.keyboard('{Enter}');
    expect(onActivate).toHaveBeenCalledWith(rows[2]);
  });
});

describe('WorkItemCard', () => {
  it('offers exactly one primary decision and keeps the others behind a menu', async () => {
    const onDecide = vi.fn();
    render(
      <WorkItemCard
        typeLabel="Covenant breach"
        itemId="WI-1"
        severity={{ tone: 'attention', label: 'Critical' }}
        breach
        subject="Brightwater Fastener Co."
        question="How should the bank respond?"
        evidence={[{ kind: 'extracted', label: 'Credit Agreement', detail: 'page 58' }]}
        decisions={[
          { id: 'escalate', label: 'Escalate to credit officer', primary: true },
          { id: 'request', label: 'Request a document' },
        ]}
        onDecide={onDecide}
        requiresSecondPerson
      />,
    );
    expect(screen.getByRole('heading', { name: 'How should the bank respond?' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Escalate to credit officer' }));
    expect(onDecide).toHaveBeenCalledWith(expect.objectContaining({ id: 'escalate' }));
    await userEvent.click(screen.getByRole('button', { name: 'Other decisions' }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Request a document' }));
    expect(onDecide).toHaveBeenLastCalledWith(expect.objectContaining({ id: 'request' }));
  });
});

describe('CommandPalette', () => {
  function Harness({ run }: { run: (id: string) => void }) {
    const [open, setOpen] = useState(false);
    useCommandPaletteShortcut(() => setOpen((value) => !value));
    return (
      <CommandPalette
        open={open}
        onOpenChange={setOpen}
        commands={[
          { id: 'queue', group: 'Go to', label: 'Command centre', run: () => run('queue') },
          { id: 'portfolio', group: 'Go to', label: 'Portfolio', run: () => run('portfolio') },
          { id: 'bw', group: 'Borrowers', label: 'Brightwater Fastener Co.', run: () => run('bw') },
        ]}
      />
    );
  }

  it('opens on Ctrl-K, filters as you type and runs the highlighted command on Enter', async () => {
    const run = vi.fn();
    render(<Harness run={run} />);
    expect(screen.queryByRole('combobox')).toBeNull();
    await userEvent.keyboard('{Control>}k{/Control}');
    const input = await screen.findByRole('combobox', { name: 'Search' });
    expect(input).toHaveFocus();
    expect(screen.getAllByRole('option')).toHaveLength(3);
    await userEvent.type(input, 'bright');
    expect(screen.getAllByRole('option')).toHaveLength(1);
    await userEvent.keyboard('{Enter}');
    expect(run).toHaveBeenCalledWith('bw');
    expect(screen.queryByRole('combobox')).toBeNull();
  });

  it('moves the highlight with the arrow keys', async () => {
    const run = vi.fn();
    render(<Harness run={run} />);
    await userEvent.keyboard('{Meta>}k{/Meta}');
    await screen.findByRole('combobox');
    await userEvent.keyboard('{ArrowDown}{Enter}');
    expect(run).toHaveBeenCalledWith('portfolio');
  });
});
