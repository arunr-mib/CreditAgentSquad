import { useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { Button, Input } from '@/design';
import { roleLabel } from '@/domain/labels';
import { Mark } from '@/shell/Wordmark';

/** The demonstration users (backend/app/seed_users.py). Listed here so a reviewer can try each role. */
const DEMO_USERS: Array<{ email: string; name: string; title: string; role: string }> = [
  { email: 'priya.raman@bankofstoic.example', name: 'Priya Raman', title: 'Senior Credit Analyst', role: 'analyst' },
  { email: 'tomas.keller@bankofstoic.example', name: 'Tomas Keller', title: 'Credit Analyst', role: 'analyst' },
  { email: 'dana.whitfield@bankofstoic.example', name: 'Dana Whitfield', title: 'Portfolio Manager', role: 'portfolio_manager' },
  { email: 'helen.strand@bankofstoic.example', name: 'Helen Strand', title: 'Senior Credit Officer', role: 'credit_officer' },
  { email: 'li.zhang@bankofstoic.example', name: 'Li Zhang', title: 'Credit Administration Lead', role: 'credit_admin' },
  { email: 'ruth.calloway@bankofstoic.example', name: 'Ruth Calloway', title: 'Credit Review Officer', role: 'credit_review' },
  { email: 'admin@bankofstoic.example', name: 'Platform Administrator', title: 'Administrator', role: 'admin' },
];
const DEMO_PASSWORD = 'squad-demo';
/** Build with VITE_DEMO_USERS=off for a deployment with real accounts: the list is then not in the page at all. */
const SHOW_DEMO_USERS = import.meta.env.VITE_DEMO_USERS !== 'off';

export function SignIn() {
  const { signIn, status, retry } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !password) {
      setProblem('Enter your email and password.');
      return;
    }
    setBusy(true);
    setProblem(null);
    try {
      await signIn(email.trim(), password);
    } catch (error) {
      setProblem(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main data-ready className="mx-auto grid min-h-screen w-full max-w-[1120px] grid-cols-[minmax(0,5fr)_minmax(0,6fr)] items-center gap-16 px-10 py-12">
      <section aria-labelledby="sign-in-title">
        <div className="flex items-center gap-2.5">
          <Mark size={24} />
          <span className="text-title font-semibold tracking-[-0.012em] text-ink">Credit Agent Squad</span>
        </div>
        <h1 id="sign-in-title" className="mt-10 text-page font-semibold tracking-[-0.018em] text-ink">
          Sign in
        </h1>
        <p className="mt-1.5 max-w-[44ch] text-prose text-pretty text-ink-700">
          Bank of Stoic, commercial lending. Agents read, spread and test. Every figure traces to its source. People decide.
        </p>
        <form onSubmit={submit} noValidate className="mt-6 max-w-[360px] space-y-3.5">
          <Input label="Email" type="email" name="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} />
          <Input
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {problem ? (
            <p role="alert" className="text-body font-medium text-amber">
              {problem}
            </p>
          ) : null}
          {status === 'unreachable' ? (
            <p role="alert" className="text-body text-ink-700">
              The server could not be reached.{' '}
              <button type="button" className="link" onClick={retry}>
                Try again
              </button>
            </p>
          ) : null}
          <Button type="submit" variant="primary" className="w-full" disabled={busy}>
            {busy ? 'Signing in' : 'Sign in'}
          </Button>
        </form>
        <p className="mt-10 text-caption text-ink-500">Synthetic data, for demonstration. No real borrower appears in this workspace.</p>
      </section>

      {SHOW_DEMO_USERS ? (
        <section aria-labelledby="demo-title" className="rounded-md border border-hairline-strong bg-surface">
          <div className="px-4 pt-3.5 pb-3">
            <h2 id="demo-title" className="text-title font-semibold text-ink">
              Demonstration users
            </h2>
            <p className="mt-0.5 text-caption text-pretty text-ink-500">
              Choose a person to fill in the form. Each role may decide different things: a breach needs a credit officer, the clock needs an administrator.
            </p>
          </div>
          <ul className="border-t border-ink">
            {DEMO_USERS.map((user) => (
              <li key={user.email} className="border-b border-hairline last:border-b-0">
                <button
                  type="button"
                  onClick={() => {
                    setEmail(user.email);
                    setPassword(DEMO_PASSWORD);
                    setProblem(null);
                  }}
                  aria-pressed={email === user.email}
                  className="group flex min-h-[38px] w-full items-center gap-4 px-4 py-1.5 text-left text-body t-colors hover:bg-hover aria-pressed:bg-cobalt-bg last:rounded-b-md"
                >
                  <span className="w-44 shrink-0 font-medium text-ink">{user.name}</span>
                  <span className="min-w-0 flex-1 text-ink-700">{user.title}</span>
                  <span className="shrink-0 text-caption text-ink-500">{roleLabel(user.role)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
