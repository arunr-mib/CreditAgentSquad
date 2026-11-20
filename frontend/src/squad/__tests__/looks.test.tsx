// frontend/src/squad/__tests__/looks.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext, type AuthValue } from '@/auth/context';
import { LookMenu } from '../LookMenu';
import { applyLook, contrast, defaultLookFor, LOOK_IDS, LOOKS } from '../looks';
import { LookProvider, useLook } from '../useLook';

const TEXT = ['ink', 'ink2', 'ink3', 'squad', 'ok', 'warn', 'bad'] as const;
const SURFACES = ['ground', 'surface', 'sunk'] as const;

describe('looks', () => {
  it('has the five looks of the spec', () => {
    expect(LOOK_IDS).toEqual(['night', 'warm', 'cool', 'lavender', 'sage']);
  });

  it.each(LOOK_IDS.flatMap((id) => TEXT.flatMap((t) => SURFACES.map((s) => [id, t, s] as const))))(
    '%s: %s on %s is at least 4.5:1',
    (id, t, s) => {
      expect(contrast(LOOKS[id].vars[t], LOOKS[id].vars[s])).toBeGreaterThanOrEqual(4.5);
    },
  );

  it.each(LOOK_IDS)('%s: the ink button text and the needs-you ember hold their contrast', (id) => {
    const v = LOOKS[id].vars;
    expect(contrast(v.onInk, v.ink)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(v.ember, v.ground)).toBeGreaterThanOrEqual(3);
    expect(contrast(v.onEmber, v.ember)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(LOOK_IDS)('%s: evidence paper is the same white-ish paper in every look', (id) => {
    expect(LOOKS[id].vars.paper).toBe('#fbfaf6');
    expect(contrast(LOOKS[id].vars.paperInk, LOOKS[id].vars.paper)).toBeGreaterThanOrEqual(7);
  });

  it('defaults to Warm paper for credit officers and Night for everyone else', () => {
    expect(defaultLookFor('credit_officer')).toBe('warm');
    for (const role of ['analyst', 'portfolio_manager', 'credit_admin', 'credit_review', 'admin']) expect(defaultLookFor(role)).toBe('night');
  });

  it('applyLook sets the attribute and the variables', () => {
    applyLook('lavender');
    expect(document.documentElement.dataset.look).toBe('lavender');
    expect(document.documentElement.style.getPropertyValue('--sq-ground')).toBe(LOOKS.lavender.vars.ground);
  });
});

const user = (role: string, id = 'u-1'): ApiUser => ({ id, email: 'x@y', name: 'X', title: '', role, permissions: [] });
const auth = (u: ApiUser): AuthValue => ({ user: u, status: 'signed-in', can: () => true, signIn: async () => u, signOut: async () => {}, retry: () => {} });

function Probe() {
  const { look } = useLook();
  return <span data-testid="look">{look}</span>;
}

describe('LookProvider', () => {
  beforeEach(() => localStorage.clear());

  it('starts from the role default and remembers a switch per person', async () => {
    const view = render(
      <AuthContext.Provider value={auth(user('credit_officer'))}>
        <LookProvider>
          <Probe />
          <LookMenu />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('warm');
    await userEvent.click(screen.getByRole('button', { name: /look/i }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: /sage/i }));
    expect(screen.getByTestId('look')).toHaveTextContent('sage');
    expect(localStorage.getItem('squad.look.u-1')).toBe('sage');
    view.unmount();
    render(
      <AuthContext.Provider value={auth(user('credit_officer'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('sage');
  });

  it('still works when storage throws', () => {
    const spy = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error('blocked');
    };
    render(
      <AuthContext.Provider value={auth(user('analyst'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('night');
    Storage.prototype.getItem = spy;
  });
});
