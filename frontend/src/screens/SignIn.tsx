import { useState, type FormEvent } from 'react';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { DEMO_PASSWORD, DEMO_USERS, SHOW_DEMO_USERS } from '@/auth/demoUsers';
import { Button, Input } from '@/design';
import { roleLabel } from '@/domain/labels';
import { Mark } from '@/shell/Wordmark';

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
    <main
      data-ready
      className="mx-auto grid min-h-screen w-full max-w-[1120px] grid-cols-1 content-center items-center gap-10 px-4 py-8 sm:px-10 md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] md:gap-16 md:py-12"
    >
      <section aria-labelledby="sign-in-title">
        <div className="flex items-center gap-2.5">
          <Mark size={24} />
          <span className="text-title font-semibold tracking-[-0.012em] text-ink">Credit Squad</span>
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
                  className="group flex min-h-[38px] w-full flex-wrap items-center gap-x-4 px-4 py-1.5 text-left text-body t-colors hover:bg-hover aria-pressed:bg-cobalt-bg last:rounded-b-md sm:flex-nowrap"
                >
                  <span className="w-full shrink-0 font-medium text-ink sm:w-44">{user.name}</span>
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
