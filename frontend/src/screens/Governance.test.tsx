import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { PolicyRegister, RolesAndPermissions } from '@/api/schema';
import { PolicyTables, RolesMatrix } from './Governance';

/** The shape `/governance/roles` returns, with the grants of backend/app/core/roles.py for the permissions used here. */
const TABLE: RolesAndPermissions = {
  roles: [
    { id: 'analyst', label: 'Credit analyst', people: 5 },
    { id: 'portfolio_manager', label: 'Portfolio manager', people: 5 },
    { id: 'credit_officer', label: 'Credit officer', people: 3 },
    { id: 'credit_admin', label: 'Credit administration', people: 2 },
    { id: 'credit_review', label: 'Credit review', people: 1 },
    { id: 'admin', label: 'Administrator', people: 1 },
  ],
  permissions: [
    { id: 'view', label: 'see the workspace', group: 'Reading', second_person: false },
    { id: 'prepare_terms', label: 'prepare terms', group: 'Terms', second_person: false },
    { id: 'approve_terms', label: 'approve terms', group: 'Terms', second_person: true },
    { id: 'decide_breach', label: 'decide the response to a breach', group: 'Exceptions', second_person: false },
  ],
  grants: {
    analyst: ['view', 'prepare_terms'],
    portfolio_manager: ['view'],
    credit_officer: ['view', 'approve_terms', 'decide_breach'],
    credit_admin: ['view', 'prepare_terms', 'approve_terms'],
    credit_review: ['view'],
    admin: ['view', 'prepare_terms', 'approve_terms', 'decide_breach'],
  },
  second_person: { rule: 'A person cannot approve their own work.', applies_to: [{ permission: 'approve_terms', what: 'Loan terms', detail: 'The person who prepared a terms version cannot approve it.', source: 'domain/terms_service.py' }] },
};

function cell(container: HTMLElement, permission: string, role: string) {
  return container.querySelector<HTMLElement>(`[data-roles-matrix] [data-permission="${permission}"] td[data-role="${role}"]`)!;
}

describe('the role and permission matrix', () => {
  it('marks a known grant, leaves a known non-grant unmarked, and shows the six roles the API returns', () => {
    const { container } = render(<RolesMatrix table={TABLE} ownRole="analyst" />);
    const matrix = container.querySelector<HTMLElement>('[data-roles-matrix]')!;

    expect(within(matrix).getAllByRole('columnheader').slice(1).map((header) => header.dataset.role)).toEqual(['analyst', 'portfolio_manager', 'credit_officer', 'credit_admin', 'credit_review', 'admin']);
    expect(matrix).not.toHaveTextContent(/committee/i);

    // only a credit officer and the administrator decide the response to a breach
    expect(cell(container, 'decide_breach', 'credit_officer')).toHaveAttribute('data-grant', 'yes');
    expect(cell(container, 'decide_breach', 'credit_officer')).toHaveTextContent('May');
    expect(cell(container, 'decide_breach', 'admin')).toHaveAttribute('data-grant', 'yes');
    expect(cell(container, 'decide_breach', 'analyst')).toHaveAttribute('data-grant', 'no');
    expect(cell(container, 'decide_breach', 'analyst')).toHaveTextContent('May not');

    // every cell is what the grants say, nothing more
    for (const role of TABLE.roles) {
      for (const permission of TABLE.permissions) {
        const held = TABLE.grants[role.id]!.includes(permission.id);
        expect(cell(container, permission.id, role.id).dataset.grant === 'no').toBe(!held);
      }
    }
  });

  it('marks the approvals a person cannot give on their own work', () => {
    const { container } = render(<RolesMatrix table={TABLE} ownRole={null} />);
    expect(cell(container, 'approve_terms', 'credit_officer')).toHaveAttribute('data-grant', 'second');
    expect(cell(container, 'approve_terms', 'credit_officer')).toHaveTextContent('May, but never on their own work');
    expect(cell(container, 'approve_terms', 'analyst')).toHaveAttribute('data-grant', 'no');
    expect(cell(container, 'prepare_terms', 'analyst')).toHaveAttribute('data-grant', 'yes');
    const approve = container.querySelector<HTMLElement>('[data-roles-matrix] [data-permission="approve_terms"]')!;
    expect(within(approve).getByRole('rowheader')).toHaveTextContent('Approve termsA second person is required');
  });

  it('names the reader’s own role and, for a small screen, lists who holds each permission', () => {
    const { container } = render(<RolesMatrix table={TABLE} ownRole="credit_officer" />);
    expect(container.querySelector('[data-roles-matrix] th[data-role="credit_officer"]')).toHaveTextContent('Your roleCredit officer3 people');
    expect(container.querySelector('[data-roles-matrix] th[data-role="credit_review"]')).toHaveTextContent('Credit review1 person');
    const list = container.querySelector<HTMLElement>('[data-roles-list]')!;
    expect(within(list).getByText('Decide the response to a breach').closest('li')).toHaveTextContent('Credit officer (your role) · Administrator');
  });
});

