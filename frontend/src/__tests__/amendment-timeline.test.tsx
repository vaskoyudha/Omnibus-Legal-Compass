import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// ─── Global mocks ──────────────────────────────────────────────────────────────

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ id: 'uu_11_2020' }),
  usePathname: () => '/regulations/uu_11_2020',
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
    ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) => <ul {...props}>{children}</ul>,
    li: ({ children, ...props }: React.HTMLAttributes<HTMLLIElement>) => <li {...props}>{children}</li>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ─── Imports ───────────────────────────────────────────────────────────────────

import AmendmentTimeline from '@/components/regulations/AmendmentTimeline';
import type { AmendmentTimelineResponse } from '@/lib/api';

// ─── Test data factories ────────────────────────────────────────────────────────

const makeEntry = (overrides: Partial<{
  regulation_id: string;
  regulation_title: string;
  year: number;
  number: number;
  edge_type: string;
  direction: string;
  target_id: string;
  target_title: string;
}> = {}) => ({
  regulation_id: 'uu_5_2019',
  regulation_title: 'UU No. 5 Tahun 2019',
  year: 2019,
  number: 5,
  edge_type: 'AMENDS',
  direction: 'outgoing',
  target_id: 'uu_11_2020',
  target_title: 'UU No. 11 Tahun 2020',
  ...overrides,
});

const makeTimeline = (entries: ReturnType<typeof makeEntry>[]): AmendmentTimelineResponse => ({
  regulation_id: 'uu_11_2020',
  regulation_title: 'UU No. 11 Tahun 2020 Cipta Kerja',
  entries,
});

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('AmendmentTimeline', () => {
  it('renders timeline entries with correct titles', () => {
    const entries = [
      makeEntry({ regulation_id: 'uu_5_2019', regulation_title: 'UU No. 5 Tahun 2019', year: 2019 }),
      makeEntry({ regulation_id: 'uu_3_2021', regulation_title: 'PP No. 3 Tahun 2021', year: 2021, edge_type: 'REVOKED_BY' }),
    ];
    const timeline = makeTimeline(entries);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="uu_11_2020" />);

    expect(screen.getByText('UU No. 5 Tahun 2019')).toBeInTheDocument();
    expect(screen.getByText('PP No. 3 Tahun 2021')).toBeInTheDocument();
  });

  it('shows empty state message when no entries', () => {
    const timeline = makeTimeline([]);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="uu_11_2020" />);

    expect(screen.getByText('Tidak ada riwayat amandemen untuk regulasi ini')).toBeInTheDocument();
  });

  it('highlights current regulation with accent color class', () => {
    const entries = [
      makeEntry({ regulation_id: 'uu_11_2020', regulation_title: 'UU No. 11 Tahun 2020 Cipta Kerja', year: 2020 }),
    ];
    const timeline = makeTimeline(entries);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="uu_11_2020" />);

    const link = screen.getByRole('link', { name: 'UU No. 11 Tahun 2020 Cipta Kerja' });
    // The link should point to the current regulation's URL
    expect(link).toHaveAttribute('href', '/regulations/uu_11_2020');
    // The parent container (content card) should have the accent border style — check the surrounding div
    const contentCard = link.closest('div');
    expect(contentCard?.className).toContain('border-[#AAFF00]/30');
  });

  it('shows correct label for AMENDS edge type', () => {
    const entries = [
      makeEntry({ edge_type: 'AMENDS' }),
    ];
    const timeline = makeTimeline(entries);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="other_reg" />);

    expect(screen.getByText('Mengamandemen')).toBeInTheDocument();
  });

  it('sorts entries by year ascending', () => {
    const entries = [
      makeEntry({ regulation_id: 'reg_2022', regulation_title: 'Reg 2022', year: 2022 }),
      makeEntry({ regulation_id: 'reg_2019', regulation_title: 'Reg 2019', year: 2019 }),
      makeEntry({ regulation_id: 'reg_2021', regulation_title: 'Reg 2021', year: 2021 }),
    ];
    const timeline = makeTimeline(entries);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="other_reg" />);

    const links = screen.getAllByRole('link');
    const titles = links.map((l) => l.textContent);

    const idx2019 = titles.findIndex((t) => t?.includes('2019'));
    const idx2021 = titles.findIndex((t) => t?.includes('2021'));
    const idx2022 = titles.findIndex((t) => t?.includes('2022'));

    expect(idx2019).toBeLessThan(idx2021);
    expect(idx2021).toBeLessThan(idx2022);
  });

  it('renders correct edge type labels for all supported types', () => {
    const edgeCases: Array<{ edge_type: string; label: string }> = [
      { edge_type: 'AMENDED_BY', label: 'Diamandemen oleh' },
      { edge_type: 'REVOKES', label: 'Mencabut' },
      { edge_type: 'REVOKED_BY', label: 'Dicabut oleh' },
      { edge_type: 'REPLACES', label: 'Menggantikan' },
      { edge_type: 'REPLACED_BY', label: 'Digantikan oleh' },
      { edge_type: 'IMPLEMENTS', label: 'Melaksanakan' },
      { edge_type: 'IMPLEMENTED_BY', label: 'Dilaksanakan oleh' },
    ];

    for (const { edge_type, label } of edgeCases) {
      const { unmount } = render(
        <AmendmentTimeline
          timeline={makeTimeline([makeEntry({ regulation_id: `reg_${edge_type}`, edge_type })])}
          currentRegulationId="other_reg"
        />
      );
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('renders links pointing to correct regulation URLs', () => {
    const entries = [
      makeEntry({ regulation_id: 'uu_5_2019', regulation_title: 'UU No. 5 Tahun 2019' }),
    ];
    const timeline = makeTimeline(entries);

    render(<AmendmentTimeline timeline={timeline} currentRegulationId="other_reg" />);

    const link = screen.getByRole('link', { name: 'UU No. 5 Tahun 2019' });
    expect(link).toHaveAttribute('href', '/regulations/uu_5_2019');
  });
});
