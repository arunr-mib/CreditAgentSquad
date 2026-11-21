// frontend/src/squad/links.ts
/** Where the client file and a thread live. One place, so every link moves together. */
export type ClientFileView = 'overview' | 'spreads' | 'covenants' | 'documents' | 'funding' | 'loans' | 'reviews' | 'history';

export function clientFile(code: string, view?: ClientFileView): string {
  return view && view !== 'overview' ? `/clients/${code}/file/${view}` : `/clients/${code}/file`;
}

export function threadHref(code: string, caseId?: string) {
  return { to: '/clients/$code' as const, params: { code }, search: caseId ? { case: caseId } : {} };
}
