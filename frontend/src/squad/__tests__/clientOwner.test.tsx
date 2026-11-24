import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ClientOwner } from '../shell/ClientOwner';

describe('whose client it is', () => {
  it('names the analyst, and says nothing more to someone who may act', () => {
    render(<ClientOwner analyst="Priya Raman" lookOnly={null} />);
    expect(screen.getByText('Analyst: Priya Raman')).toBeInTheDocument();
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });

  it('tells another analyst she can look but not act, in the server’s words', () => {
    const why = "Tavernel Grid is Tomas Keller's client; only that analyst, or a credit officer, portfolio manager or credit administration, can act on it.";
    render(<ClientOwner analyst="Tomas Keller" lookOnly={why} />);
    expect(screen.getByText('Analyst: Tomas Keller')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent(`You can look at this client, not act on it. ${why}`);
  });

  it('says when no analyst is named, and shows nothing at all when an older server sends neither', () => {
    const { container, rerender } = render(<ClientOwner analyst={null} lookOnly="Zephyr Zinc Works has no analyst yet; an analyst can act on its cases once one is named." />);
    expect(screen.getByText('No analyst is named')).toBeInTheDocument();
    rerender(<ClientOwner analyst={undefined} lookOnly={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
