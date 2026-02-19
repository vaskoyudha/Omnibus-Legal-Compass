'use client';

import type { ChapterDetail } from '@/lib/api';

export interface ArticleRendererProps {
  chapter: Readonly<ChapterDetail>;
  isActive?: boolean;
}

export default function ArticleRenderer({ chapter, isActive }: Readonly<ArticleRendererProps>) {
  return (
    <section
      id={`chapter-${chapter.id}`}
      className={`mb-12 transition-opacity duration-300 ${isActive ? 'opacity-100' : 'opacity-80'}`}
    >
      {/* Chapter heading */}
      <h2 className="text-lg font-bold text-white/90 mb-6 flex items-center gap-3">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-[#AAFF00]/10 text-[#AAFF00] text-sm font-bold flex-shrink-0">
          {chapter.number}
        </span>
        <span>
          BAB {chapter.number}
          {chapter.title ? ` — ${chapter.title}` : ''}
        </span>
      </h2>

      {/* Articles */}
      <div className="space-y-8">
        {chapter.articles.map((article) => (
          <article
            key={article.id}
            id={`pasal-${article.number}`}
            className="scroll-mt-24"
          >
            {/* Article number */}
            <h3 className="text-sm font-semibold text-[#AAFF00]/80 mb-3 flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-[#AAFF00]/40 inline-block" aria-hidden="true" />
              Pasal {article.number}
            </h3>

            {/* Full text */}
            <div className="pl-3 border-l border-white/[0.06]">
              <pre className="font-mono text-sm text-white/70 whitespace-pre-wrap leading-relaxed break-words">
                {article.full_text}
              </pre>

              {/* Content summary */}
              {article.content_summary && (
                <p className="mt-3 text-xs text-white/40 italic leading-relaxed">
                  {article.content_summary}
                </p>
              )}

              {/* Cross-references */}
              {article.cross_references.length > 0 && (
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-white/30 font-medium">Lihat juga:</span>
                  {article.cross_references.map((ref, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-[11px] text-white/50"
                    >
                      {ref}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </article>
        ))}
      </div>

      {/* Separator */}
      <div className="border-t border-white/[0.04] mt-8" aria-hidden="true" />
    </section>
  );
}