const REGISTER: PolicyRegister = {
  sections: [
    {
      id: 'agent_limits',
      title: 'Limits on agents',
      summary: 'Applied by code after the agent answers.',
      rules: [{ id: 'margin_floor', rule: 'Margin floor', setting: '15%', effect: 'A resolve becomes an escalate.', source: 'guardrails/policy.py', kind: 'text', state: null }],
    },
    {
      id: 'records',
      title: 'Records and access',
      summary: 'What is kept.',
      rules: [
        { id: 'ledger_append_only', rule: 'The ledger is append-only', setting: 'Not held for this connection', effect: 'The role could switch it off.', source: 'core/ledger.py', kind: 'text', state: 'attention' },
        { id: 'facts', rule: 'Facts are never edited', setting: 'Always', effect: 'A correction is a new fact.', source: 'domain/facts_service.py', kind: 'text', state: null },
      ],
    },
    {
      id: 'versions',
      title: 'Calculation versions',
      summary: 'Every calculation stores its version.',
      rules: [{ id: 'signals', rule: 'Early warning rules', setting: 'signals-1', effect: 'The rule table.', source: 'calc/signals.py', kind: 'ident', state: null }],
    },
  ],
  signal_rules: { version: 'signals-1', rules: [{ id: 'net_loss', name: 'Net loss', severity: 'high', trigger: 'Net income over the trailing twelve months below $0' }] },
  agents: [{ name: 'covenant', version: '1', purpose: 'Investigate a covenant exception.', model: 'claude-opus-5-5', effort: 'high', max_steps: 12, tools: ['a', 'b'], prompt_sha256: 'abcdef0123456789' }],
};

describe('the policy rules', () => {
  it('sets out each rule with the setting the API returns, and tags only a rule that does not hold', () => {
    const { container } = render(<PolicyTables register={REGISTER} />);
    const limits = screen.getByRole('table', { name: 'Limits on agents' });
    expect(within(limits).getByRole('rowheader', { name: 'Margin floor' })).toBeVisible();
    expect(within(limits).getByText('15%')).toBeVisible();
    expect(within(limits).getByText('guardrails/policy.py')).toHaveClass('ident');

    const records = screen.getByRole('table', { name: 'Records and access' });
    expect(within(records).getByText('Not held for this connection').closest('[data-tag]')).toHaveAttribute('data-tag', 'attention');
    expect(container.querySelectorAll('[data-tag]')).toHaveLength(1);

    expect(within(screen.getByRole('table', { name: 'Calculation versions' })).getByText('signals-1')).toHaveClass('ident');
    expect(within(screen.getByRole('table', { name: 'Early warning rules' })).getByText('Net income over the trailing twelve months below $0')).toBeVisible();
    const agents = screen.getByRole('table', { name: 'Agent versions in this build' });
    expect(within(agents).getByRole('rowheader', { name: 'Covenant' })).toBeVisible();
    expect(within(agents).getByText('abcdef012345')).toBeVisible();
  });
});
