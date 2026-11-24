import { useDocumentTypeWords, useSignalWordsTable } from './api/hooks';

/** Document types and signal rules in the server's words (`GET /words/document-types`, `/words/signals`). The browser
 * keeps no list: before a table arrives, or for a key the table lacks, the stored key is shown as the words it is. */
const humanise = (type: string) => { const t = type.replace(/_/g, ' '); return t.charAt(0).toUpperCase() + t.slice(1); };

export function useDocWords(): (type: string | null | undefined) => string {
  const table = useDocumentTypeWords().data;
  return (type) => (!table ? '' : !type ? table.unclassified : (table.types[type] ?? humanise(type)));
}

export function useSignalWords(): (rule: string) => string {
  const table = useSignalWordsTable().data;
  return (rule) => (!table ? '' : (table.rules?.[rule] ?? humanise(rule)));
}

export function DocType({ type }: { type: string | null }) {
  const words = useDocWords();
  return <>{words(type)}</>;
}
