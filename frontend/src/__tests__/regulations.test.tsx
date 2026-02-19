import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import React from 'react';

// ─── Global mocks ──────────────────────────────────────────────────────────────

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ id: 'uu-40-2007' }),
  usePathname: () => '/regulations',
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
    header: ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => <header {...props}>{children}</header>,
    h1: ({ children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => <p {...props}>{children}</p>,
    span: ({ children, ...props }: React.HTMLAttributes<HTMLSpanElement>) => <span {...props}>{children}</span>,
    button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useMotionValue: () => ({ set: vi.fn(), get: () => 0 }),
  useAnimationFrame: () => {},
  useTransform: () => '0% center',
}));

vi.mock('next/image', () => ({
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}));

vi.mock('@/components/reactbits/ShinyText', () => ({
  default: ({ text, className }: { text: string; className?: string }) => (
    <span className={className}>{text}</span>
  ),
}));

// Mock fetchRegulations so it stays in "pending" state (loading) by default
vi.mock('@/lib/api', () => ({
  fetchRegulations: vi.fn(),
  fetchRegulationDetail: vi.fn(),
}));

// ─── Test data factories ────────────────────────────────────────────────────────

import type { RegulationListItem, ChapterDetail, ArticleDetail } from '@/lib/api';

const makeArticle = (overrides: Partial<ArticleDetail> = {}): ArticleDetail => ({
  id: 'art-1',
  number: '1',
  full_text: 'Dalam undang-undang ini yang dimaksud dengan...',
  content_summary: null,
  parent_chapter_id: 'ch-1',
  cross_references: [],
  ...overrides,
});

const makeChapter = (overrides: Partial<ChapterDetail> = {}): ChapterDetail => ({
  id: 'ch-1',
  number: '1',
  title: 'Ketentuan Umum',
  articles: [makeArticle()],
  ...overrides,
});

const makeRegulation = (overrides: Partial<RegulationListItem> = {}): RegulationListItem => ({
  id: 'uu-40-2007',
  node_type: 'law',
  number: 40,
  year: 2007,
  title: 'Undang-Undang Nomor 40 Tahun 2007 tentang Perseroan Terbatas',
  about: 'Perseroan Terbatas',
  status: 'active',
  chapter_count: 15,
  article_count: 161,
  indexed_chunk_count: 200,
  amendment_count: 0,
  cross_reference_count: 45,
  ...overrides,
});

// ─── Imports (must come AFTER mocks are set up) ────────────────────────────────

