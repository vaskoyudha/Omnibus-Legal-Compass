'use client';

import { CitationInfo, mapCitation } from '@/lib/api';

interface CitationListProps {
  citations: CitationInfo[];
}

export default function CitationList({ citations }: CitationListProps) {
  if (!citations || citations.length === 0) {
    return null;
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'UU': 'bg-blue-100 text-blue-800 border-blue-200',
      'PP': 'bg-green-100 text-green-800 border-green-200',
      'Perpres': 'bg-purple-100 text-purple-800 border-purple-200',
      'Permen': 'bg-orange-100 text-orange-800 border-orange-200',
      'Perda': 'bg-teal-100 text-teal-800 border-teal-200',
    };
    return colors[type] || 'bg-slate-100 text-slate-800 border-slate-200';
  };

  const formatScore = (score: number) => {
    if (isNaN(score) || score === undefined || score === null) return 0;
    return Math.round(score * 100);
  };

  return (
    <div className="mt-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Sumber Referensi ({citations.length})
      </h3>
      <div className="space-y-3">
        {citations.map((citationInfo, index) => {
          const citation = mapCitation(citationInfo);
          return (
            <div
              key={index}
              className="p-4 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all duration-200"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getTypeColor(citation.document_type)}`}>
                      {citation.document_type}
                    </span>
                    <span className="text-xs text-slate-400">
                      Relevansi: {formatScore(citation.relevance_score)}%
                    </span>
                  </div>
                  <h4 className="font-medium text-slate-800 text-sm">
                    {citation.document_title}
                  </h4>
                  {citation.pasal && (
                    <p className="text-sm text-blue-600 font-medium mt-1">
                      {citation.pasal}
                    </p>
                  )}
                  {citation.content_snippet && (
                    <p className="text-sm text-slate-600 mt-2 line-clamp-3">
                      {citation.content_snippet}
                    </p>
                  )}
                </div>
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-700 font-bold text-sm">
                    {index + 1}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
