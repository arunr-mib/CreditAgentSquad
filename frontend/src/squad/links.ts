// frontend/src/squad/links.ts
/** Where "Open in client file" and a thread go. One place, so Phase 4b retargets the client file in one edit. */
export type ClientFileView = 'documents' | 'covenants' | 'spreads' | 'timeline';

export function clientFile(code: string, view?: ClientFileView): string {
  return view ? `/borrowers/${code}/${view}` : `/borrowers/${code}`;
}

export function threadHref(code: string, caseId?: string) {
  return { to: '/clients/$code' as const, params: { code }, search: caseId ? { case: caseId } : {} };
}
