'use client';

import { useState } from 'react';
import type { ChapterDetail } from '@/lib/api';

export interface TableOfContentsProps {
  chapters: Readonly<ChapterDetail[]>;
  activeChapterId?: string;
  activeArticleId?: string;
  onChapterClick: (id: string) => void;
  onArticleClick: (id: string) => void;
}

export default function TableOfContents({
  chapters,
  activeChapterId,
  activeArticleId,
  onChapterClick,
  onArticleClick,
}: Readonly<TableOfContentsProps>) {
  // Start with all chapters collapsed; expand active one
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    chapters.forEach((ch) => {
      init[ch.id] = ch.id === activeChapterId;
    });
    return init;
  });

  const toggleChapter = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
    onChapterClick(id);
  };

  if (chapters.length === 0) return null;

  return (
    <nav
      aria-label="Daftar Isi"
      className="sticky top-4 max-h-[calc(100vh-6rem)] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
    >
      <p className="text-[10px] uppercase tracking-widest text-white/30 font-semibold mb-3 px-1">
        Daftar Isi
      </p>
      <ul className="space-y-0.5">
        {chapters.map((chapter) => {
          const isActiveChapter = chapter.id === activeChapterId;
          const isOpen = expanded[chapter.id] ?? false;

          return (
            <li key={chapter.id}>
              {/* Chapter heading */}
              <button
                onClick={() => toggleChapter(chapter.id)}
                className={`w-full text-left flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActiveChapter
                    ? 'text-[#AAFF00] border-l-2 border-[#AAFF00] pl-3 bg-[#AAFF00]/5'
                    : 'text-white/70 hover:text-white/90 hover:bg-white/[0.04]'
                }`}
                aria-expanded={isOpen}
              >
                <svg
                  className={`w-3 h-3 flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <span className="truncate">
                  Bab {chapter.number}
                  {chapter.title ? ` — ${chapter.title}` : ''}
                </span>
              </button>

              {/* Articles */}
              {isOpen && chapter.articles.length > 0 && (
                <ul className="mt-0.5 ml-3 space-y-0.5 border-l border-white/[0.06] pl-2">
                  {chapter.articles.map((article) => {
                    const isActiveArticle = article.id === activeArticleId;
                    return (
                      <li key={article.id}>
                        <button
                          onClick={() => onArticleClick(article.id)}
                          className={`w-full text-left px-2 py-1 rounded text-[11px] transition-colors truncate ${
                            isActiveArticle
                              ? 'text-[#AAFF00] font-medium border-l-2 border-[#AAFF00] pl-3 bg-[#AAFF00]/5'
                              : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
                          }`}
                        >
                          Pasal {article.number}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
