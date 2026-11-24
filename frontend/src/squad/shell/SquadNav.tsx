// frontend/src/squad/shell/SquadNav.tsx
import { Link } from '@tanstack/react-router';
import { ChevronsLeft, ChevronsRight, ChartNoAxesColumn, FolderOpen, Landmark, LogOut, Presentation, Stamp } from 'lucide-react';
import { SquadMark } from '../mark/SquadMark';
import { LookMenu } from '../LookMenu';
import type { Briefing } from '../api/types';

export interface SquadNavProps {
  collapsed: boolean;
  onToggle: () => void;
  needs: number;
  showApprovals: boolean;
  openClients: Briefing['open_clients'];
  pathname: string;
  userName: string;
  oversight: boolean;
  onSignOut: () => void;
}

export function SquadNav({ collapsed, onToggle, needs, showApprovals, openClients, pathname, userName, oversight, onSignOut }: SquadNavProps) {
  const initials = userName.split(/\s+/).map((p) => p[0]).slice(0, 2).join('');
  return (
    <aside className="sq-nav" data-collapsed={collapsed} aria-label="Credit Squad">
      <p className="sq-product sq-navlabel">Credit Squad</p>
      <Link to="/" className="sq-navlink sq-navhome" title="Squad" aria-current={pathname === '/' ? 'page' : undefined}>
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
      {showApprovals ? (
        <Link to="/approvals" className="sq-navlink" aria-current={pathname.startsWith('/approvals') ? 'page' : undefined} title="Approvals">
          <Stamp size={18} aria-hidden />
          <span className="sq-navlabel">Approvals</span>
        </Link>
      ) : null}
      <Link to="/review-room" className="sq-navlink" aria-current={pathname.startsWith('/review-room') ? 'page' : undefined} title="Review room">
        <Presentation size={18} aria-hidden />
        <span className="sq-navlabel">Review room</span>
      </Link>
      {openClients.length > 0 && collapsed ? (
        <button type="button" className="sq-navlink sq-navbtn" onClick={onToggle} title="Clients with open cases"
          aria-label={`Clients with open cases: ${openClients.length}`}>
          <FolderOpen size={18} aria-hidden />
          <span className="sq-count">{openClients.length}</span>
        </button>
      ) : null}
      {openClients.length > 0 && !collapsed ? (
        <nav aria-label="Clients with open cases" className="sq-cases">
          <p className="sq-navhead sq-navlabel">Clients with open cases</p>
          {openClients.map((c) => (
            <Link key={c.borrower_id} to="/clients/$code" params={{ code: c.code }} className="sq-navlink" title={c.name}
              aria-current={pathname === `/clients/${c.code}` ? 'page' : undefined}>
              <span className="sq-navlabel sq-grow">{c.name}</span>
              <span className="sq-count sq-navlabel">{c.open}</span>
            </Link>
          ))}
        </nav>
      ) : null}
      {oversight ? (
        <Link to="/oversight" className="sq-navlink" title="Oversight" aria-current={pathname.startsWith('/oversight') ? 'page' : undefined}>
          <Landmark size={18} aria-hidden />
          <span className="sq-navlabel">Oversight</span>
        </Link>
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
