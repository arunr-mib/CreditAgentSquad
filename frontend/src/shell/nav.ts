import { Activity, Building2, CalendarDays, ChartNoAxesColumn, Inbox, Landmark, Presentation, type LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  description: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

/** The rail, in two groups: the daily work, then the record of what agents and people did. */
export const NAV_SECTIONS: NavSection[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'Command centre', to: '/command-centre', icon: Inbox, description: 'Work queue by risk and due date' },
      { label: 'Portfolio', to: '/portfolio', icon: ChartNoAxesColumn, description: 'Exposure, covenant status and signals across the book' },
      { label: 'Borrowers', to: '/borrowers', icon: Building2, description: 'Each borrower: loans, documents, spreads, covenants, reviews' },
      { label: 'Calendar', to: '/calendar', icon: CalendarDays, description: 'Reporting requirements: due, received and overdue' },
      { label: 'Review room', to: '/review-room', icon: Presentation, description: 'Review sheets before, during and after the meeting' },
    ],
  },
  {
    label: 'Oversight',
    items: [
      { label: 'Agent activity', to: '/agent-activity', icon: Activity, description: 'Runs, steps and guardrail notes' },
      { label: 'Governance', to: '/governance', icon: Landmark, description: 'Ledger, agent versions and the simulated clock' },
    ],
  },
];

export const NAV: NavItem[] = NAV_SECTIONS.flatMap((section) => section.items);
