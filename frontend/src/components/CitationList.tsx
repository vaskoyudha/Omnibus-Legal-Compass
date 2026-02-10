'use client';

import { useState } from 'react';
import { CitationInfo, mapCitation } from '@/lib/api';

interface CitationListProps {
  citations: CitationInfo[];
}

export default function CitationList({ citations }: CitationListProps) {
  const [expandedCitations, setExpandedCitations] = useState<Set<number>>(new Set());
  
  if (!citations || citations.length === 0) {
    return null;
  }

  const toggleExpand = (index: number) => {
    setExpandedCitations(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedCitations(new Set(citations.map((_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedCitations(new Set());
  };

  const getTypeConfig = (type: string) => {
    const configs: Record<string, { bg: string; text: string; border: string; icon: string }> = {
      'UU': { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-200', icon: '📜' },
      'PP': { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-200', icon: '📋' },
      'Perpres': { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-200', icon: '🏛️' },
      'Permen': { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-200', icon: '📑' },
      'Perda': { bg: 'bg-teal-100', text: 'text-teal-800', border: 'border-teal-200', icon: '🏢' },
    };
    return configs[type] || { bg: 'bg-slate-100', text: 'text-slate-800', border: 'border-slate-200', icon: '📄' };
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-emerald-600 bg-emerald-50';
    if (score >= 0.4) return 'text-amber-600 bg-amber-50';
    return 'text-slate-500 bg-slate-50';
  };

  const formatScore = (score: number) => {
    if (isNaN(score) || score === undefined || score === null) return 0;
    return Math.round(score * 100);
  };

  return (
    <div className="p-6">
      {/* Header with expand/collapse controls */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Sumber Referensi
          <span className="ml-1 px-2 py-0.5 text-sm bg-blue-100 text-blue-700 rounded-full font-medium">
            {citations.length}
          </span>
        </h3>
        
        {/* Expand/Collapse buttons */}
        <div className="flex items-center gap-2 text-sm no-print">
          <button
            onClick={expandAll}
            className="text-slate-500 hover:text-blue-600 flex items-center gap-1 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            Buka Semua
          </button>
          <span className="text-slate-300">|</span>
          <button
            onClick={collapseAll}
            className="text-slate-500 hover:text-blue-600 flex items-center gap-1 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
            Tutup Semua
          </button>
        </div>
      </div>
      
      {/* Citation Cards */}
      <div className="space-y-3">
        {citations.map((citationInfo, index) => {
          const citation = mapCitation(citationInfo);
          const typeConfig = getTypeConfig(citation.document_type);
          const isExpanded = expandedCitations.has(index);
          const scorePercent = formatScore(citation.relevance_score);
          
          return (
            <div
              key={index}
              className={`bg-white border rounded-xl overflow-hidden transition-all duration-200 ${
                isExpanded 
                  ? 'border-blue-300 shadow-md' 
                  : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
              }`}
            >
              {/* Citation Header - Always Visible */}
              <button
                onClick={() => toggleExpand(index)}
                className="w-full p-4 flex items-center gap-4 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset"
              >
                {/* Number Badge */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                  isExpanded ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700'
                }`}>
                  {index + 1}
                </div>
                
                {/* Main Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-md ${typeConfig.bg} ${typeConfig.text}`}>
                      {typeConfig.icon} {citation.document_type}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-md ${getScoreColor(citation.relevance_score)}`}>
                      {scorePercent}% relevan
                    </span>
                  </div>
                  <h4 className="font-medium text-slate-800 text-sm truncate pr-4">
                    {citation.document_title}
                  </h4>
                  {citation.pasal && (
                    <p className="text-sm text-blue-600 font-medium mt-0.5">
                      {citation.pasal}
                    </p>
                  )}
                </div>
                
                {/* Expand Icon */}
                <div className="flex-shrink-0">
                  <svg 
                    className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              
              {/* Expandable Content */}
              {isExpanded && citation.content_snippet && (
                <div className="px-4 pb-4 border-t border-slate-100">
                  <div className="pt-4 pl-14">
                    <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                      Kutipan Teks
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                        {citation.content_snippet}
                      </p>
                    </div>
                    
                    {/* Relevance Bar */}
                    <div className="mt-3 flex items-center gap-3">
                      <span className="text-xs text-slate-500">Relevansi:</span>
                      <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            scorePercent >= 70 ? 'bg-emerald-500' :
                            scorePercent >= 40 ? 'bg-amber-500' : 'bg-slate-400'
                          }`}
                          style={{ width: `${scorePercent}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-slate-600">{scorePercent}%</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
