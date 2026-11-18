import { describe, expect, it } from 'vitest';
import { defaultCopilotScope } from './context';

describe('the scope the Copilot opens on', () => {
  it('is the exception open in the drawer, even on a borrower’s page', () => {
    expect(defaultCopilotScope({ open: true, itemId: 'w-1', borrowerCode: null }, '/borrowers/kestrel-bay-packaging')).toEqual({ kind: 'item', itemId: 'w-1' });
    expect(defaultCopilotScope({ open: true, itemId: 'w-1', borrowerCode: null }, '/command-centre')).toEqual({ kind: 'item', itemId: 'w-1' });
  });

  it('is the borrower on screen when no exception is open', () => {
    expect(defaultCopilotScope({ open: false, itemId: 'w-1', borrowerCode: null }, '/borrowers/kestrel-bay-packaging/covenants')).toEqual({
      kind: 'borrower',
      code: 'kestrel-bay-packaging',
    });
    expect(defaultCopilotScope({ open: true, itemId: null, borrowerCode: 'ashgrove-fleet' }, '/portfolio')).toEqual({ kind: 'borrower', code: 'ashgrove-fleet' });
  });

  it('is the portfolio otherwise', () => {
    expect(defaultCopilotScope({ open: false, itemId: null, borrowerCode: null }, '/command-centre')).toEqual({ kind: 'portfolio' });
  });
});
