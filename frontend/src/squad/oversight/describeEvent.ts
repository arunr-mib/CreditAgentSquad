import type { LedgerEvent } from '@/api/schema';
import { formatDate } from '@/design';
import { decisionLabel, humanize, roleLabel, signalLabel, STAGE_STATUS_LABEL, stageLabel } from '@/domain/labels';

const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

/** The payload in a few plain words: the decision and its reason first, then whatever else is there. */
export function describeEvent(event: LedgerEvent, docWords: (type: string | null) => string = (t) => t ?? ''): string {
  const payload = event.payload ?? {};
  const text = (key: string) => (typeof payload[key] === 'string' && payload[key] ? (payload[key] as string) : null);
  const parts: string[] = [];
  if (text('decision')) parts.push(decisionLabel(text('decision')));
  if (text('reason')) parts.push(`“${text('reason')}”`);
  if (text('title')) parts.push(text('title') as string);
  if (text('key')) parts.push(text('key') as string);
  const covenant = text('covenant') ?? text('covenant_id');
  if (covenant) parts.push(humanize(covenant));
  const rule = text('rule') ?? text('rule_id');
  if (rule) parts.push(`${signalLabel(rule)}${text('subject') ? ` (${humanize(text('subject')).toLowerCase()})` : ''}`);
  if (text('outcome')) parts.push(humanize(text('outcome')).toLowerCase());
  if (text('stage')) {
    const status = (value: unknown) => STAGE_STATUS_LABEL[String(value) as keyof typeof STAGE_STATUS_LABEL]?.toLowerCase() ?? String(value ?? '');
    parts.push(`${stageLabel(text('stage'))}: ${status(payload.from)} to ${status(payload.to)}`);
  }
  if (text('document_type') && docWords(text('document_type'))) parts.push(docWords(text('document_type')));
  if (text('period_end')) parts.push(`period ended ${formatDate(text('period_end') as string)}`);
  if (event.action === 'clock.set' && text('to')) parts.push(`to ${formatDate(text('to') as string)}`);
  if (text('received_date')) parts.push(`received ${formatDate(text('received_date') as string)}`);
  if (text('email')) parts.push(`${text('email')}${text('role') ? `, ${roleLabel(text('role')).toLowerCase()}` : ''}`);
  if (event.document_title) parts.push(event.document_title);
  else if (text('file_name')) parts.push(text('file_name') as string);
  if (text('view')) parts.push(`“${text('view')}”`);
  if (parts.length === 0) {
    for (const [key, value] of Object.entries(payload).slice(0, 3)) {
      if (value !== null && typeof value !== 'object') parts.push(`${humanize(key).toLowerCase()} ${String(value).replace(UUID, (id) => id.slice(0, 8))}`);
    }
  }
  return parts.join(' · ');
}
