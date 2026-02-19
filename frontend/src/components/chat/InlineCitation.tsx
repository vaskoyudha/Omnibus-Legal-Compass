'use client';

import { motion } from 'framer-motion';

interface InlineCitationProps {
  readonly number: number;           // 1-based display number
  readonly citationIndex: number;    // 0-based index into citations array
  readonly onClick?: (index: number) => void;
  readonly isHighlighted?: boolean;
  readonly title?: string;           // tooltip text
}

export default function InlineCitation({
  number,
  citationIndex,
  onClick,
  isHighlighted = false,
  title,
}: InlineCitationProps) {
  const handleClick = () => {
    onClick?.(citationIndex);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.(citationIndex);
    }
  };

  return (
    <motion.sup
      role="button"
      tabIndex={0}
      aria-label={`Kutipan ${number}`}
      title={title}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={[
        'inline-flex items-center justify-center',
        'text-[11px] font-semibold leading-none',
        'cursor-pointer select-none',
        'rounded px-1 py-0.5 mx-0.5',
        'transition-all duration-150',
        'text-[#AAFF00]',
        'hover:underline hover:brightness-125',
        'focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/50',
        isHighlighted
          ? 'bg-[#AAFF00]/20 shadow-[0_0_6px_rgba(170,255,0,0.3)]'
          : 'bg-[#AAFF00]/10',
      ].join(' ')}
      whileTap={{ scale: 0.92 }}
      data-citation-index={citationIndex}
    >
      [{number}]
    </motion.sup>
  );
}
