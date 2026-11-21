import { useDocumentTypeWords } from './api/hooks';

/** Document types in the server's words (`GET /words/document-types`, one table in `app/squad/words.py`). The browser
 * keeps no list: before the table arrives, or for a type the table lacks, the stored type is shown as the identifier
 * it is. Task 5 points every remaining user of the old `docTypeLabel` here and deletes that table. */
export function useDocWords(): (type: string | null | undefined) => string {
  const table = useDocumentTypeWords().data;
  return (type) => (!table ? '' : !type ? table.unclassified : (table.types[type] ?? type));
}

export function DocType({ type }: { type: string | null }) {
  const words = useDocWords();
  const text = words(type);
  return text === type ? <span className="sq-mono">{type}</span> : <>{text}</>;
}
