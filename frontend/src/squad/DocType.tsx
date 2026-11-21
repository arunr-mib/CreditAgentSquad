import { useDocumentTypeWords } from './api/hooks';

/** Document types in the server's words (`GET /words/document-types`, one table in `app/squad/words.py`). The browser
 * keeps no list: before the table arrives, or for a type the table lacks, the stored type is shown as the identifier
 * it is. Task 5 points every remaining user of the old `docTypeLabel` here and deletes that table. */
/** The server's fallback for a type its table lacks (`document_type_words` in `app/squad/words.py`): the same rule, so a
 * thread message and a client file row read the same. */
const humanise = (type: string) => { const t = type.replace(/_/g, ' '); return t.charAt(0).toUpperCase() + t.slice(1); };

export function useDocWords(): (type: string | null | undefined) => string {
  const table = useDocumentTypeWords().data;
  return (type) => (!table ? '' : !type ? table.unclassified : (table.types[type] ?? humanise(type)));
}

export function DocType({ type }: { type: string | null }) {
  const words = useDocWords();
  return <>{words(type)}</>;
}
