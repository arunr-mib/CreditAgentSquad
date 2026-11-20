// frontend/src/squad/shell/SquadNav.tsx
import { Link } from '@tanstack/react-router';
import { ChevronsLeft, ChevronsRight, ChartNoAxesColumn, LogOut } from 'lucide-react';
import { SquadMark } from '../mark/SquadMark';
import { LookMenu } from '../LookMenu';
import { OVERSIGHT_ROLES } from './commands';
import type { Briefing } from '../api/types';

export interface SquadNavProps {
  collapsed: boolean;
  onToggle: () => void;
  needs: number;
  openClients: Briefing['open_clients'];
  pathname: string;
  userName: string;
  role: string;
  onSignOut: () => void;
}

export function SquadNav({ collapsed, onToggle, needs, openClients, pathname, userName, role, onSignOut }: SquadNavProps) {
  const initials = userName.split(/\s+/).map((p) => p[0]).slice(0, 2).join('');
  return (
    <aside className="sq-nav" data-collapsed={collapsed} aria-label="Credit Squad">
      <Link to="/" className="sq-navlink sq-navhome" aria-current={pathname === '/' ? 'page' : undefined}>
        <SquadMark size={collapsed ? 30 : 34} state={needs > 0 ? 'needs' : 'rest'} />
        <span className="sq-navlabel">Squad</span>
        {needs > 0 ? (
          <span className="sq-badge" aria-label={`${needs} ${needs === 1 ? 'needs' : 'need'} you`}>
            {needs}
          </span>
        ) : null}
      </Link>
      <Link to="/portfolio" className="sq-navlink" aria-current={pathname.startsWith('/portfolio') ? 'page' : undefined} title="My Portfolio">
        <ChartNoAxesColumn size={18} aria-hidden />
        <span className="sq-navlabel">My Portfolio</span>
      </Link>
      {openClients.length > 0 ? (
        <nav aria-label="Open cases" className="sq-cases">
          <p className="sq-navhead sq-navlabel">Open cases</p>
          {openClients.map((c) => (
            <Link key={c.borrower_id} to="/clients/$code" params={{ code: c.code }} className="sq-navlink" title={c.name}
              aria-current={pathname === `/clients/${c.code}` ? 'page' : undefined}>
              <span className="sq-initial" aria-hidden>{c.name[0]}</span>
              <span className="sq-navlabel">{c.name}</span>
              <span className="sq-count sq-navlabel">{c.open}</span>
            </Link>
          ))}
        </nav>
      ) : null}
      {OVERSIGHT_ROLES.includes(role) ? (
        <div className="sq-cases">
          <p className="sq-navhead sq-navlabel">Oversight</p>
          <Link to="/agent-activity" className="sq-navlink"><span className="sq-initial" aria-hidden>A</span><span className="sq-navlabel">Agent activity</span></Link>
          <Link to="/governance" className="sq-navlink"><span className="sq-initial" aria-hidden>G</span><span className="sq-navlabel">Governance</span></Link>
        </div>
      ) : null}
      <div className="sq-navfoot">
        <span className="sq-avatar" title={userName}>{initials}</span>
        <span className="sq-navlabel sq-grow">{userName}</span>
        <LookMenu />
        <button type="button" className="sq-iconbtn" onClick={onSignOut} aria-label="Sign out"><LogOut size={16} aria-hidden /></button>
        <button type="button" className="sq-iconbtn" onClick={onToggle} aria-expanded={!collapsed} aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}>
          {collapsed ? <ChevronsRight size={16} aria-hidden /> : <ChevronsLeft size={16} aria-hidden />}
        </button>
      </div>
    </aside>
  );
}
