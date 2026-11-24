/** Whose client this is, and whether the person looking may act on it. `lookOnly` is the engine's own refusal
 * (the client list sends it), so this line and the server cannot disagree. */
export function ClientOwner({ analyst, lookOnly }: { analyst: string | null | undefined; lookOnly: string | null | undefined }) {
  if (analyst === undefined && lookOnly === undefined) return null; // an older server sends neither
  return (
    <div>
      <p className="sq-faint">{analyst ? `Analyst: ${analyst}` : 'No analyst is named'}</p>
      {lookOnly ? <p role="note" className="sq-muted">You can look at this client, not act on it. {lookOnly}</p> : null}
    </div>
  );
}
