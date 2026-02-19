'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { AmendmentTimelineResponse, AmendmentTimelineEntry } from '@/lib/api';

export interface AmendmentTimelineProps {
  timeline: Readonly<AmendmentTimelineResponse>;
  currentRegulationId: string;
}

const EDGE_TYPE_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  AMENDS: { color: 'text-amber-400', bg: 'bg-amber-500/15 border-amber-500/25', label: 'Mengamandemen' },
  AMENDED_BY: { color: 'text-amber-400', bg: 'bg-amber-500/15 border-amber-500/25', label: 'Diamandemen oleh' },
  REVOKES: { color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/25', label: 'Mencabut' },
  REVOKED_BY: { color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/25', label: 'Dicabut oleh' },
  REPLACES: { color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/25', label: 'Menggantikan' },
  REPLACED_BY: { color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/25', label: 'Digantikan oleh' },
  IMPLEMENTS: { color: 'text-emerald-400', bg: 'bg-emerald-500/15 border-emerald-500/25', label: 'Melaksanakan' },
  IMPLEMENTED_BY: { color: 'text-emerald-400', bg: 'bg-emerald-500/15 border-emerald-500/25', label: 'Dilaksanakan oleh' },
};

const DEFAULT_EDGE_CONFIG = { color: 'text-white/40', bg: 'bg-white/[0.06] border-white/[0.1]', label: 'Terkait' };

function getDotColor(edgeType: string): string {
  switch (edgeType) {
    case 'AMENDS':
    case 'AMENDED_BY':
      return 'bg-amber-500';
    case 'REVOKES':
    case 'REVOKED_BY':
      return 'bg-red-500';
    case 'REPLACES':
    case 'REPLACED_BY':
      return 'bg-blue-500';
    case 'IMPLEMENTS':
    case 'IMPLEMENTED_BY':
      return 'bg-emerald-500';
    default:
      return 'bg-white/30';
  }
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07 } },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
};

export default function AmendmentTimeline({ timeline, currentRegulationId }: Readonly<AmendmentTimelineProps>) {
  const sorted = [...timeline.entries].sort((a: AmendmentTimelineEntry, b: AmendmentTimelineEntry) => a.year - b.year);

  if (sorted.length === 0) {
    return (
      <div className="py-6 text-center text-white/30 text-sm">
        Tidak ada riwayat amandemen untuk regulasi ini
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-2.5 top-2 bottom-2 w-px bg-white/[0.08]" />

      <motion.ul
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="space-y-5"
      >
        {sorted.map((entry: AmendmentTimelineEntry, i: number) => {
          const config = EDGE_TYPE_CONFIG[entry.edge_type] ?? DEFAULT_EDGE_CONFIG;
          const isCurrentRegulation = entry.regulation_id === currentRegulationId;
          const dotColor = getDotColor(entry.edge_type);

          return (
            <motion.li key={`${entry.regulation_id}-${i}`} variants={itemVariants}>
              <div className="flex items-start gap-3">
                {/* Dot */}
                <div
                  className={`flex-shrink-0 mt-1.5 w-2.5 h-2.5 rounded-full ${dotColor} -ml-6 border-2 border-[#0A0A0F]`}
                />

                {/* Content */}
                <div
                  className={`flex-1 min-w-0 p-3 rounded-xl border ${
                    isCurrentRegulation
                      ? 'border-[#AAFF00]/30 bg-[#AAFF00]/[0.04]'
                      : 'border-white/[0.06] bg-white/[0.02]'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`text-[10px] font-medium px-2 py-0.5 rounded-md border ${config.bg} ${config.color}`}
                    >
                      {config.label}
                    </span>
                    <span className="text-[11px] text-white/30">{entry.year}</span>
                  </div>
                  <Link
                    href={`/regulations/${entry.regulation_id}`}
                    className={`text-sm font-medium leading-snug hover:underline ${
                      isCurrentRegulation
                        ? 'text-[#AAFF00]'
                        : 'text-white/80 hover:text-white'
                    }`}
                  >
                    {entry.regulation_title || `Reg. No. ${entry.number} (${entry.year})`}
                  </Link>
                </div>
              </div>
            </motion.li>
          );
        })}
      </motion.ul>
    </div>
  );
}
