import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

const getDocument = vi.fn();
// the build for older browsers: the modern one calls Map.getOrInsertComputed and Promise.try, which a cloud
// browser a few versions back does not have, so every page failed to draw there
vi.mock('pdfjs-dist/legacy/build/pdf.mjs', () => ({ GlobalWorkerOptions: {}, getDocument: (...args: unknown[]) => getDocument(...args) }));
vi.mock('pdfjs-dist/legacy/build/pdf.worker.min.mjs?url', () => ({ default: '/worker.mjs' }));

import { PdfPage } from './PdfPage';

afterEach(() => getDocument.mockReset());

describe('a page that cannot be drawn', () => {
  it('says so, keeps the quoted text as the record, and tries again from the file when asked', async () => {
    getDocument.mockReturnValueOnce({ promise: Promise.reject(new Error('503')) });
    getDocument.mockReturnValue({ promise: new Promise(() => {}) }); // the second attempt is still loading
    render(<PdfPage documentId="d1" page={2} width={480} title="Compliance certificate" />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('This page could not be drawn. The quoted text beside it is still what the fact records.');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(await screen.findByRole('status')).toHaveTextContent('Drawing page 2');
    expect(getDocument).toHaveBeenCalledTimes(2); // the failed file is fetched again, not served from the failure
  });
});
