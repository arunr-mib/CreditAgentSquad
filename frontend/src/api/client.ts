/**
 * The one way the workspace talks to /api/v1. Cookie session; JSON in and out.
 * A 401 anywhere means the session has ended: listeners (the auth provider) send the person to sign in.
 */
export const API = '/api/v1';

export class ApiError extends Error {
  readonly status: number;
  /** The server's own words, shown to the person as they are. */
  readonly detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();

/** Called when any request (other than sign-in itself) is refused for lack of a session. */
export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : String(entry))).join('; ');
  }
  return fallback;
}

export type Query = Record<string, string | number | boolean | null | undefined>;

export function withQuery(path: string, query?: Query): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  const text = params.toString();
  return text ? `${path}?${text}` : path;
}

interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  query?: Query;
  /** Sign-in and "who am I" handle their own 401. */
  quiet401?: boolean;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(withQuery(`${API}${path}`, options.query), {
      method: options.method ?? 'GET',
      credentials: 'same-origin',
      headers: options.body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch {
    throw new ApiError(0, 'The server could not be reached. Check that the API is running, then try again.');
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!response.ok) {
    if (response.status === 401 && !options.quiet401) for (const listener of unauthorizedListeners) listener();
    throw new ApiError(response.status, detailOf(body, `The server answered ${response.status}.`));
  }
  return body as T;
}

export const get = <T>(path: string, query?: Query, signal?: AbortSignal) => request<T>(path, { query, signal });
export const post = <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body ?? {} });

/** What to tell a person when a request fails. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.detail;
  if (error instanceof Error) return error.message;
  return 'Something went wrong.';
}
