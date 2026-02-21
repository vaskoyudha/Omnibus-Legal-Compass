'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { fetchRegulations, RegulationListItem, RegulationListResponse } from '@/lib/api';
import RegulationCard from '@/components/regulations/RegulationCard';
import RegulationFilters from '@/components/regulations/RegulationFilters';

const PAGE_SIZE = 12;

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3.5 p-6 bg-white/[0.02] border border-white/[0.06] rounded-2xl animate-pulse">
      <div className="flex gap-2">
        <div className="h-6 w-12 rounded-lg bg-white/[0.06]" />
        <div className="h-6 w-16 rounded-lg bg-white/[0.06]" />
        <div className="ml-auto h-6 w-24 rounded-lg bg-white/[0.04]" />
      </div>
      <div className="h-5 w-3/4 rounded bg-white/[0.06]" />
      <div className="space-y-2 mt-1">
        <div className="h-3 w-full rounded bg-white/[0.04]" />
        <div className="h-3 w-5/6 rounded bg-white/[0.04]" />
      </div>
      <div className="flex gap-3 pt-3 mt-auto border-t border-white/[0.04]">
        <div className="h-4 w-16 rounded bg-white/[0.04]" />
        <div className="h-4 w-12 rounded bg-white/[0.04]" />
        <div className="h-4 w-16 rounded bg-white/[0.04]" />
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
    <div className="flex items-center justify-center gap-1.5 mt-12" role="navigation" aria-label="Halaman">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="px-4 py-2.5 rounded-xl text-sm font-medium text-white/50 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="Halaman sebelumnya"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
      </button>
      {getPages().map((p, idx) =>
        p === '…' ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-white/20 text-sm select-none">…</span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p as number)}
            className={`w-10 h-10 rounded-xl text-sm font-bold transition-all duration-200 ${page === p
              ? 'bg-[#AAFF00] text-[#0A0A0F] shadow-[0_0_20px_rgba(170,255,0,0.3)]'
              : 'text-white/50 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/[0.08]'
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
        className="px-4 py-2.5 rounded-xl text-sm font-medium text-white/50 hover:text-white hover:bg-white/[0.06] border border-transparent hover:border-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        aria-label="Halaman berikutnya"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
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

  useEffect(() => { setPage(1); }, [debouncedSearch, nodeType, status, year]);
  useEffect(() => { loadData(page); }, [loadData, page]);

  const handleCardClick = (regulation: RegulationListItem) => {
    router.push(`/regulations/${encodeURIComponent(regulation.id)}`);
  };

  return (
    <div className="min-h-screen bg-[#0A0A0F] relative overflow-hidden -mt-16 sm:-mt-20">
      {/* Film Grain */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
          backgroundSize: '200px 200px',
        }}
      />

      {/* Ambient Background Glow */}
      <div className="fixed inset-0 pointer-events-none z-[-1]">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[600px] bg-gradient-to-b from-[#AAFF00]/[0.04] to-transparent rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-0 w-[500px] h-[500px] bg-[radial-gradient(ellipse_at_right,rgba(170,255,0,0.02),transparent_70%)] blur-2xl" />
      </div>

      {/* ═══ HERO SECTION ═══ */}
      <div className="relative pt-20 sm:pt-24 pb-6 px-4 overflow-hidden">
        {/* Hero gradient aura */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[300px] bg-[radial-gradient(ellipse_at_center,rgba(170,255,0,0.08)_0%,transparent_70%)] blur-[60px]" />
        </div>

        <div className="relative max-w-7xl mx-auto z-10">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8">
            {/* Left: Title block */}
            <div className="max-w-2xl">
              <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-5">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#0A0A0F]/80 backdrop-blur-xl border border-[#AAFF00]/30 text-xs font-bold text-[#AAFF00] uppercase tracking-widest shadow-[0_0_20px_rgba(170,255,0,0.15)]">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                  Regulation Library
                </div>
              </motion.div>
              <motion.h1
                className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tighter text-white mb-4 leading-[1.1]"
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
              >
                Perpustakaan{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-br from-[#AAFF00] via-white to-white/40">
                  Regulasi.
                </span>
              </motion.h1>
              <motion.p
                className="text-white/50 text-base lg:text-lg font-light leading-relaxed max-w-lg"
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              >
                Koleksi lengkap peraturan perundang-undangan Indonesia yang terindeks dan siap digunakan.
              </motion.p>
            </div>

            {/* Right: Stats counters */}
            <motion.div
              className="flex items-center gap-6 lg:gap-8"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
            >
              {data && (
                <>
                  <div className="text-center lg:text-right">
                    <p className="text-[#AAFF00] font-mono text-3xl lg:text-4xl font-black tracking-tight drop-shadow-[0_0_10px_rgba(170,255,0,0.4)]">
                      {data.total.toLocaleString()}
                    </p>
                    <p className="text-[10px] text-white/35 uppercase tracking-widest font-bold mt-1">Total Regulasi</p>
                  </div>
                  <div className="w-px h-12 bg-white/[0.06]" />
                  <div className="text-center lg:text-right">
                    <p className="text-white font-mono text-3xl lg:text-4xl font-black tracking-tight">{data.total_pages}</p>
                    <p className="text-[10px] text-white/35 uppercase tracking-widest font-bold mt-1">Halaman</p>
                  </div>
                </>
              )}
            </motion.div>
          </div>
        </div>
      </div>

      {/* ═══ STICKY FILTERS BAR ═══ */}
      <div className="sticky top-0 z-40 backdrop-blur-2xl bg-[#050508]/80 border-b border-white/[0.05]">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <RegulationFilters
              search={search} nodeType={nodeType} status={status} year={year}
              onSearchChange={setSearch}
              onNodeTypeChange={(v) => { setNodeType(v); setPage(1); }}
              onStatusChange={(v) => { setStatus(v); setPage(1); }}
              onYearChange={(v) => { setYear(v); setPage(1); }}
            />
          </motion.div>
        </div>
      </div>

      {/* ═══ CONTENT AREA ═══ */}
      <div className="max-w-7xl mx-auto px-4 pt-8 pb-20 relative z-10">
        {/* Loading */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" aria-label="Memuat regulasi" role="status">
            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <motion.div className="flex flex-col items-center gap-5 py-20 text-center" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
            <div className="w-20 h-20 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
              <svg className="w-10 h-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <div>
              <p className="text-white/70 font-semibold mb-1">Gagal Memuat Data</p>
              <p className="text-white/40 text-sm">{error}</p>
            </div>
            <button
              onClick={() => loadData(page)}
              className="px-6 py-3 rounded-xl bg-[#AAFF00] text-[#0A0A0F] text-sm font-bold hover:shadow-[0_0_20px_rgba(170,255,0,0.3)] transition-all"
            >
              Coba Lagi
            </button>
          </motion.div>
        )}

        {/* Empty */}
        {!loading && !error && data && data.items.length === 0 && (
          <motion.div className="flex flex-col items-center gap-5 py-20 text-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="w-20 h-20 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
              <svg className="w-10 h-10 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </div>
            <div>
              <p className="text-white/60 font-semibold mb-1">Tidak Ada Hasil</p>
              <p className="text-white/30 text-sm">Coba ubah filter atau kata kunci pencarian</p>
            </div>
          </motion.div>
        )}

        {/* Results */}
        {!loading && !error && data && data.items.length > 0 && (
          <AnimatePresence mode="wait">
            <motion.div
              key={`page-${page}-${nodeType}-${status}-${year}-${debouncedSearch}`}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {data.items.map((regulation) => (
                <motion.div key={regulation.id} variants={itemVariants}>
                  <RegulationCard regulation={regulation} onClick={() => handleCardClick(regulation)} />
                </motion.div>
              ))}
            </motion.div>
          </AnimatePresence>
        )}

        {/* Pagination */}
        {!loading && !error && data && (
          <Pagination page={page} totalPages={data.total_pages} onPageChange={setPage} />
        )}
      </div>
    </div>
  );
}
