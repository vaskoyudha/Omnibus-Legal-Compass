'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
import SpotlightCard from '@/components/reactbits/SpotlightCard';

// Animation Variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } 
  },
};

// Helper for labels
const getNodeTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    law: 'Undang-Undang',
    government_regulation: 'Peraturan Pemerintah',
    presidential_regulation: 'Peraturan Presiden',
    ministerial_regulation: 'Peraturan Menteri',
    chapter: 'Bab',
    article: 'Pasal',
  };
  return labels[type] || type;
};

// Helper for status badges
const getStatusConfig = (status?: string) => {
  switch (status) {
    case 'active':
      return { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', label: 'Aktif' };
    case 'amended':
      return { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20', label: 'Diubah' };
    case 'repealed':
      return { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', label: 'Dicabut' };
    default:
      return { color: 'text-text-muted', bg: 'bg-white/5', border: 'border-white/10', label: 'Tidak Diketahui' };
  }
};

// Recursive Tree Node Component
const TreeNode = ({ 
  node, 
  level = 0, 
  onExpand, 
  expandedIds,
  onViewArticle 
}: { 
  node: GraphNode; 
  level?: number; 
  onExpand: (node: GraphNode) => void; 
  expandedIds: Set<string>;
  onViewArticle: (node: GraphNode) => void;
}) => {
  const isExpanded = expandedIds.has(node.id);
  const hasChildren = node.children && node.children.length > 0;
  const isArticle = node.node_type === 'article';
  const status = getStatusConfig(node.status);
  
  // Indentation based on level
  const paddingLeft = `${level * 1.5 + 1}rem`;

  return (
    <div className="group">
      <div 
        className={`
          flex items-center gap-3 py-3 pr-4 border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer
          ${isExpanded ? 'bg-white/[0.02]' : ''}
        `}
        style={{ paddingLeft }}
        onClick={() => {
          if (isArticle) {
            onViewArticle(node);
          } else {
            onExpand(node);
          }
        }}
      >
        {/* Chevron / Icon */}
        <div className="flex-shrink-0 w-6 flex justify-center">
          {!isArticle ? (
            <motion.svg 
              animate={{ rotate: isExpanded ? 90 : 0 }}
              className={`w-4 h-4 text-text-muted ${hasChildren || node.node_type === 'law' ? 'opacity-100' : 'opacity-30'}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </motion.svg>
          ) : (
            <svg className="w-4 h-4 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-medium ${isArticle ? 'text-text-secondary' : 'text-text-primary'}`}>
              {node.node_type === 'law' ? (
                <>
                  <span className="text-[#AAFF00] mr-2">{node.title?.split('tentang')[0] || `UU No. ${node.number} Tahun ${node.year}`}</span>
                  <span className="text-text-muted font-normal text-xs">{node.year}</span>
                </>
              ) : (
                node.title || `${getNodeTypeLabel(node.node_type)} ${node.number}`
              )}
            </span>
            
            {node.status && node.node_type === 'law' && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${status.bg} ${status.color} ${status.border}`}>
                {status.label}
              </span>
            )}
          </div>
          
          {node.about && (
            <p className="text-xs text-text-muted truncate mt-0.5 max-w-2xl">
              {node.about}
            </p>
          )}
        </div>
      </div>

      {/* Children */}
      <AnimatePresence>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            {node.children!.map((child) => (
              <TreeNode 
                key={child.id} 
                node={child} 
                level={level + 1} 
                onExpand={onExpand} 
                expandedIds={expandedIds}
                onViewArticle={onViewArticle}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default function KnowledgeGraphPage() {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [laws, setLaws] = useState<GraphNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeType, setSelectedNodeType] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [selectedArticle, setSelectedArticle] = useState<GraphNode | null>(null);
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set());

  // Initial Load
  useEffect(() => {
    const init = async () => {
    try {
      const [statsData, lawsData] = await Promise.all([
        fetchGraphStats(),
        fetchGraphLaws()
      ]);
      setStats(statsData);
      setLaws(lawsData);
    } catch (error) {
      // Graph load failed; user notified
      toast.error('Gagal memuat data graf');
    } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Search Handler
  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const results = await fetchGraphSearch(searchQuery, selectedNodeType || undefined);
      setLaws(results);
      // Collapse all when searching new results
      setExpandedIds(new Set()); 
    } catch (error) {
      toast.error('Pencarian gagal');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedNodeType]);

  // Reset Search
  const resetSearch = async () => {
    setSearchQuery('');
    setSelectedNodeType(null);
    setLoading(true);
    try {
      const lawsData = await fetchGraphLaws();
      setLaws(lawsData);
      setExpandedIds(new Set());
    } catch (error) {
      toast.error('Gagal memuat ulang data');
    } finally {
      setLoading(false);
    }
  };

  // Expand/Collapse Handler
  const handleExpand = async (node: GraphNode) => {
    const isExpanded = expandedIds.has(node.id);
    const newExpanded = new Set(expandedIds);

    if (isExpanded) {
      newExpanded.delete(node.id);
      setExpandedIds(newExpanded);
      return;
    }

    // If expanding and children missing (lazy load for laws)
    if (!node.children || node.children.length === 0) {
      // Only laws need lazy loading usually, as chapters come with the law detail
      if (node.node_type === 'law') {
        setLoadingNodes(new Set(loadingNodes).add(node.id));
        try {
          const fullLaw = await fetchGraphLaw(node.id);
          
          // Update the specific node in our laws state
          // This is a simple deep update for the top-level laws list
          setLaws(prev => prev.map(l => l.id === node.id ? { ...l, children: fullLaw.children } : l));
          
          newExpanded.add(node.id);
          setExpandedIds(newExpanded);
        } catch (error) {
          toast.error('Gagal memuat detail regulasi');
        } finally {
          const newLoading = new Set(loadingNodes);
          newLoading.delete(node.id);
          setLoadingNodes(newLoading);
        }
      } else {
        // For other nodes without children, just expand (shows empty or previously loaded)
        newExpanded.add(node.id);
        setExpandedIds(newExpanded);
      }
    } else {
      // Already has children, just toggle
      newExpanded.add(node.id);
      setExpandedIds(newExpanded);
    }
  };

  return (
    <div className="min-h-screen pb-20">
      {/* Breadcrumb */}
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <nav className="flex items-center gap-2 text-xs text-text-muted">
          <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
          <span>/</span>
          <span className="text-text-primary">Graf Hukum</span>
        </nav>
      </div>

      {/* Hero Section */}
      <motion.div
        className="py-8 px-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="max-w-6xl mx-auto text-center">
          <motion.div className="mb-4" variants={itemVariants}>
            <span className="ai-badge">
              <span>🔗</span> Knowledge Graph
            </span>
          </motion.div>
          <motion.h1 className="text-4xl font-extrabold text-gradient mb-2" variants={itemVariants}>
            Graf Pengetahuan Hukum
          </motion.h1>
          <motion.p className="text-text-secondary max-w-2xl mx-auto" variants={itemVariants}>
            Jelajahi hierarki dan hubungan antar peraturan perundang-undangan Indonesia
          </motion.p>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 space-y-8">
        
        {/* Stats Section */}
        {stats && (
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SpotlightCard className="p-6 bg-white/[0.03] border border-white/10 rounded-2xl">
              <h3 className="text-3xl font-bold text-text-primary mb-1">{stats.total_nodes}</h3>
              <p className="text-sm text-text-muted">Total Regulasi & Pasal</p>
            </SpotlightCard>
            <SpotlightCard className="p-6 bg-white/[0.03] border border-white/10 rounded-2xl">
              <h3 className="text-3xl font-bold text-[#AAFF00] mb-1">{stats.total_edges}</h3>
              <p className="text-sm text-text-muted">Total Relasi</p>
            </SpotlightCard>
            <SpotlightCard className="p-6 bg-white/[0.03] border border-white/10 rounded-2xl">
              <h3 className="text-3xl font-bold text-amber-400 mb-1">{stats.nodes_by_type.law || 0}</h3>
              <p className="text-sm text-text-muted">Undang-Undang</p>
            </SpotlightCard>
            <SpotlightCard className="p-6 bg-white/[0.03] border border-white/10 rounded-2xl">
              <h3 className="text-3xl font-bold text-emerald-400 mb-1">{stats.nodes_by_type.article || 0}</h3>
              <p className="text-sm text-text-muted">Total Pasal</p>
            </SpotlightCard>
          </motion.div>
        )}

        {/* Search & Filter */}
        <motion.div 
          className="glass-strong rounded-2xl p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cari regulasi, pasal, atau topik..."
                className="flex-1 px-4 py-3 rounded-xl dark-input text-sm"
              />
              <button 
                type="submit" 
                className="px-6 py-3 bg-gradient-to-r from-[#AAFF00] to-[#88CC00] text-[#0A0A0F] font-semibold rounded-xl hover:shadow-lg hover:shadow-[#AAFF00]/20 transition-all whitespace-nowrap"
              >
                Cari
              </button>
            </div>
            
            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSelectedNodeType(null)}
                className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${!selectedNodeType ? 'bg-[#AAFF00]/10 border-[#AAFF00]/50 text-[#AAFF00]' : 'border-white/10 text-text-secondary hover:bg-white/5'}`}
              >
                Semua
              </button>
              {['law', 'government_regulation', 'presidential_regulation', 'ministerial_regulation'].map(type => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedNodeType(type)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${selectedNodeType === type ? 'bg-[#AAFF00]/10 border-[#AAFF00]/50 text-[#AAFF00]' : 'border-white/10 text-text-secondary hover:bg-white/5'}`}
                >
                  {getNodeTypeLabel(type)}
                </button>
              ))}
              {searchQuery && (
                <button 
                  type="button" 
                  onClick={resetSearch}
                  className="ml-auto text-xs text-text-muted hover:text-white underline"
                >
                  Reset Filter
                </button>
              )}
            </div>
          </form>
        </motion.div>

        {/* Tree View Results */}
        <motion.div 
          className="glass-strong rounded-2xl overflow-hidden min-h-[400px]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-white/[0.02]">
            <h2 className="font-semibold text-text-primary">Daftar Regulasi</h2>
            <span className="text-xs text-text-muted">{laws.length} dokumen ditemukan</span>
          </div>
          
          {loading ? (
            <div className="p-6 space-y-4">
              <SkeletonLoader variant="text" />
              <SkeletonLoader variant="text" />
              <SkeletonLoader variant="text" />
            </div>
          ) : laws.length === 0 ? (
            <div className="p-12 text-center">
              <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-text-secondary">Tidak ada data ditemukan</p>
              <p className="text-sm text-text-muted mt-1">Coba kata kunci lain atau ubah filter</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {laws.map((node) => (
                <div key={node.id} className="relative">
                  <TreeNode 
                    node={node} 
                    onExpand={handleExpand}
                    expandedIds={expandedIds}
                    onViewArticle={setSelectedArticle}
                  />
                  {loadingNodes.has(node.id) && (
                    <div className="absolute top-4 right-4">
                      <svg className="animate-spin h-4 w-4 text-[#AAFF00]" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Article Detail Modal */}
      <AnimatePresence>
        {selectedArticle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              onClick={() => setSelectedArticle(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-2xl glass-strong rounded-2xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col"
            >
              <div className="p-6 border-b border-white/10 flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-bold text-text-primary mb-1">
                    {selectedArticle.title || `Pasal ${selectedArticle.number}`}
                  </h3>
                  <p className="text-sm text-text-muted">
                    {/* Access parent info if available, otherwise just node type */}
                    {getNodeTypeLabel(selectedArticle.node_type)}
                  </p>
                </div>
                <button 
                  onClick={() => setSelectedArticle(null)}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="p-6 overflow-y-auto">
                <div className="prose prose-invert max-w-none">
                  <p className="text-text-primary leading-relaxed whitespace-pre-wrap">
                    {selectedArticle.full_text || selectedArticle.about || "Konten tidak tersedia."}
                  </p>
                </div>
              </div>

              <div className="p-4 border-t border-white/10 bg-white/[0.02] flex justify-end">
                <button
                  onClick={() => setSelectedArticle(null)}
                  className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm font-medium transition-colors"
                >
                  Tutup
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
