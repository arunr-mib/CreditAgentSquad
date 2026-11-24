import { createContext, useContext } from 'react';
import type { Box } from '@/api/schema';
import type { ProvenanceKind } from '@/api/types';

/** What the source drawer can show. Every figure in the workspace opens one of these. */
export type SourceRef =
  | { type: 'fact'; id: string }
  | { type: 'calculation'; id: string; title?: string }
  | { type: 'document'; documentId: string; page: number; title?: string; quote?: string | null; boxes?: Box[]; section?: string | null; borrowerCode?: string }
  | {
      /** A figure that is not a stored fact: a field of a record, or a total of records. Says plainly what it is. */
      type: 'record';
      kind: ProvenanceKind;
      title: string;
      value: string;
      rows: Array<[string, string]>;
      note: string;
      link?: { to: string; label: string };
    };

export interface SourceApi {
  /** Opens the drawer, or goes one level deeper when it is already open. */
  open: (ref: SourceRef) => void;
  close: () => void;
  /** The source on show, if the drawer is open. */
  current: SourceRef | null;
}

export const SourceContext = createContext<SourceApi>({ open: () => {}, close: () => {}, current: null });

export function useSource(): SourceApi {
  return useContext(SourceContext);
}
