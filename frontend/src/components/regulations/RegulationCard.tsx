'use client';

import { motion } from 'framer-motion';
import type { RegulationListItem } from '@/lib/api';

export interface RegulationCardProps {
  regulation: Readonly<RegulationListItem>;
  onClick?: () => void;
}

const NODE_TYPE_BADGE: Record<string, { label: string; className: string }> = {
  law: { label: 'UU', className: 'bg-blue-500/15 text-blue-400 border border-blue-500/25' },
  government_regulation: { label: 'PP', className: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' },
  presidential_regulation: { label: 'Perpres', className: 'bg-purple-500/15 text-purple-400 border border-purple-500/25' },
  ministerial_regulation: { label: 'Permen', className: 'bg-orange-500/15 text-orange-400 border border-orange-500/25' },
};

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  active: { label: 'Aktif', className: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' },
  amended: { label: 'Diamandemen', className: 'bg-amber-500/15 text-amber-400 border border-amber-500/25' },
  repealed: { label: 'Dicabut', className: 'bg-red-500/15 text-red-400 border border-red-500/25' },
};

export default function RegulationCard({ regulation, onClick }: Readonly<RegulationCardProps>) {
  const typeBadge = NODE_TYPE_BADGE[regulation.node_type] ?? {
    label: regulation.node_type,
    className: 'bg-slate-500/15 text-slate-400 border border-slate-500/25',
  };
  const statusBadge = STATUS_BADGE[regulation.status] ?? {
    label: regulation.status,
    className: 'bg-slate-500/15 text-slate-400 border border-slate-500/25',
  };

  return (
    <motion.div
      className="relative flex flex-col gap-3 p-5 bg-white/[0.03] border border-white/[0.06] rounded-2xl cursor-pointer hover:bg-white/[0.05] hover:border-white/[0.1] transition-colors"
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Badge row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${typeBadge.className}`}>
          {typeBadge.label}
        </span>
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusBadge.className}`}>
          {statusBadge.label}
        </span>
        <span className="ml-auto text-xs text-white/30 font-mono">
          No.{regulation.number}/{regulation.year}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-white/85 leading-snug line-clamp-2">
        {regulation.title}
      </h3>

      {/* About */}
      {regulation.about && (
        <p className="text-xs text-white/50 leading-relaxed line-clamp-3">
          Tentang: {regulation.about}
        </p>
      )}

      {/* Stats row */}
      <div className="flex items-center gap-3 mt-auto pt-2 border-t border-white/[0.04]">
        <span className="text-xs text-white/40 font-mono">
          {regulation.article_count} Pasal
        </span>
        <span className="text-white/20 text-xs">·</span>
        <span className="text-xs text-white/40 font-mono">
          {regulation.chapter_count} Bab
        </span>
        <span className="text-white/20 text-xs">·</span>
        <span className="text-xs text-white/40 font-mono">
          {regulation.indexed_chunk_count} indexed
        </span>

        {regulation.amendment_count > 0 && (
          <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#AAFF00]/10 text-[#AAFF00]/80 text-xs font-medium border border-[#AAFF00]/15">
            🔄 {regulation.amendment_count} amandemen
          </span>
        )}
      </div>
    </motion.div>
  );
}
