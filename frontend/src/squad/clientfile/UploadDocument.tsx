import { Link } from '@tanstack/react-router';
import { ArrowUpRight } from 'lucide-react';
import { useId, useRef, useState, type FormEvent } from 'react';
import { useUploadDocument } from '@/api/hooks';
import { Button, Card, CardHeader, fieldLabelClass, formatDate, Input } from '@/design';
import { word } from '@/api/words';
import { cx } from '@/lib/cx';
import { Refusal } from '@/repair/FigureForm';
import { Notice } from '@/screens/parts';


/**
 * File a PDF, .xlsx or .csv for the borrower. The route takes the file and an optional title and nothing else:
 * the document is filed as unclassified, and intake classifies and dates it. What the server
 * answers is shown as it is: the filed document, or its refusal.
 */
export function UploadDocument({ borrowerId, code, onClose }: { borrowerId: string; code: string; onClose?: () => void }) {
  const send = useUploadDocument(borrowerId);
  const fileId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const filed = send.data;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setProblem('Choose a document file first.');
      return;
    }
    setProblem(null);
    send.mutate(
      { file, title },
      {
        onSuccess: () => {
          setFile(null);
          setTitle('');
          if (input.current) input.current.value = '';
        },
      },
    );
  }

  return (
    <Card data-upload-document>
      <CardHeader
        as="h3"
        title="File a document"
        meta="A PDF, an Excel workbook (.xlsx) or a CSV file. It is filed as unclassified; the Intake Agent classifies and dates it when the borrower’s monitoring cycle next runs intake."
        actions={
          onClose ? (
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          ) : undefined
        }
      />
      <form onSubmit={submit} noValidate aria-label="File a document" className="border-t border-hairline px-4 pt-3 pb-4">
        <div className="grid items-start gap-3 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_auto]">
          <div>
            <label htmlFor={fileId} className={fieldLabelClass}>
              Document file
            </label>
            <input
              id={fileId}
              ref={input}
              type="file"
              accept="application/pdf,.pdf,.xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
              aria-invalid={problem ? true : undefined}
              aria-describedby={`${fileId}-note`}
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setProblem(null);
                send.reset();
              }}
              className={cx(
                'block h-8 w-full cursor-pointer rounded-sm border bg-surface pr-2 text-body text-ink-700 t-colors',
                'file:mr-3 file:h-full file:cursor-pointer file:border-0 file:border-r file:border-solid file:border-hairline-strong file:bg-canvas file:px-3 file:text-body file:font-medium file:text-ink hover:file:bg-hover',
                problem ? 'border-amber-mark' : 'border-ink-400 hover:border-ink-500',
              )}
            />
            <p id={`${fileId}-note`} className={cx('mt-1 text-caption', problem ? 'font-medium text-amber' : 'text-ink-500')}>
              {problem ?? (file ? `${file.name} is ready to file.` : 'One file at a time.')}
            </p>
          </div>
          <Input label="Title (optional)" value={title} onChange={(event) => setTitle(event.target.value)} placeholder={file?.name ?? 'The file name is used if left empty'} hint="How the document is listed." />
          <Button type="submit" variant="primary" className="md:mt-[20px]" disabled={send.isPending}>
            {send.isPending ? 'Filing' : 'File the document'}
          </Button>
        </div>
        {send.error ? <Refusal error={send.error} outcome="Not filed" className="mt-3" /> : null}
        <div aria-live="polite" data-upload-result>
          {filed ? (
            <Notice
              className="mt-3"
              tone="neutral"
              title={`Filed: ${filed.title}`}
              action={
                <Link to="/clients/$code/file/$view" params={{ code, view: 'documents' }} search={{ document: filed.id, page: 1 }} className="link inline-flex items-center gap-0.5 text-body font-medium">
                  Open it <ArrowUpRight size={12} aria-hidden />
                </Link>
              }
            >
              <span className="tnum">{filed.page_count}</span> {filed.page_count === 1 ? 'page' : 'pages'}, {word('document_reads', filed.status).toLowerCase()}
              {filed.received_date ? `, received ${formatDate(filed.received_date)}` : ''}. Unclassified until intake reads it. The receipt is in the ledger.
            </Notice>
          ) : null}
        </div>
      </form>
    </Card>
  );
}
