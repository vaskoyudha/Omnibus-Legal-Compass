'use client';

import { motion } from 'framer-motion';
import type { RegulationListItem } from '@/lib/api';

export interface RegulationCardProps {
  regulation: Readonly<RegulationListItem>;
  onClick?: () => void;
}

const NODE_TYPE_BADGE: Record<string, { label: string; color: string; bg: string; border: string }> = {
  law: { label: 'UU', color: 'text-blue-400', bg: 'bg-blue-500/15', border: 'border-blue-500/25' },
  government_regulation: { label: 'PP', color: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/25' },
  presidential_regulation: { label: 'Perpres', color: 'text-purple-400', bg: 'bg-purple-500/15', border: 'border-purple-500/25' },
  ministerial_regulation: { label: 'Permen', color: 'text-orange-400', bg: 'bg-orange-500/15', border: 'border-orange-500/25' },
};

const STATUS_BADGE: Record<string, { label: string; color: string; dot: string }> = {
  active: { label: 'Aktif', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  amended: { label: 'Diamandemen', color: 'text-amber-400', dot: 'bg-amber-400' },
  repealed: { label: 'Dicabut', color: 'text-red-400', dot: 'bg-red-400' },
};

export default function RegulationCard({ regulation, onClick }: Readonly<RegulationCardProps>) {
  const typeBadge = NODE_TYPE_BADGE[regulation.node_type] ?? {
    label: regulation.node_type, color: 'text-slate-400', bg: 'bg-slate-500/15', border: 'border-slate-500/25',
  };
  const statusBadge = STATUS_BADGE[regulation.status] ?? {
    label: regulation.status, color: 'text-slate-400', dot: 'bg-slate-400',
  };

  return (
    <motion.div
      className="relative flex flex-col gap-3.5 p-5 rounded-2xl cursor-pointer group overflow-hidden transition-all duration-300 border border-white/[0.06] hover:border-[#AAFF00]/30"
      style={{
        background: 'linear-gradient(180deg, rgba(255,255,255,0.025) 0%, rgba(255,255,255,0.01) 100%)',
      }}
      onClick={onClick}
      whileHover={{ y: -4, transition: { duration: 0.25 } }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Hover glow */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none bg-[radial-gradient(ellipse_at_50%_0%,rgba(170,255,0,0.06)_0%,transparent_60%)]" />
      {/* Top highlight line */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent group-hover:via-[#AAFF00]/30 transition-all duration-500" />

      <div className="relative z-10 flex flex-col gap-3.5 h-full">
        {/* Header: badges + number */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-bold tracking-wide ${typeBadge.bg} ${typeBadge.color} border ${typeBadge.border}`}>
            {typeBadge.label}
          </span>
          <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-bold bg-white/[0.03] border border-white/[0.06] ${statusBadge.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusBadge.dot}`} />
            {statusBadge.label}
          </span>
          <span className="ml-auto text-[11px] text-white/25 font-mono font-bold tracking-wide">
            No.{regulation.number}/{regulation.year}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-[15px] font-bold text-white/90 leading-snug line-clamp-2 group-hover:text-white transition-colors">
          {regulation.title}
        </h3>

        {/* About */}
        {regulation.about && (
          <p className="text-xs text-white/40 leading-relaxed line-clamp-2 font-medium">
            {regulation.about}
          </p>
        )}

        {/* Stats footer */}
        <div className="flex items-center gap-3 mt-auto pt-3 border-t border-white/[0.05]">
          <span className="flex items-center gap-1 text-[11px] text-white/35 font-mono font-bold">
            <svg className="w-3 h-3 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            {regulation.article_count} Pasal
          </span>
          <span className="text-white/10 text-[8px]">●</span>
          <span className="flex items-center gap-1 text-[11px] text-white/35 font-mono font-bold">
            <svg className="w-3 h-3 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
            {regulation.chapter_count} Bab
          </span>
          <span className="text-white/10 text-[8px]">●</span>
          <span className="flex items-center gap-1 text-[11px] text-white/35 font-mono font-bold">
            <svg className="w-3 h-3 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
            {regulation.indexed_chunk_count}
          </span>

          {regulation.amendment_count > 0 && (
            <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-[#AAFF00]/10 text-[#AAFF00] text-[10px] font-bold border border-[#AAFF00]/20">
              ↻ {regulation.amendment_count}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
