import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import CitationList from '@/components/CitationList';
import type { CitationInfo } from '@/lib/api';

const makeCitation = (overrides: Partial<CitationInfo> = {}): CitationInfo => ({
  number: 1,
  citation_id: 'cite-1',
  citation: 'UU No. 40 Tahun 2007 tentang Perseroan Terbatas',
  score: 0.85,
  metadata: {
    jenis_dokumen: 'UU',
    nomor: '40',
    tahun: '2007',
    pasal: '1',
    ayat: '1',
    text: 'Perseroan Terbatas adalah badan hukum yang merupakan persekutuan modal.',
  },
  ...overrides,
});

describe('CitationList', () => {
  it('renders nothing when citations array is empty', () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing when citations is undefined-like (empty)', () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders citation cards when citations are provided', () => {
    const citations = [makeCitation(), makeCitation({ citation_id: 'cite-2', number: 2 })];
    render(<CitationList citations={citations} />);

    // Header should show "Sumber Referensi"
    expect(screen.getByText('Sumber Referensi')).toBeInTheDocument();
    // Citation titles rendered
    expect(screen.getAllByText('UU No. 40 Tahun 2007 tentang Perseroan Terbatas')).toHaveLength(2);
  });

  it('expands a citation to show content snippet when clicked', () => {
    render(<CitationList citations={[makeCitation()]} />);

    // Content snippet should NOT be visible initially
    expect(screen.queryByText(/Perseroan Terbatas adalah badan hukum/)).not.toBeInTheDocument();

    // Click the citation header button (the first button inside the citation card)
    const buttons = screen.getAllByRole('button');
    // buttons[0] = "Buka Semua", buttons[1] = "Tutup Semua", buttons[2] = citation expand
    const expandButton = buttons[2];
    fireEvent.click(expandButton);

    // Now the snippet should be visible
    expect(screen.getByText(/Perseroan Terbatas adalah badan hukum/)).toBeInTheDocument();
  });

  it('shows "Buka Semua" and "Tutup Semua" controls', () => {
    render(<CitationList citations={[makeCitation()]} />);
    expect(screen.getByText('Buka Semua')).toBeInTheDocument();
    expect(screen.getByText('Tutup Semua')).toBeInTheDocument();
  });
});
