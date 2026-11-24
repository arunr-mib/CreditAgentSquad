// frontend/src/squad/__tests__/looks.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiUser } from '@/api/schema';
import { AuthContext, type AuthValue } from '@/auth/context';
import { LookMenu } from '../LookMenu';
import { applyLook, contrast, defaultLookFor, LOOK_IDS, LOOKS } from '../looks';
import { LookProvider, useLook } from '../useLook';

const TEXT = ['ink', 'ink2', 'ink3', 'squad', 'ok', 'warn', 'bad'] as const;
const SURFACES = ['ground', 'surface', 'sunk', 'squadSoft'] as const;

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
    for (const s of ['ground', 'surface', 'sunk'] as const) expect(contrast(v.ember, v[s])).toBeGreaterThanOrEqual(3);
    expect(contrast(v.onEmber, v.ember)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(LOOK_IDS)('%s: evidence paper is the same white-ish paper in every look', (id) => {
    expect(LOOKS[id].vars.paper).toBe('#fbfaf6');
    expect(contrast(LOOKS[id].vars.paperInk, LOOKS[id].vars.paper)).toBeGreaterThanOrEqual(7);
  });

  it.each(LOOK_IDS)('%s: control borders (lineStrong) are at least 3:1 on ground and surface', (id) => {
    const v = LOOKS[id].vars;
    expect(contrast(v.lineStrong, v.ground)).toBeGreaterThanOrEqual(3);
    expect(contrast(v.lineStrong, v.surface)).toBeGreaterThanOrEqual(3);
  });

  it('defaults to Warm paper for credit officers and Night for everyone else', () => {
    expect(defaultLookFor('credit_officer')).toBe('warm');
    for (const role of ['analyst', 'portfolio_manager', 'credit_admin', 'credit_review', 'admin']) expect(defaultLookFor(role)).toBe('night');
  });

  it('applyLook sets the attribute and variables on the given root, not the page', () => {
    const el = document.createElement('div');
    applyLook('lavender', el);
    expect(el.dataset.look).toBe('lavender');
    expect(el.style.getPropertyValue('--sq-ground')).toBe(LOOKS.lavender.vars.ground);
    expect(document.documentElement.dataset.look).toBeUndefined();
  });

  it('applyLook defaults to the .sq-root container', () => {
    const el = document.createElement('div');
    el.className = 'sq-root';
    document.body.append(el);
    applyLook('sage');
    expect(el.dataset.look).toBe('sage');
    expect(document.documentElement.dataset.look).toBeUndefined();
    el.remove();
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
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    render(
      <AuthContext.Provider value={auth(user('analyst'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    expect(screen.getByTestId('look')).toHaveTextContent('night');
    spy.mockRestore();
  });

  it('re-resolves the look when a different person signs in', () => {
    localStorage.setItem('squad.look.u-3', 'sage');
    const tree = (u: ApiUser) => (
      <AuthContext.Provider value={auth(u)}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>
    );
    const view = render(tree(user('analyst', 'u-1')));
    expect(screen.getByTestId('look')).toHaveTextContent('night');
    view.rerender(tree(user('credit_officer', 'u-2')));
    expect(screen.getByTestId('look')).toHaveTextContent('warm');
    view.rerender(tree(user('analyst', 'u-3')));
    expect(screen.getByTestId('look')).toHaveTextContent('sage');
  });

  it('puts the look on the Squad root and removes it on unmount', () => {
    const view = render(
      <AuthContext.Provider value={auth(user('analyst'))}>
        <LookProvider>
          <Probe />
        </LookProvider>
      </AuthContext.Provider>,
    );
    const root = document.querySelector('.sq-root') as HTMLElement;
    expect(root.dataset.look).toBe('night');
    expect(document.documentElement.dataset.look).toBeUndefined();
    view.unmount();
    expect(root.dataset.look).toBeUndefined();
    expect(root.style.getPropertyValue('--sq-ground')).toBe('');
  });
});
