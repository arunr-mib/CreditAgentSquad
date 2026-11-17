import { Activity, Building2, CalendarDays, ChartNoAxesColumn, Inbox, Landmark, Presentation, type LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Paths that also mark this item as current. */
  match: string[];
  description: string;
}

export const NAV: NavItem[] = [
  { label: 'Command centre', to: '/showcase/command-centre', icon: Inbox, match: ['/showcase/command-centre'], description: 'Work queue by risk and due date' },
  {
    label: 'Portfolio',
    to: '/portfolio',
    icon: ChartNoAxesColumn,
    match: ['/portfolio'],
    description: 'Exposure, covenant status, signals and trends across the book',
  },
  {
    label: 'Borrowers',
    to: '/showcase/covenants',
    icon: Building2,
    match: ['/showcase/covenants', '/showcase/spread'],
    description: 'Each borrower: loans, documents, spreads, covenants, reviews',
  },
  { label: 'Calendar', to: '/calendar', icon: CalendarDays, match: ['/calendar'], description: 'Reporting requirements: due, received and overdue' },
  { label: 'Review room', to: '/review-room', icon: Presentation, match: ['/review-room'], description: 'Review sheets before, during and after the meeting' },
  { label: 'Agent activity', to: '/agent-activity', icon: Activity, match: ['/agent-activity'], description: 'Runs, steps and guardrail notes' },
  { label: 'Governance', to: '/governance', icon: Landmark, match: ['/governance'], description: 'Ledger, agent and method versions, scorecard and policy' },
];
