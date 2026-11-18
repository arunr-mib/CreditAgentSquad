import { Link } from '@tanstack/react-router';
import { ChevronDown, LogOut, Palette } from 'lucide-react';
import { DropdownMenu } from 'radix-ui';
import { errorMessage } from '@/api/client';
import { useAuth } from '@/auth/context';
import { DEMO_PASSWORD, DEMO_USERS, SHOW_DEMO_USERS, type DemoUser } from '@/auth/demoUsers';
import { useToast } from '@/design';
import { roleLabel } from '@/domain/labels';
import { cx } from '@/lib/cx';

function initials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : '')).toUpperCase();
}

/** A person's initials on a square. Ink for the person signed in, a quiet outline for anyone else. */
function Initials({ name, signedIn = false }: { name: string; signedIn?: boolean }) {
  return (
    <span
      aria-hidden
      className={cx(
        'flex size-7 shrink-0 items-center justify-center rounded-sm text-micro font-semibold tracking-wide',
        signedIn ? 'bg-ink text-canvas' : 'border border-hairline-strong bg-canvas text-ink-700',
      )}
    >
      {initials(name)}
    </span>
  );
}

const itemClass = 'flex cursor-pointer items-center gap-2.5 rounded-xs px-2 text-body text-ink outline-none select-none data-[highlighted]:bg-cobalt-bg';

export interface UserMenuProps {
  /** The demonstration users offered under "Switch demo user". Empty, or left out where demo users are off, hides the list. */
  demoUsers?: DemoUser[];
}

/**
 * Who is signed in, with their role as plain text, and the way out. Where demonstration users are
 * enabled, the menu also signs in as another of them: a real sign-out and sign-in as that person,
 * never a change of role on the same identity, so the ledger always names who acted.
 */
export function UserMenu({ demoUsers = SHOW_DEMO_USERS ? DEMO_USERS : [] }: UserMenuProps) {
  const { user, signOut, signIn } = useAuth();
  const toast = useToast();
  if (!user) return null;
  const others = demoUsers.filter((person) => person.email !== user.email);

  async function switchTo(person: DemoUser) {
    // End this person's session first; if the server cannot be told, the new sign-in replaces the cookie anyway.
    await signOut().catch(() => undefined);
    try {
      const next = await signIn(person.email, DEMO_PASSWORD);
      toast({ title: `Signed in as ${next.name}`, description: `${roleLabel(next.role)}. Everything on screen is now read with this person’s authority.` });
    } catch (error) {
      toast({
        title: `Could not sign in as ${person.name}`,
        description: `${errorMessage(error)} You are signed out; sign in again to continue.`,
        tone: 'attention',
      });
    }
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="inline-flex h-9 shrink-0 items-center gap-2.5 rounded-sm py-1 pr-1.5 pl-1 text-left t-colors hover:bg-hover data-[state=open]:bg-hover"
        >
          <Initials name={user.name} signedIn />
          <span className="leading-tight @max-[760px]:hidden">
            <span data-user-name className="block text-caption font-semibold whitespace-nowrap text-ink">
              {user.name}
            </span>
            <span data-user-role className="block text-micro whitespace-nowrap text-ink-500">
              {roleLabel(user.role)}
            </span>
          </span>
          <span className="sr-only @min-[760px]:hidden">
            {user.name}, {roleLabel(user.role)}
          </span>
          <span className="sr-only">Account menu</span>
          <ChevronDown size={13} aria-hidden className="text-ink-500" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          collisionPadding={8}
          className="anim-pop z-50 max-h-[var(--radix-dropdown-menu-content-available-height)] w-72 max-w-[calc(100vw-16px)] overflow-y-auto rounded-md border border-hairline-strong bg-surface p-1 shadow-raised"
        >
          <DropdownMenu.Label className="flex items-start gap-2.5 px-2 pt-2 pb-2">
            <Initials name={user.name} signedIn />
            <span className="min-w-0">
              <span className="eyebrow block">Signed in as</span>
              <span className="block text-body font-semibold text-ink">{user.name}</span>
              <span className="block text-caption text-ink-700">
                {user.title} · {roleLabel(user.role)}
              </span>
              <span className="block text-caption break-all text-ink-500">{user.email}</span>
            </span>
          </DropdownMenu.Label>
          {others.length > 0 ? (
            <>
              <DropdownMenu.Separator className="my-1 border-t border-hairline" />
              <DropdownMenu.Group>
                <DropdownMenu.Label className="px-2 pt-1.5 pb-1">
                  <span className="eyebrow block">Switch demo user</span>
                  <span className="block text-caption text-pretty text-ink-500">Signs you out, then in as that person.</span>
                </DropdownMenu.Label>
                {others.map((person) => (
                  <DropdownMenu.Item
                    key={person.email}
                    data-demo-user={person.email}
                    onSelect={() => void switchTo(person)}
                    className={cx(itemClass, 'py-1.5')}
                  >
                    <Initials name={person.name} />
                    <span className="min-w-0 flex-1 leading-tight">
                      <span className="block font-medium">{person.name}</span>
                      <span className="block text-caption text-ink-500">{roleLabel(person.role)}</span>
                    </span>
                  </DropdownMenu.Item>
                ))}
              </DropdownMenu.Group>
            </>
          ) : null}
          <DropdownMenu.Separator className="my-1 border-t border-hairline" />
          <DropdownMenu.Item asChild className={cx(itemClass, 'h-8')}>
            <Link to="/design">
              <Palette size={14} aria-hidden className="text-ink-500" />
              Design system
            </Link>
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={() =>
              void signOut().catch(() =>
                toast({ title: 'Signed out on this device', description: 'The server could not be told; the session will expire by itself.' }),
              )
            }
            className={cx(itemClass, 'h-8')}
          >
            <LogOut size={14} aria-hidden className="text-ink-500" />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
