'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { toast } from 'sonner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  fetchDashboardCoverage,
  fetchDashboardStats,
  LawCoverage,
  DashboardStats,
} from '@/lib/api';
import SkeletonLoader from '@/components/SkeletonLoader';

// Animation variants (project pattern)
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
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

// Icons
const DashboardIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
  </svg>
);

const ChevronIcon = ({ className, direction = 'down' }: { className?: string; direction?: 'down' | 'up' }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${direction === 'up' ? 'rotate-180' : ''} ${className}`}>
    <path d="m6 9 6 6 6-6" />
  </svg>
);

// Coverage color helpers
function getCoverageColor(pct: number): string {
  if (pct >= 80) return '#22c55e'; // green-500
  if (pct >= 50) return '#eab308'; // yellow-500
  return '#ef4444'; // red-500
}

function getCoverageBg(pct: number): string {
  if (pct >= 80) return 'bg-emerald-500/20 border-emerald-500/30';
  if (pct >= 50) return 'bg-yellow-500/20 border-yellow-500/30';
  return 'bg-red-500/20 border-red-500/30';
}

function getCoverageLabel(pct: number): string {
  if (pct >= 80) return 'Tinggi';
  if (pct >= 50) return 'Sedang';
  return 'Rendah';
}

// Regulation type labels
const getRegTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    law: 'UU',
    government_regulation: 'PP',
    presidential_regulation: 'Perpres',
    ministerial_regulation: 'Permen',
  };
  return labels[type] || type;
};

// Group coverage by domain
interface DomainGroup {
  domain: string;
  totalArticles: number;
  indexedArticles: number;
  coveragePercent: number;
  regulationCount: number;
  laws: LawCoverage[];
}

function groupByDomain(items: LawCoverage[]): DomainGroup[] {
  const map = new Map<string, DomainGroup>();
  for (const item of items) {
    let group = map.get(item.domain);
    if (!group) {
      group = {
        domain: item.domain,
        totalArticles: 0,
        indexedArticles: 0,
        coveragePercent: 0,
        regulationCount: 0,
        laws: [],
      };
      map.set(item.domain, group);
    }
    group.totalArticles += item.total_articles;
    group.indexedArticles += item.indexed_articles;
    group.regulationCount += 1;
    group.laws.push(item);
  }
  for (const g of map.values()) {
    g.coveragePercent = g.totalArticles > 0
      ? Math.round((g.indexedArticles / g.totalArticles) * 1000) / 10
      : 0;
  }
  return Array.from(map.values()).sort((a, b) => a.domain.localeCompare(b.domain));
}

// Custom tooltip for bar chart
function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: DomainGroup }> }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass-strong rounded-lg p-3 border border-white/10 text-xs">
      <p className="font-semibold text-text-primary mb-1">{d.domain}</p>
      <p className="text-text-secondary">Regulasi: {d.regulationCount}</p>
      <p className="text-text-secondary">Pasal: {d.indexedArticles}/{d.totalArticles}</p>
      <p className="text-text-secondary">Coverage: {d.coveragePercent}%</p>
    </div>
  );
}

export default function DashboardPage() {
  const [coverage, setCoverage] = useState<LawCoverage[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [cov, st] = await Promise.all([
        fetchDashboardCoverage(),
        fetchDashboardStats(),
      ]);
      setCoverage(cov);
      setStats(st);
    } catch (err) {
      // Dashboard fetch failed; user notified
      toast.error('Gagal memuat data dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const domains = useMemo(() => groupByDomain(coverage), [coverage]);

  // Chart data
  const chartData = useMemo(
    () => domains.map((d) => ({ ...d, name: d.domain })),
    [domains]
  );

  return (
    <div className="min-h-screen pt-24 pb-10 px-4">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-2"
        >
          <div className="flex items-center gap-2 text-sm text-text-muted mb-1">
            <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
            <span>/</span>
            <span className="text-text-primary">Dashboard</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="ai-badge flex items-center gap-2">
              <DashboardIcon className="w-4 h-4" />
              <span>Compliance Dashboard</span>
            </div>
          </div>
          <h1 className="text-3xl font-bold text-text-primary">Dashboard Kepatuhan</h1>
          <p className="text-text-secondary max-w-2xl">
            Visualisasi cakupan indeks peraturan Indonesia. Pantau regulasi yang sudah terindeks, identifikasi celah, dan lihat statistik sistem secara keseluruhan.
          </p>
        </motion.div>

        {loading ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="glass-strong rounded-xl p-5 border border-white/5">
                  <SkeletonLoader variant="text" lines={2} />
                </div>
              ))}
            </div>
            <div className="glass-strong rounded-xl p-6 border border-white/5">
              <SkeletonLoader variant="text" lines={8} />
            </div>
          </div>
        ) : (
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Stats Cards */}
            {stats && (
              <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  label="Total Regulasi"
                  value={stats.total_regulations}
                  sub={`${stats.domain_count} domain hukum`}
                />
                <StatCard
                  label="Total Pasal"
                  value={stats.total_articles}
                  sub={`${stats.total_chapters} bab`}
                />
                <StatCard
                  label="Pasal Terindeks"
                  value={stats.indexed_articles}
                  sub={`${stats.overall_coverage_percent}% coverage`}
                  accent
                />
                <StatCard
                  label="Total Relasi"
                  value={stats.total_edges}
                  sub="Tautan dalam graf"
                />
              </motion.div>
            )}

            {/* Coverage Indicator */}
            {stats && (
              <motion.div variants={itemVariants} className="glass-strong rounded-2xl p-6 border border-white/5">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-text-primary">Coverage Keseluruhan</h2>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getCoverageBg(stats.overall_coverage_percent)}`}>
                    {getCoverageLabel(stats.overall_coverage_percent)} — {stats.overall_coverage_percent}%
                  </span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-3 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${stats.overall_coverage_percent}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: getCoverageColor(stats.overall_coverage_percent) }}
                  />
                </div>
                <div className="flex justify-between mt-2 text-xs text-text-muted">
                  <span>{stats.indexed_articles} pasal terindeks</span>
                  <span>{stats.total_articles - stats.indexed_articles} pasal belum terindeks</span>
                </div>
                {stats.most_covered_domain && stats.least_covered_domain && (
                  <div className="flex flex-wrap gap-4 mt-4 text-xs text-text-secondary">
                    <span>
                      Tertinggi: <span className="text-emerald-400 font-medium">{stats.most_covered_domain}</span>
                    </span>
                    <span>
                      Terendah: <span className="text-red-400 font-medium">{stats.least_covered_domain}</span>
                    </span>
                  </div>
                )}
              </motion.div>
            )}

            {/* Domain Bar Chart */}
            {domains.length > 0 && (
              <motion.div variants={itemVariants} className="glass-strong rounded-2xl p-6 border border-white/5">
                <h2 className="text-lg font-semibold text-text-primary mb-6">Coverage per Domain Hukum</h2>
                <div className="w-full h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={130} tick={{ fill: '#e2e8f0', fontSize: 12 }} />
                      <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                      <Bar dataKey="coveragePercent" radius={[0, 6, 6, 0]} barSize={24} name="Coverage %">
                        {chartData.map((entry, idx) => (
                          <Cell key={idx} fill={getCoverageColor(entry.coveragePercent)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            )}

            {/* Heat Map Grid */}
            {domains.length > 0 && (
              <motion.div variants={itemVariants} className="glass-strong rounded-2xl p-6 border border-white/5">
                <h2 className="text-lg font-semibold text-text-primary mb-4">Peta Panas Regulasi</h2>
                <p className="text-text-muted text-sm mb-6">Klik domain untuk melihat detail regulasi dan pasal yang belum terindeks.</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3" data-testid="coverage-heatmap">
                  {domains.map((d) => (
                    <button
                      key={d.domain}
                      onClick={() => setExpandedDomain(expandedDomain === d.domain ? null : d.domain)}
                      className={`relative p-4 rounded-xl border text-left transition-all hover:scale-[1.02] ${
                        expandedDomain === d.domain
                          ? 'border-[#AAFF00]/40 bg-[#AAFF00]/5'
                          : 'border-white/5 hover:border-white/20'
                      }`}
                      style={{
                        backgroundColor: expandedDomain === d.domain
                          ? undefined
                          : `${getCoverageColor(d.coveragePercent)}10`,
                      }}
                    >
                      <div className="text-sm font-semibold text-text-primary truncate">{d.domain}</div>
                      <div className="text-2xl font-bold mt-1" style={{ color: getCoverageColor(d.coveragePercent) }}>
                        {d.coveragePercent}%
                      </div>
                      <div className="text-xs text-text-muted mt-1">
                        {d.regulationCount} regulasi · {d.totalArticles} pasal
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-1.5 mt-2 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${d.coveragePercent}%`,
                            backgroundColor: getCoverageColor(d.coveragePercent),
                          }}
                        />
                      </div>
                    </button>
                  ))}
                </div>

                {/* Expanded Domain Detail */}
                {expandedDomain && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-6 p-4 glass rounded-xl border border-white/10"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-base font-semibold text-text-primary">{expandedDomain}</h3>
                      <button
                        onClick={() => setExpandedDomain(null)}
                        className="text-text-muted hover:text-text-primary text-xs"
                      >
                        Tutup
                      </button>
                    </div>
                    <div className="space-y-3">
                      {domains
                        .find((d) => d.domain === expandedDomain)
                        ?.laws.map((law) => (
                          <LawCoverageRow key={law.regulation_id} law={law} />
                        ))}
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}

            {/* All Regulations Table */}
            <motion.div variants={itemVariants} className="glass-strong rounded-2xl p-6 border border-white/5">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Semua Regulasi</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-text-muted text-left">
                      <th className="py-3 pr-4">Regulasi</th>
                      <th className="py-3 pr-4">Jenis</th>
                      <th className="py-3 pr-4">Domain</th>
                      <th className="py-3 pr-4 text-right">Pasal</th>
                      <th className="py-3 pr-4 text-right">Terindeks</th>
                      <th className="py-3 text-right">Coverage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverage.map((law) => (
                      <tr key={law.regulation_id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 pr-4 text-text-primary font-medium">{law.title}</td>
                        <td className="py-3 pr-4">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-text-secondary border border-white/10">
                            {getRegTypeLabel(law.regulation_type)}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-text-secondary">{law.domain}</td>
                        <td className="py-3 pr-4 text-right text-text-secondary">{law.total_articles}</td>
                        <td className="py-3 pr-4 text-right text-text-secondary">{law.indexed_articles}</td>
                        <td className="py-3 text-right">
                          <span
                            className="font-semibold"
                            style={{ color: getCoverageColor(law.coverage_percent) }}
                          >
                            {law.coverage_percent}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: number;
  sub: string;
  accent?: boolean;
}) {
  return (
    <div className="glass-strong rounded-xl p-5 border border-white/5">
      <p className="text-xs text-text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? 'text-[#AAFF00]' : 'text-text-primary'}`}>
        {value.toLocaleString()}
      </p>
      <p className="text-xs text-text-secondary mt-1">{sub}</p>
    </div>
  );
}

function LawCoverageRow({ law }: { law: LawCoverage }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-white/5 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-white/[0.02] transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-text-secondary border border-white/10">
            {getRegTypeLabel(law.regulation_type)}
          </span>
          <span className="text-sm text-text-primary font-medium">{law.title}</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-sm font-semibold"
            style={{ color: getCoverageColor(law.coverage_percent) }}
          >
            {law.coverage_percent}%
          </span>
          <span className="text-xs text-text-muted">{law.indexed_articles}/{law.total_articles}</span>
          <ChevronIcon direction={expanded ? 'up' : 'down'} className="text-text-muted" />
        </div>
      </button>
      {expanded && law.missing_articles.length > 0 && (
        <div className="px-3 pb-3 pt-1 border-t border-white/5">
          <p className="text-xs text-text-muted mb-2">Pasal belum terindeks:</p>
          <div className="flex flex-wrap gap-1.5">
            {law.missing_articles.map((id) => (
              <span
                key={id}
                className="text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20"
              >
                {id.split('_').pop()}
              </span>
            ))}
          </div>
        </div>
      )}
      {expanded && law.missing_articles.length === 0 && (
        <div className="px-3 pb-3 pt-1 border-t border-white/5">
          <p className="text-xs text-emerald-400">Semua pasal sudah terindeks</p>
        </div>
      )}
    </div>
  );
}
