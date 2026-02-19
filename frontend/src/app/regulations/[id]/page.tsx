'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { fetchRegulationDetail, fetchAmendmentTimeline, RegulationDetailResponse, AmendmentTimelineResponse } from '@/lib/api';
import TableOfContents from '@/components/regulations/TableOfContents';
import ArticleRenderer from '@/components/regulations/ArticleRenderer';
import MetadataPanel from '@/components/regulations/MetadataPanel';
import AmendmentTimeline from '@/components/regulations/AmendmentTimeline';

const NODE_TYPE_LABEL: Record<string, string> = {
  law: 'UU',
  government_regulation: 'PP',
  presidential_regulation: 'Perpres',
  ministerial_regulation: 'Permen',
};

const STATUS_CLASS: Record<string, string> = {
  active: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25',
  amended: 'bg-amber-500/15 text-amber-400 border border-amber-500/25',
  repealed: 'bg-red-500/15 text-red-400 border border-red-500/25',
};

function LoadingSkeleton() {
  return (
    <div className="min-h-screen" aria-label="Memuat regulasi" role="status">
      <div className="max-w-7xl mx-auto px-4 pt-10 pb-8 animate-pulse">
        <div className="h-4 w-48 rounded bg-white/[0.06] mb-6" />
        <div className="flex gap-2 mb-4">
          <div className="h-6 w-10 rounded-full bg-white/[0.06]" />
          <div className="h-6 w-16 rounded-full bg-white/[0.06]" />
        </div>
        <div className="h-8 w-2/3 rounded bg-white/[0.06] mb-3" />
        <div className="h-4 w-1/2 rounded bg-white/[0.04]" />
      </div>
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex gap-8">
          <div className="hidden lg:block w-56 flex-shrink-0">
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-5 rounded bg-white/[0.04] animate-pulse" />
              ))}
            </div>
          </div>
          <div className="flex-1 space-y-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-3 animate-pulse">
                <div className="h-6 w-48 rounded bg-white/[0.06]" />
                <div className="h-3 w-full rounded bg-white/[0.04]" />
                <div className="h-3 w-5/6 rounded bg-white/[0.04]" />
                <div className="h-3 w-4/5 rounded bg-white/[0.04]" />
              </div>
            ))}
          </div>
          <div className="hidden xl:block w-64 flex-shrink-0">
            <div className="space-y-3 animate-pulse">
              <div className="h-24 rounded-2xl bg-white/[0.04]" />
              <div className="h-10 rounded-xl bg-white/[0.04]" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RegulationDetailPage() {
  const params = useParams();
  const id = typeof params.id === 'string' ? params.id : Array.isArray(params.id) ? params.id[0] : '';

  const [data, setData] = useState<RegulationDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<AmendmentTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChapterId, setActiveChapterId] = useState<string>('');
  const [activeArticleId, setActiveArticleId] = useState<string>('');
  const [tocOpen, setTocOpen] = useState(false);

  const articleRefs = useRef<Map<string, HTMLElement>>(new Map());

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchRegulationDetail(id),
      fetchAmendmentTimeline(id).catch(() => null),
    ])
      .then(([regData, timelineData]) => {
        setData(regData);
        setTimeline(timelineData);
        if (regData.chapters.length > 0) {
          setActiveChapterId(regData.chapters[0].id);
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Regulasi tidak ditemukan');
      })
      .finally(() => setLoading(false));
  }, [id]);

  // IntersectionObserver for active chapter/article tracking
  useEffect(() => {
    if (!data) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement;
            const chapterId = el.dataset.chapterId;
            const articleId = el.dataset.articleId;
            if (chapterId) setActiveChapterId(chapterId);
            if (articleId) setActiveArticleId(articleId);
          }
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 }
    );

    // Observe chapter sections and articles
    data.chapters.forEach((ch) => {
      const chEl = document.getElementById(`chapter-${ch.id}`);
      if (chEl) {
        chEl.dataset.chapterId = ch.id;
        observer.observe(chEl);
      }
      ch.articles.forEach((art) => {
        const artEl = document.getElementById(`pasal-${art.number}`);
        if (artEl) {
          artEl.dataset.articleId = art.id;
          artEl.dataset.chapterId = ch.id;
          observer.observe(artEl);
        }
      });
    });

    return () => observer.disconnect();
  }, [data]);

  const handleChapterClick = useCallback((chapterId: string) => {
    const el = document.getElementById(`chapter-${chapterId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActiveChapterId(chapterId);
  }, []);

  const handleArticleClick = useCallback((articleId: string) => {
    if (!data) return;
    // Find article number across all chapters
    for (const ch of data.chapters) {
      const art = ch.articles.find((a) => a.id === articleId);
      if (art) {
        const el = document.getElementById(`pasal-${art.number}`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setActiveArticleId(articleId);
        setActiveChapterId(ch.id);
        break;
      }
    }
  }, [data]);

  if (loading) return <LoadingSkeleton />;

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-500/10 flex items-center justify-center text-3xl">
            📄
          </div>
          <h2 className="text-lg font-semibold text-white/80 mb-2">Regulasi tidak ditemukan</h2>
          <p className="text-sm text-white/40 mb-6">{error}</p>
          <Link
            href="/regulations"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.06] text-white/70 text-sm hover:bg-white/[0.1] transition-colors"
          >
            ← Perpustakaan Regulasi
          </Link>
        </div>
      </div>
    );
  }

  const typeLabel = NODE_TYPE_LABEL[data.node_type] ?? data.node_type;
  const statusClass = STATUS_CLASS[data.status] ?? 'bg-slate-500/15 text-slate-400 border border-slate-500/25';
  const statusLabel = data.status === 'active' ? 'Aktif' : data.status === 'amended' ? 'Diamandemen' : data.status === 'repealed' ? 'Dicabut' : data.status;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <motion.div
        className="px-4 pt-6 pb-8 max-w-7xl mx-auto"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-xs text-white/30 mb-5">
          <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
          <span>/</span>
          <Link href="/regulations" className="hover:text-[#AAFF00] transition-colors">Perpustakaan Regulasi</Link>
          <span>/</span>
          <span className="text-white/50 truncate max-w-[200px]">{data.title}</span>
        </nav>

        {/* Back button */}
        <Link
          href="/regulations"
          className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-[#AAFF00] transition-colors mb-4"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Perpustakaan Regulasi
        </Link>

        {/* Badges */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/25">
            {typeLabel}
          </span>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusClass}`}>
            {statusLabel}
          </span>
          <span className="text-xs text-white/30 font-mono">
            No. {data.number} Tahun {data.year}
          </span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-white/90 leading-snug mb-2">
          {data.title}
        </h1>
        {data.about && (
          <p className="text-sm text-white/50 leading-relaxed max-w-2xl">
            Tentang: {data.about}
          </p>
        )}

        {/* Stats row */}
        <div className="flex flex-wrap items-center gap-4 mt-4">
          <span className="text-xs text-white/35 font-mono">{data.chapters.length} Bab</span>
          <span className="text-white/20 text-xs">·</span>
          <span className="text-xs text-white/35 font-mono">
            {data.chapters.reduce((acc, ch) => acc + ch.articles.length, 0)} Pasal
          </span>
          <span className="text-white/20 text-xs">·</span>
          <span className="text-xs text-white/35 font-mono">{data.indexed_chunk_count} indexed</span>
          {data.amendments.length > 0 && (
            <>
              <span className="text-white/20 text-xs">·</span>
              <span className="text-xs text-[#AAFF00]/60 font-mono">🔄 {data.amendments.length} amandemen</span>
            </>
          )}
        </div>

        {/* Mobile ToC toggle */}
        <button
          className="lg:hidden mt-4 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-white/60 hover:bg-white/[0.07] transition-colors"
          onClick={() => setTocOpen((prev) => !prev)}
          aria-expanded={tocOpen}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
          </svg>
          {tocOpen ? 'Sembunyikan Daftar Isi' : 'Tampilkan Daftar Isi'}
        </button>

        {/* Mobile ToC */}
        {tocOpen && (
          <div className="lg:hidden mt-3 p-4 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
            <TableOfContents
              chapters={data.chapters}
              activeChapterId={activeChapterId}
              activeArticleId={activeArticleId}
              onChapterClick={handleChapterClick}
              onArticleClick={handleArticleClick}
            />
          </div>
        )}
      </motion.div>

      {/* Three-column layout */}
      <div className="max-w-7xl mx-auto px-4 pb-16">
        <div className="flex gap-8 items-start">
          {/* Left: ToC sidebar (desktop only) */}
          <aside className="hidden lg:block w-56 flex-shrink-0">
            <TableOfContents
              chapters={data.chapters}
              activeChapterId={activeChapterId}
              activeArticleId={activeArticleId}
              onChapterClick={handleChapterClick}
              onArticleClick={handleArticleClick}
            />
          </aside>

          {/* Center: Article content */}
          <main
            className="flex-1 min-w-0 max-w-2xl"
            ref={(el) => { articleRefs.current.set('main', el as HTMLElement); }}
          >
            {data.chapters.length === 0 ? (
              <p className="text-sm text-white/40 py-8 text-center">Tidak ada konten tersedia untuk regulasi ini.</p>
            ) : (
              data.chapters.map((chapter) => (
                <ArticleRenderer
                  key={chapter.id}
                  chapter={chapter}
                  isActive={chapter.id === activeChapterId}
                />
              ))
            )}

            {/* Amendment Timeline Section */}
            {timeline && timeline.entries.length > 0 && (
              <section className="mt-12 pt-8 border-t border-white/[0.06]">
                <h2 className="text-base font-semibold text-white/70 mb-6">Riwayat Amandemen</h2>
                <AmendmentTimeline timeline={timeline} currentRegulationId={id} />
              </section>
            )}
          </main>

          {/* Right: MetadataPanel (desktop/large only) */}
          <aside className="hidden xl:block w-64 flex-shrink-0">
            <div className="sticky top-4">
              <MetadataPanel regulation={data} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