import RegulationCard from '@/components/regulations/RegulationCard';
import RegulationFilters from '@/components/regulations/RegulationFilters';
import TableOfContents from '@/components/regulations/TableOfContents';
import Navbar from '@/components/Navbar';

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('RegulationCard', () => {
  it('renders RegulationCard with correct title', () => {
    const regulation = makeRegulation();
    render(<RegulationCard regulation={regulation} />);
    expect(screen.getByText(/Undang-Undang Nomor 40 Tahun 2007/)).toBeInTheDocument();
  });

  it('shows UU type badge for node_type="law"', () => {
    const regulation = makeRegulation({ node_type: 'law' });
    render(<RegulationCard regulation={regulation} />);
    expect(screen.getByText('UU')).toBeInTheDocument();
  });

  it('shows PP type badge for node_type="government_regulation"', () => {
    const regulation = makeRegulation({ node_type: 'government_regulation', title: 'PP Test' });
    render(<RegulationCard regulation={regulation} />);
    expect(screen.getByText('PP')).toBeInTheDocument();
  });

  it('shows amendment count badge when amendment_count > 0', () => {
    const regulation = makeRegulation({ amendment_count: 3 });
    render(<RegulationCard regulation={regulation} />);
    expect(screen.getByText(/3 amandemen/)).toBeInTheDocument();
  });

  it('does NOT show amendment badge when amendment_count is 0', () => {
    const regulation = makeRegulation({ amendment_count: 0 });
    render(<RegulationCard regulation={regulation} />);
    expect(screen.queryByText(/amandemen/)).not.toBeInTheDocument();
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = vi.fn();
    const regulation = makeRegulation();
    render(<RegulationCard regulation={regulation} onClick={handleClick} />);
    fireEvent.click(screen.getByText(/Undang-Undang Nomor 40 Tahun 2007/).closest('div')!);
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('shows active status badge', () => {
    const regulation = makeRegulation({ status: 'active' });
    render(<RegulationCard regulation={regulation} />);
    expect(screen.getByText('Aktif')).toBeInTheDocument();
  });
});

describe('RegulationFilters', () => {
  const defaultProps = {
    search: '',
    nodeType: '',
    status: '',
    year: '',
    onSearchChange: vi.fn(),
    onNodeTypeChange: vi.fn(),
    onStatusChange: vi.fn(),
    onYearChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls onSearchChange when search input changes', () => {
    const onSearchChange = vi.fn();
    render(<RegulationFilters {...defaultProps} onSearchChange={onSearchChange} />);
    const input = screen.getByPlaceholderText('Cari regulasi…');
    fireEvent.change(input, { target: { value: 'perseroan' } });
    expect(onSearchChange).toHaveBeenCalledWith('perseroan');
  });

  it('calls onNodeTypeChange when jenis select changes', () => {
    const onNodeTypeChange = vi.fn();
    render(<RegulationFilters {...defaultProps} onNodeTypeChange={onNodeTypeChange} />);
    const select = screen.getByLabelText('Filter jenis regulasi');
    fireEvent.change(select, { target: { value: 'law' } });
    expect(onNodeTypeChange).toHaveBeenCalledWith('law');
  });

  it('calls onStatusChange when status select changes', () => {
    const onStatusChange = vi.fn();
    render(<RegulationFilters {...defaultProps} onStatusChange={onStatusChange} />);
    const select = screen.getByLabelText('Filter status regulasi');
    fireEvent.change(select, { target: { value: 'active' } });
    expect(onStatusChange).toHaveBeenCalledWith('active');
  });

  it('calls onYearChange when year select changes', () => {
    const onYearChange = vi.fn();
    render(<RegulationFilters {...defaultProps} onYearChange={onYearChange} />);
    const select = screen.getByLabelText('Filter tahun regulasi');
    fireEvent.change(select, { target: { value: '2020' } });
    expect(onYearChange).toHaveBeenCalledWith('2020');
  });
});

describe('TableOfContents', () => {
  const chapters: ChapterDetail[] = [
    makeChapter({ id: 'ch-1', number: '1', title: 'Ketentuan Umum', articles: [makeArticle({ id: 'art-1', number: '1' })] }),
    makeChapter({ id: 'ch-2', number: '2', title: 'Pendirian', articles: [makeArticle({ id: 'art-2', number: '2' })] }),
  ];

  it('renders chapter titles in TableOfContents', () => {
    render(
      <TableOfContents
        chapters={chapters}
        onChapterClick={vi.fn()}
        onArticleClick={vi.fn()}
      />
    );
    expect(screen.getByText(/Ketentuan Umum/)).toBeInTheDocument();
    expect(screen.getByText(/Pendirian/)).toBeInTheDocument();
  });

  it('renders article items when chapter is expanded', async () => {
    render(
      <TableOfContents
        chapters={[makeChapter({ id: 'ch-1', number: '1', title: 'Ketentuan Umum', articles: [makeArticle({ id: 'art-1', number: '1' })] })]}
        activeChapterId="ch-1"
        onChapterClick={vi.fn()}
        onArticleClick={vi.fn()}
      />
    );
    // The active chapter starts expanded — click to expand if not already
    const chapterBtn = screen.getByRole('button', { name: /Bab 1/i });
    // If not already showing article, click to toggle open
    if (!screen.queryByText('Pasal 1')) {
      fireEvent.click(chapterBtn);
    }
    await waitFor(() => {
      expect(screen.getByText('Pasal 1')).toBeInTheDocument();
    });
  });

  it('calls onChapterClick when a chapter button is clicked', () => {
    const onChapterClick = vi.fn();
    render(
      <TableOfContents
        chapters={chapters}
        onChapterClick={onChapterClick}
        onArticleClick={vi.fn()}
      />
    );
    fireEvent.click(screen.getAllByRole('button')[0]);
    expect(onChapterClick).toHaveBeenCalled();
  });
});

describe('Library page loading state', () => {
  it('shows loading skeleton when fetchRegulations is pending', async () => {
    // Import inside test to get fresh module with mock
    const { fetchRegulations } = await import('@/lib/api');
    const mockedFetch = fetchRegulations as ReturnType<typeof vi.fn>;

    // Make it return a never-resolving promise (always loading)
    mockedFetch.mockReturnValue(new Promise(() => {}));

    const { default: RegulationsPage } = await import('@/app/regulations/page');
    render(<RegulationsPage />);

    // Loading skeletons have role="status" with aria-label
    await waitFor(() => {
      const loader = screen.getByRole('status');
      expect(loader).toBeInTheDocument();
    });
  });
});

describe('Navigation', () => {
  it('Navbar contains Regulasi link', () => {
    render(<Navbar />);
    const banners = screen.getAllByRole('banner');
    const found = banners.some((b) => {
      try {
        return within(b).getAllByText('Regulasi').length > 0;
      } catch {
        return false;
      }
    });
    expect(found).toBe(true);
  });
});
