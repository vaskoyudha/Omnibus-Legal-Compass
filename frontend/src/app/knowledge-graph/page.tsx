'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import Link from 'next/link';
import { toast } from 'sonner';
import {
  fetchGraphLaws,
  fetchGraphLaw,
  fetchGraphSearch,
  fetchGraphStats,
  GraphNode,
  GraphStats,
  GraphNodeType
} from '@/lib/api';
import SkeletonLoader from '@/components/SkeletonLoader';

/* ─── Variants ─── */
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

/* ─── Helpers ─── */
const getNodeTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    law: 'Undang-Undang', government_regulation: 'Peraturan Pemerintah',
    presidential_regulation: 'Peraturan Presiden', ministerial_regulation: 'Peraturan Menteri',
    chapter: 'Bab', article: 'Pasal',
  };
  return labels[type] || type;
};

const getStatusConfig = (status?: string) => {
  switch (status) {
    case 'active': return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', label: 'Aktif' };
    case 'amended': return { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Diubah' };
    case 'repealed': return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Dicabut' };
    default: return { color: 'text-white/40', bg: 'bg-white/5', border: 'border-white/10', label: 'N/A' };
  }
};

/* ─── Tree Node ─── */
const TreeNode = ({ node, level = 0, onExpand, expandedIds, onViewArticle }: {
  node: GraphNode; level?: number;
  onExpand: (node: GraphNode) => void; expandedIds: Set<string>;
  onViewArticle: (node: GraphNode) => void;
}) => {
  const isExpanded = expandedIds.has(node.id);
  const hasChildren = node.children && node.children.length > 0;
  const isArticle = node.node_type === 'article';
  const status = getStatusConfig(node.status);
  const paddingLeft = `${level * 1.5 + 1}rem`;

  return (
    <div className="group relative">
      <div className="absolute inset-0 bg-gradient-to-r from-[#AAFF00]/0 to-transparent group-hover:from-[#AAFF00]/[0.03] transition-all duration-300 pointer-events-none" />
      {isExpanded && <div className="absolute inset-y-0 left-0 w-[2px] bg-gradient-to-b from-[#AAFF00] to-transparent pointer-events-none" />}

      <div
        className={`relative z-10 flex items-center gap-3 py-3 pr-4 border-b border-white/[0.05] cursor-pointer ${isExpanded ? 'bg-white/[0.03]' : ''}`}
        style={{ paddingLeft }}
        onClick={() => isArticle ? onViewArticle(node) : onExpand(node)}
      >
        <div className="flex-shrink-0 w-6 flex justify-center">
          {!isArticle ? (
            <motion.svg animate={{ rotate: isExpanded ? 90 : 0 }}
              className={`w-4 h-4 text-white/40 group-hover:text-[#AAFF00] transition-colors ${hasChildren || node.node_type === 'law' ? 'opacity-100' : 'opacity-30'}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </motion.svg>
          ) : (
            <svg className="w-4 h-4 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[15px] font-medium ${isArticle ? 'text-white/60' : 'text-white/90 group-hover:text-[#AAFF00] transition-colors'}`}>
              {node.node_type === 'law' ? (
                <>
                  <span className="text-[#AAFF00] mr-2">{node.title?.split('tentang')[0] || `UU No. ${node.number} Tahun ${node.year}`}</span>
                  <span className="text-white/30 font-normal text-xs">{node.year}</span>
                </>
              ) : (
                node.title || `${getNodeTypeLabel(node.node_type)} ${node.number}`
              )}
            </span>
            {node.status && node.node_type === 'law' && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${status.bg} ${status.color} ${status.border}`}>{status.label}</span>
            )}
          </div>
          {node.about && <p className="text-xs text-white/40 truncate mt-1 max-w-2xl">{node.about}</p>}
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && hasChildren && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            {node.children!.map((child) => (
              <TreeNode key={child.id} node={child} level={level + 1} onExpand={onExpand} expandedIds={expandedIds} onViewArticle={onViewArticle} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

/* ─── Main Page ─── */
export default function KnowledgeGraphPage() {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [laws, setLaws] = useState<GraphNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeType, setSelectedNodeType] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedArticle, setSelectedArticle] = useState<GraphNode | null>(null);
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    const init = async () => {
      try {
        const [statsData, lawsData] = await Promise.all([fetchGraphStats(), fetchGraphLaws()]);
        setStats(statsData); setLaws(lawsData);
      } catch { toast.error('Gagal memuat data graf'); }
      finally { setLoading(false); }
    };
    init();
  }, []);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const results = await fetchGraphSearch(searchQuery, selectedNodeType || undefined);
      setLaws(results); setExpandedIds(new Set());
    } catch { toast.error('Pencarian gagal'); }
    finally { setLoading(false); }
  }, [searchQuery, selectedNodeType]);

  const resetSearch = async () => {
    setSearchQuery(''); setSelectedNodeType(null); setLoading(true);
    try {
      const lawsData = await fetchGraphLaws();
      setLaws(lawsData); setExpandedIds(new Set());
    } catch { toast.error('Gagal memuat ulang data'); }
    finally { setLoading(false); }
  };

  const handleExpand = async (node: GraphNode) => {
    const isExpanded = expandedIds.has(node.id);
    const newExpanded = new Set(expandedIds);
    if (isExpanded) { newExpanded.delete(node.id); setExpandedIds(newExpanded); return; }
    if (!node.children || node.children.length === 0) {
      if (node.node_type === 'law') {
        setLoadingNodes(new Set(loadingNodes).add(node.id));
        try {
          const fullLaw = await fetchGraphLaw(node.id);
          setLaws(prev => prev.map(l => l.id === node.id ? { ...l, children: fullLaw.children } : l));
          newExpanded.add(node.id); setExpandedIds(newExpanded);
        } catch { toast.error('Gagal memuat detail regulasi'); }
        finally { const nl = new Set(loadingNodes); nl.delete(node.id); setLoadingNodes(nl); }
      } else { newExpanded.add(node.id); setExpandedIds(newExpanded); }
    } else { newExpanded.add(node.id); setExpandedIds(newExpanded); }
  };

  const STAT_ITEMS = stats ? [
    { label: 'Total Node', value: stats.total_nodes.toLocaleString(), color: 'text-white', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
    { label: 'Total Relasi', value: stats.total_edges.toLocaleString(), color: 'text-[#AAFF00]', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' },
    { label: 'Undang-Undang', value: String(stats.nodes_by_type.law || 0), color: 'text-amber-400', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' },
    { label: 'Total Pasal', value: String(stats.nodes_by_type.article || 0), color: 'text-emerald-400', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  ] : [];

  return (
    <div className="min-h-screen bg-[#0A0A0F] relative overflow-hidden -mt-16 sm:-mt-20">
      {/* Film Grain */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
        backgroundSize: '200px 200px',
      }} />

      {/* Ambient Glow */}
      <div className="fixed inset-0 pointer-events-none z-[-1]">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[500px] bg-gradient-to-b from-[#AAFF00]/[0.04] to-transparent rounded-full blur-3xl" />
        <div className="absolute top-1/3 left-0 w-[400px] h-[400px] bg-[radial-gradient(ellipse_at_left,rgba(170,255,0,0.03),transparent_70%)] blur-2xl" />
      </div>

      {/* ═══ HERO ═══ */}
      <div className="relative pt-20 sm:pt-24 pb-6 px-4 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[250px] bg-[radial-gradient(ellipse_at_center,rgba(170,255,0,0.08)_0%,transparent_70%)] blur-[60px]" />
        </div>

        <div className="relative max-w-6xl mx-auto z-10">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8">
            <div className="max-w-2xl">
              <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-5">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#0A0A0F]/80 backdrop-blur-xl border border-[#AAFF00]/30 text-xs font-bold text-[#AAFF00] uppercase tracking-widest shadow-[0_0_20px_rgba(170,255,0,0.15)]">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                  Knowledge Graph
                </div>
              </motion.div>
              <motion.h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tighter text-white mb-4 leading-[1.1]"
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                Graf Pengetahuan{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-br from-[#AAFF00] via-white to-white/40">Hukum.</span>
              </motion.h1>
              <motion.p className="text-white/50 text-base lg:text-lg font-light leading-relaxed max-w-lg"
                initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                Jelajahi hierarki dan hubungan antar peraturan perundang-undangan Indonesia.
              </motion.p>
            </div>

            {/* Stats Pills */}
            {stats && (
              <motion.div className="flex items-center gap-4 flex-wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
                {STAT_ITEMS.map((s, i) => (
                  <div key={i} className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <svg className={`w-4 h-4 ${s.color} opacity-60`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d={s.icon} /></svg>
                    <div>
                      <p className={`font-mono text-lg font-black ${s.color} leading-none`}>{s.value}</p>
                      <p className="text-[10px] text-white/30 uppercase tracking-widest font-bold">{s.label}</p>
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* ═══ SEARCH BAR (Sticky) ═══ */}
      <div className="sticky top-0 z-40 backdrop-blur-2xl bg-[#0A0A0F]/80 border-b border-white/[0.05]">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 group">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-white/25 group-focus-within:text-[#AAFF00] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" /></svg>
              </span>
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cari regulasi, pasal, atau topik..."
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0A0A0F]/60 border border-white/[0.08] text-white/90 text-sm font-medium placeholder:text-white/25 focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/40 focus:border-[#AAFF00]/40 hover:border-white/[0.15] transition-all" />
            </div>
            <div className="flex gap-2 flex-wrap">
              {[null, 'law', 'government_regulation', 'presidential_regulation', 'ministerial_regulation'].map((type) => (
                <button key={type ?? 'all'} type="button" onClick={() => setSelectedNodeType(type)}
                  className={`px-3.5 py-2.5 text-xs font-bold rounded-xl border transition-all ${selectedNodeType === type
                    ? 'bg-[#AAFF00]/10 border-[#AAFF00]/40 text-[#AAFF00]'
                    : 'border-white/[0.06] text-white/40 hover:text-white/60 hover:bg-white/[0.03]'}`}>
                  {type ? getNodeTypeLabel(type) : 'Semua'}
                </button>
              ))}
            </div>
            <button type="submit" className="px-6 py-2.5 bg-[#AAFF00] text-[#0A0A0F] font-bold text-sm rounded-xl hover:shadow-[0_0_20px_rgba(170,255,0,0.3)] transition-all whitespace-nowrap">
              Cari
            </button>
            {searchQuery && (
              <button type="button" onClick={resetSearch} className="px-4 py-2.5 text-xs font-bold text-white/40 hover:text-white border border-white/[0.06] rounded-xl transition-colors">
                Reset
              </button>
            )}
          </form>
        </div>
      </div>

      {/* ═══ TREE VIEW ═══ */}
      <div className="max-w-6xl mx-auto px-4 pt-8 pb-20 relative z-10">
        <motion.div className="rounded-2xl overflow-hidden border border-white/[0.06]" style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.005) 100%)' }}
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="px-6 py-4 border-b border-white/[0.06] flex justify-between items-center">
            <h2 className="text-sm font-bold text-white/80 uppercase tracking-wide flex items-center gap-2">
              <svg className="w-4 h-4 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
              Daftar Regulasi
            </h2>
            <span className="text-xs font-bold text-[#AAFF00] tracking-widest">{laws.length} DOKUMEN</span>
          </div>

          {loading ? (
            <div className="p-6 space-y-4"><SkeletonLoader variant="text" /><SkeletonLoader variant="text" /><SkeletonLoader variant="text" /></div>
          ) : laws.length === 0 ? (
            <div className="p-16 text-center">
              <div className="w-16 h-16 bg-white/[0.03] border border-white/[0.06] rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white/15" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              </div>
              <p className="text-white/50 font-semibold mb-1">Tidak ada data ditemukan</p>
              <p className="text-white/25 text-sm">Coba kata kunci lain atau ubah filter</p>
            </div>
          ) : (
            <div>
              {laws.map((node) => (
                <div key={node.id} className="relative">
                  <TreeNode node={node} onExpand={handleExpand} expandedIds={expandedIds} onViewArticle={setSelectedArticle} />
                  {loadingNodes.has(node.id) && (
                    <div className="absolute top-4 right-4">
                      <svg className="animate-spin h-4 w-4 text-[#AAFF00]" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Article Modal */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSelectedArticle(null)} className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
            <motion.div initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col border border-white/[0.08]"
              style={{ background: 'linear-gradient(180deg, rgba(15,15,20,0.98) 0%, rgba(10,10,15,0.98) 100%)', backdropFilter: 'blur(40px)' }}>
              <div className="p-6 border-b border-white/[0.06] flex justify-between items-start bg-[#AAFF00]/[0.02]">
                <div>
                  <h3 className="text-xl font-bold text-white mb-1">{selectedArticle.title || `Pasal ${selectedArticle.number}`}</h3>
                  <p className="text-sm text-white/40">{getNodeTypeLabel(selectedArticle.node_type)}</p>
                </div>
                <button onClick={() => setSelectedArticle(null)} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
                  <svg className="w-5 h-5 text-white/40" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <p className="text-white/80 leading-relaxed whitespace-pre-wrap text-sm font-light">{selectedArticle.full_text || selectedArticle.about || "Konten tidak tersedia."}</p>
              </div>
              <div className="p-4 border-t border-white/[0.06] flex justify-end">
                <button onClick={() => setSelectedArticle(null)} className="px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-sm font-bold text-white/60 transition-colors border border-white/[0.06]">Tutup</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
