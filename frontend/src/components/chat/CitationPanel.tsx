'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CitationInfo, mapCitation } from '@/lib/api';

interface CitationPanelProps {
  readonly citations: CitationInfo[];
  readonly activeCitationIndex: number | null;
  readonly onCitationClick: (index: number) => void;
}

// Document type → style config (mirrors CitationList but tuned for compact panel)
const TYPE_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  UU:      { bg: 'bg-blue-500/15',    text: 'text-blue-300',    label: 'UU' },
  PP:      { bg: 'bg-emerald-500/15', text: 'text-emerald-300', label: 'PP' },
  Perpres: { bg: 'bg-purple-500/15',  text: 'text-purple-300',  label: 'Perpres' },
  Permen:  { bg: 'bg-orange-500/15',  text: 'text-orange-300',  label: 'Permen' },
  Perda:   { bg: 'bg-teal-500/15',    text: 'text-teal-300',    label: 'Perda' },
};

function getTypeConfig(type: string) {
  return TYPE_CONFIG[type] ?? { bg: 'bg-white/[0.06]', text: 'text-white/50', label: type || 'Dok' };
}

function getScoreColor(score: number) {
  if (score >= 0.7) return 'text-emerald-400';
  if (score >= 0.4) return 'text-amber-400';
  return 'text-white/40';
}

// ─── Individual card ──────────────────────────────────────────────────────────
interface CitationCardProps {
  citationInfo: CitationInfo;
  index: number;
  isActive: boolean;
  onClick: (index: number) => void;
}

function CitationCard({ citationInfo, index, isActive, onClick }: CitationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const mapped = mapCitation(citationInfo);
  const typeConfig = getTypeConfig(mapped.document_type);
  const scorePercent = Math.round((mapped.relevance_score || 0) * 100);

  const handleCardClick = () => {
    onClick(index);
    setIsExpanded((prev) => !prev);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className={[
        'rounded-xl border overflow-hidden cursor-pointer transition-colors duration-150',
        isActive
          ? 'border-[#AAFF00]/30 bg-[#AAFF00]/[0.04]'
          : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]',
      ].join(' ')}
      onClick={handleCardClick}
    >
      {/* Card header */}
      <div className="flex items-start gap-2.5 p-3">
        {/* Number badge */}
        <div
          className={[
            'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold mt-0.5',
            isActive
              ? 'bg-[#AAFF00] text-[#0A0A0F]'
              : 'bg-white/[0.08] text-white/50',
          ].join(' ')}
        >
          {index + 1}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          {/* Badges row */}
          <div className="flex items-center gap-1.5 flex-wrap mb-1">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeConfig.bg} ${typeConfig.text}`}>
              {typeConfig.label}
            </span>
            <span className={`text-[10px] font-medium ${getScoreColor(mapped.relevance_score)}`}>
              {scorePercent}%
            </span>
          </div>

          {/* Title */}
          <p className="text-[12px] text-white/80 font-medium leading-snug truncate">
            {mapped.document_title}
          </p>

          {/* Pasal */}
          {mapped.pasal && (
            <p className="text-[11px] text-[#AAFF00]/70 mt-0.5 truncate">
              {mapped.pasal}
            </p>
          )}
        </div>

        {/* Chevron */}
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.18 }}
          className="flex-shrink-0 mt-1 text-white/25"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </motion.div>
      </div>

      {/* Expandable snippet */}
      <AnimatePresence initial={false}>
        {isExpanded && mapped.content_snippet && (
          <motion.div
            key="snippet"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-1 border-t border-white/[0.05]">
              {/* Relevance bar */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] text-white/30">Relevansi</span>
                <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                  <div
                    className={[
                      'h-full rounded-full transition-all duration-500',
                      scorePercent >= 70 ? 'bg-emerald-500' : scorePercent >= 40 ? 'bg-amber-500' : 'bg-white/20',
                    ].join(' ')}
                    style={{ width: `${scorePercent}%` }}
                  />
                </div>
                <span className="text-[10px] text-white/40 font-medium">{scorePercent}%</span>
              </div>

              {/* Snippet text */}
              <p className="text-[11px] text-white/50 leading-relaxed whitespace-pre-wrap line-clamp-6">
                {mapped.content_snippet}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────
export default function CitationPanel({ citations, activeCitationIndex, onCitationClick }: CitationPanelProps) {
  const isEmpty = citations.length === 0;

  return (
    <aside className="hidden lg:flex lg:flex-col w-80 flex-shrink-0 sticky top-0 h-screen overflow-y-auto bg-[#0A0A0F] border-l border-white/[0.06] custom-scrollbar">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/[0.06] flex-shrink-0 bg-[#0A0A0F] sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#AAFF00]">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
          <span className="text-[13px] font-semibold text-white/80">Sumber Referensi</span>
        </div>
        {!isEmpty && (
          <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-full bg-[#AAFF00]/10 text-[#AAFF00]">
            {citations.length}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 px-3 py-3">
        {isEmpty ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-center px-4">
            <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-3">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/20">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
              </svg>
            </div>
            <p className="text-[12px] text-white/25 leading-relaxed">
              Tidak ada sumber untuk percakapan ini
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {citations.map((cit, idx) => (
                <CitationCard
                  key={`${cit.citation_id ?? idx}-${idx}`}
                  citationInfo={cit}
                  index={idx}
                  isActive={idx === activeCitationIndex}
                  onClick={onCitationClick}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </aside>
  );
}
