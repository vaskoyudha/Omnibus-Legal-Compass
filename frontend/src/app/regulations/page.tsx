'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { fetchRegulations, RegulationListItem, RegulationListResponse } from '@/lib/api';
import RegulationCard from '@/components/regulations/RegulationCard';
import RegulationFilters from '@/components/regulations/RegulationFilters';

const PAGE_SIZE = 12;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3 p-5 bg-white/[0.03] border border-white/[0.06] rounded-2xl animate-pulse">
      <div className="flex gap-2">
        <div className="h-5 w-10 rounded-full bg-white/[0.06]" />
        <div className="h-5 w-16 rounded-full bg-white/[0.06]" />
      </div>
      <div className="h-4 w-3/4 rounded bg-white/[0.06]" />
      <div className="h-3 w-full rounded bg-white/[0.04]" />
      <div className="h-3 w-5/6 rounded bg-white/[0.04]" />
      <div className="h-3 w-2/3 rounded bg-white/[0.04]" />
      <div className="flex gap-2 pt-2 mt-auto border-t border-white/[0.04]">
        <div className="h-3 w-16 rounded bg-white/[0.04]" />
        <div className="h-3 w-12 rounded bg-white/[0.04]" />
        <div className="h-3 w-16 rounded bg-white/[0.04]" />
      </div>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  onPageChange,
}: Readonly<{ page: number; totalPages: number; onPageChange: (p: number) => void }>) {
  if (totalPages <= 1) return null;

  const getPages = (): (number | '…')[] => {
    if (totalPages <= 5) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | '…')[] = [1];
    if (page > 3) pages.push('…');
    for (let p = Math.max(2, page - 1); p <= Math.min(totalPages - 1, page + 1); p++) {
      pages.push(p);
    }
    if (page < totalPages - 2) pages.push('…');
    pages.push(totalPages);
    return pages;
  };

  return (
    <div className="flex items-center justify-center gap-1.5 mt-10" role="navigation" aria-label="Halaman">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="px-3 py-2 rounded-lg text-sm text-white/50 hover:text-white/80 hover:bg-white/[0.05] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Halaman sebelumnya"
      >
        ←
      </button>
      {getPages().map((p, idx) =>
        p === '…' ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-white/25 text-sm select-none">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p as number)}
            className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${page === p
                ? 'bg-[#AAFF00]/15 text-[#AAFF00] border border-[#AAFF00]/30'
                : 'text-white/50 hover:text-white/80 hover:bg-white/[0.05]'
              }`}
            aria-current={page === p ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className="px-3 py-2 rounded-lg text-sm text-white/50 hover:text-white/80 hover:bg-white/[0.05] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Halaman berikutnya"
      >
        →
      </button>
    </div>
  );
}

export default function RegulationsPage() {
  const router = useRouter();

  const [search, setSearch] = useState('');
  const [nodeType, setNodeType] = useState('');
  const [status, setStatus] = useState('');
  const [year, setYear] = useState('');
  const [page, setPage] = useState(1);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [data, setData] = useState<RegulationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadData = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchRegulations({
        search: debouncedSearch || undefined,
        node_type: nodeType || undefined,
        status: status || undefined,
        year: year ? Number(year) : undefined,
        page: p,
        page_size: PAGE_SIZE,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, nodeType, status, year]);

  // Reset page to 1 on filter change (except pagination)
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, nodeType, status, year]);

  useEffect(() => {
    loadData(page);
  }, [loadData, page]);

  const handleCardClick = (regulation: RegulationListItem) => {
    router.push(`/regulations/${encodeURIComponent(regulation.id)}`);
  };

  return (
    <div className="min-h-screen">
      {/* Breadcrumb */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <nav className="flex items-center gap-2 text-xs text-white/30">
          <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
          <span>/</span>
          <span className="text-white/60">Perpustakaan Regulasi</span>
        </nav>
      </div>

      {/* Hero */}
      <motion.div
        className="relative py-12 px-4 overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-[-1]"
          style={{
            width: '60%',
            height: '200px',
            background: 'radial-gradient(ellipse at center, rgba(170,255,0,0.15) 0%, transparent 70%)',
            filter: 'blur(40px)',
          }}
        />
        <div className="relative max-w-7xl mx-auto z-10 text-center">
          <motion.div
            className="mb-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <span className="ai-badge inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-[#AAFF00]/30 text-sm font-medium text-[#AAFF00] shadow-[0_0_15px_rgba(170,255,0,0.2)]">
              <span>📚</span> Regulation Library
            </span>
          </motion.div>
          <motion.h1
            className="text-4xl sm:text-5xl font-extrabold mb-3 tracking-tight text-transparent bg-clip-text bg-gradient-to-b from-white to-white/70"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            Perpustakaan Regulasi
          </motion.h1>
          <motion.p
            className="text-white/60 text-base max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            {data ? (
              <>
                <span className="text-[#AAFF00] font-semibold text-lg">{data.total}</span> regulasi ditemukan
              </>
            ) : (
              'Memuat koleksi peraturan perundang-undangan Indonesia...'
            )}
          </motion.p>
        </div>
      </motion.div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <RegulationFilters
            search={search}
            nodeType={nodeType}
            status={status}
            year={year}
            onSearchChange={setSearch}
            onNodeTypeChange={(v) => { setNodeType(v); setPage(1); }}
            onStatusChange={(v) => { setStatus(v); setPage(1); }}
            onYearChange={(v) => { setYear(v); setPage(1); }}
          />
        </motion.div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 pb-16">
        {/* Loading state */}
        {loading && (
          <div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            aria-label="Memuat regulasi"
            role="status"
          >
            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <motion.div
            className="flex flex-col items-center gap-4 py-16 text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-white/60 text-sm">Gagal memuat data. Coba lagi.</p>
            <button
              onClick={() => loadData(page)}
              className="px-5 py-2.5 rounded-xl bg-[#AAFF00]/10 text-[#AAFF00] text-sm font-medium border border-[#AAFF00]/20 hover:bg-[#AAFF00]/20 transition-colors"
            >
              Coba Lagi
            </button>
          </motion.div>
        )}

        {/* Empty state */}
        {!loading && !error && data && data.items.length === 0 && (
          <motion.div
            className="flex flex-col items-center gap-4 py-16 text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] flex items-center justify-center text-3xl">
              📭
            </div>
            <p className="text-white/50 text-sm">Tidak ada regulasi ditemukan</p>
            <p className="text-white/30 text-xs">Coba ubah filter pencarian</p>
          </motion.div>
        )}

        {/* Results grid */}
        {!loading && !error && data && data.items.length > 0 && (
          <AnimatePresence mode="wait">
            <motion.div
              key={`page-${page}-${nodeType}-${status}-${year}-${debouncedSearch}`}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {data.items.map((regulation) => (
                <motion.div key={regulation.id} variants={itemVariants}>
                  <RegulationCard
                    regulation={regulation}
                    onClick={() => handleCardClick(regulation)}
                  />
                </motion.div>
              ))}
            </motion.div>
          </AnimatePresence>
        )}

        {/* Pagination */}
        {!loading && !error && data && (
          <Pagination
            page={page}
            totalPages={data.total_pages}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  );
}
