import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
// The build for older browsers. The default build calls methods only the newest browsers have, and where one is
// missing every page fails to draw; this one carries its own.
import type * as PdfJs from 'pdfjs-dist/legacy/build/pdf.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';
import { API } from '@/api/client';
import type { Box } from '@/api/schema';
import { cx } from '@/lib/cx';

type PdfModule = typeof PdfJs;
type PdfDocument = Awaited<ReturnType<PdfModule['getDocument']>['promise']>;

let pdfModule: Promise<PdfModule> | null = null;
const documents = new Map<string, Promise<PdfDocument>>();

/** The PDF renderer is loaded on first use, so screens without a page never pay for it. */
function loadPdf(documentId: string): Promise<PdfDocument> {
  if (!pdfModule) {
    pdfModule = import('pdfjs-dist/legacy/build/pdf.mjs').then((module) => {
      module.GlobalWorkerOptions.workerSrc = workerUrl;
      return module;
    });
    pdfModule.catch(() => (pdfModule = null)); // a renderer that failed to load is asked for again on the next try
  }
  let document = documents.get(documentId);
  if (!document) {
    document = pdfModule.then((module) => module.getDocument({ url: `${API}/documents/${documentId}/file`, withCredentials: true }).promise);
    document.catch(() => documents.delete(documentId));
    documents.set(documentId, document);
  }
  return document;
}

/**
 * The width a page can take inside `ref`, never more than `max`: a page drawn wider than its frame
 * would hide the figure it was opened for off the side of a phone.
 */
export function useFitWidth(ref: RefObject<HTMLElement | null>, max: number): number {
  const [width, setWidth] = useState(max);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === 'undefined') return;
    const measure = () => {
      const available = Math.floor(element.clientWidth) - 2; // the page's own border
      if (available > 0) setWidth(Math.min(max, available));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref, max]);
  return width;
}

export interface PageMark {
  id: string;
  /** Boxes in PDF points, origin at the top left of the page: one per printed line. */
  boxes: Box[];
  /** The figure or quote the reader came for: drawn with the strong outline and scrolled into view. */
  active?: boolean;
  label?: string;
  onSelect?: () => void;
}

export interface PdfPageProps {
  documentId: string;
  page: number;
  /** Rendered width in CSS pixels. */
  width: number;
  title: string;
  marks?: PageMark[];
  /** Show the page through a window of this height, scrolled to the active mark. */
  maxHeight?: number;
  className?: string;
}

/**
 * One page of a stored PDF, rendered from the file itself, with citations outlined on it.
 * The outline is cobalt because it is interactive context, like a selected cell; it is not a status.
 */
export function PdfPage({ documentId, page, width, title, marks = [], maxHeight, className }: PdfPageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<{ key: string; status: 'ready' | 'error'; pointWidth: number; pointHeight: number } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const key = `${documentId}:${page}:${width}:${attempt}`;
  const current = state?.key === key ? state : null;

  useEffect(() => {
    let cancelled = false;
    let task: { cancel: () => void; promise: Promise<unknown> } | null = null;
    void (async () => {
      try {
        const pdf = await loadPdf(documentId);
        const pdfPage = await pdf.getPage(page);
        if (cancelled) return;
        const base = pdfPage.getViewport({ scale: 1 });
        const ratio = Math.min(window.devicePixelRatio || 1, 3);
        const viewport = pdfPage.getViewport({ scale: (width / base.width) * ratio });
        const canvas = canvasRef.current;
        const context = canvas?.getContext('2d');
        if (!canvas || !context) return;
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        task = pdfPage.render({ canvas, canvasContext: context, viewport });
        await task.promise;
        if (!cancelled) setState({ key, status: 'ready', pointWidth: base.width, pointHeight: base.height });
      } catch (error) {
        if (!cancelled && (error as { name?: string })?.name !== 'RenderingCancelledException') {
          setState({ key, status: 'error', pointWidth: 0, pointHeight: 0 });
        }
      }
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [documentId, page, width, key]); // `key` carries the attempt: Try again draws afresh

  const scale = current?.status === 'ready' ? width / current.pointWidth : 0;
  const height = current?.status === 'ready' ? current.pointHeight * scale : Math.round(width * 1.294);
  const activeBox = marks.find((mark) => mark.active)?.boxes[0];
  const activeTop = activeBox?.[1];
  const activeLeft = activeBox?.[0];

  // Bring the cited figure into the window once the page is drawn: down to it, and across where the frame is narrower than the page.
  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller || !scale || activeTop === undefined) return;
    if (maxHeight) scroller.scrollTop = Math.max(0, activeTop * scale - maxHeight / 2);
    if (activeLeft !== undefined && scroller.scrollWidth > scroller.clientWidth) {
      scroller.scrollLeft = Math.max(0, activeLeft * scale - scroller.clientWidth / 2);
    }
  }, [scale, activeTop, activeLeft, maxHeight, key]);

  return (
    <div
      ref={scrollerRef}
      // The window scrolls, so it takes focus for keyboard scrolling.
      tabIndex={maxHeight ? 0 : undefined}
      role={maxHeight ? 'group' : undefined}
      aria-label={maxHeight ? `${title}, page ${page}` : undefined}
      data-pdf-page={current?.status ?? 'loading'}
      className={cx('relative max-w-full rounded-sm border border-hairline-strong bg-white', Boolean(maxHeight) && 'overflow-auto', className)}
      style={{ width: width + 2, maxHeight }}
    >
      <div className="relative" style={{ width, height }}>
        <canvas ref={canvasRef} role="img" aria-label={`Page ${page} of ${title}`} style={{ width, height }} className="block" />
        {current?.status === 'ready'
          ? marks.flatMap((mark) =>
              mark.boxes.map((box, index) => {
                const pad = mark.active ? 3 : 2;
                const style = {
                  left: box[0] * scale - pad,
                  top: box[1] * scale - pad,
                  width: (box[2] - box[0]) * scale + pad * 2,
                  height: (box[3] - box[1]) * scale + pad * 2,
                };
                const look = cx(
                  'absolute rounded-xs mix-blend-multiply',
                  mark.active ? 'bg-cobalt-bg ring-2 ring-cobalt' : 'ring-1 ring-cobalt-border hover:bg-cobalt-bg hover:ring-cobalt',
                );
                return mark.onSelect ? (
                  <button
                    key={`${mark.id}-${index}`}
                    type="button"
                    data-mark={mark.id}
                    data-active={mark.active ? '' : undefined}
                    aria-label={mark.label ?? 'Citation'}
                    aria-pressed={mark.active}
                    onClick={mark.onSelect}
                    style={style}
                    className={look}
                  />
                ) : (
                  <span key={`${mark.id}-${index}`} data-mark={mark.id} data-active={mark.active ? '' : undefined} aria-hidden style={style} className={look} />
                );
              }),
            )
          : null}
        {current?.status === 'error' ? (
          <div className="absolute inset-x-0 top-10 px-6 text-center">
            <p role="alert" className="text-body text-ink-700">
              This page could not be drawn. The quoted text beside it is still what the fact records.
            </p>
            <button type="button" className="link mt-2 text-body" onClick={() => setAttempt((n) => n + 1)}>
              Try again
            </button>
          </div>
        ) : null}
        {!current ? (
          <p role="status" className="absolute inset-x-0 top-10 text-center text-caption text-ink-500">
            Drawing page {page}
          </p>
        ) : null}
      </div>
    </div>
  );
}
