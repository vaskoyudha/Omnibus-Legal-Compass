'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import { CitationInfo, ConfidenceScore, ValidationResult } from '@/lib/api';
import CitationList from './CitationList';

interface StreamingAnswerCardProps {
  answer: string;
  citations: CitationInfo[];
  confidenceScore: ConfidenceScore | null;
  validation: ValidationResult | null;
  processingTimeMs: number;
  isStreaming: boolean;
}

export default function StreamingAnswerCard({ 
  answer, 
  citations, 
  confidenceScore, 
  validation, 
  processingTimeMs,
  isStreaming 
}: StreamingAnswerCardProps) {
  const [copied, setCopied] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);
  const answerRef = useRef<HTMLDivElement>(null);
  
  // Get numeric confidence from confidence_score if available
  const numericConfidence = confidenceScore?.numeric ?? 0;
  
  // Convert processing_time_ms to seconds
  const processingTimeSec = processingTimeMs / 1000;

  // Auto-scroll as content streams in
  useEffect(() => {
    if (isStreaming && answerRef.current) {
      answerRef.current.scrollTop = answerRef.current.scrollHeight;
    }
  }, [answer, isStreaming]);
  
  // Copy answer to clipboard
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [answer]);
  
  // Share functionality
  const handleShare = useCallback(async () => {
    const shareData = {
      title: 'Jawaban Hukum - Omnibus Legal Compass',
      text: answer.slice(0, 300) + '...',
      url: window.location.href,
    };
    
    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.log('Share cancelled');
      }
    } else {
      await navigator.clipboard.writeText(window.location.href);
      alert('Link disalin ke clipboard');
    }
  }, [answer]);
  
  // Print functionality
  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const getConfidenceConfig = (confidence: number) => {
    if (confidence >= 0.65) return {
      color: 'text-emerald-700',
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      label: 'Tinggi',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      ),
    };
    if (confidence >= 0.4) return {
      color: 'text-amber-700',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      label: 'Sedang',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      ),
    };
    return {
      color: 'text-red-700',
      bg: 'bg-red-50',
      border: 'border-red-200',
      label: 'Rendah',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      ),
    };
  };

  const getHallucinationConfig = (risk: string) => {
    if (risk === 'low') return { color: 'text-emerald-600', bg: 'bg-emerald-100', label: 'Rendah' };
    if (risk === 'medium') return { color: 'text-amber-600', bg: 'bg-amber-100', label: 'Sedang' };
    return { color: 'text-red-600', bg: 'bg-red-100', label: 'Tinggi' };
  };

  const confidenceConfig = getConfidenceConfig(numericConfidence);
  const hallucinationConfig = validation 
    ? getHallucinationConfig(validation.hallucination_risk)
    : null;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8 print:mt-0 print:max-w-none">
      {/* Main Answer Card */}
      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden print:shadow-none print:border-slate-300">
        
        {/* Header with Confidence Badge & Actions */}
        <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/10 rounded-lg">
                {isStreaming ? (
                  <svg className="w-6 h-6 text-white animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                )}
              </div>
              <div>
                <h2 className="text-white font-semibold text-lg flex items-center gap-2">
                  Jawaban Legal
                  {isStreaming && (
                    <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full animate-pulse">
                      Streaming...
                    </span>
                  )}
                </h2>
                {processingTimeSec > 0 && !isStreaming && (
                  <p className="text-blue-100 text-sm">Diproses dalam {processingTimeSec.toFixed(2)} detik</p>
                )}
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center gap-2 no-print">
              <button
                onClick={handleCopy}
                disabled={isStreaming}
                className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                title="Salin jawaban"
              >
                {copied ? (
                  <svg className="w-5 h-5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
              <button
                onClick={handleShare}
                disabled={isStreaming}
                className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                title="Bagikan"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
              </button>
              <button
                onClick={handlePrint}
                disabled={isStreaming}
                className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
                title="Cetak"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Confidence Summary Bar */}
        {confidenceScore && (
          <div className={`px-6 py-3 border-b ${confidenceConfig.bg} ${confidenceConfig.border} flex items-center justify-between`}>
            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 ${confidenceConfig.color} font-medium`}>
                {confidenceConfig.icon}
                <span>Keyakinan {confidenceConfig.label}</span>
                <span className="font-bold">{Math.round(numericConfidence * 100)}%</span>
              </div>
              
              {validation && (
                <div className="flex items-center gap-2 text-slate-600 text-sm border-l border-slate-300 pl-4">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>{Math.round(validation.citation_coverage * 100)}% sumber dikutip</span>
                </div>
              )}
              
              {hallucinationConfig && (
                <div className={`flex items-center gap-1.5 text-sm ${hallucinationConfig.color}`}>
                  <span className={`w-2 h-2 rounded-full ${hallucinationConfig.bg}`}></span>
                  <span>Risiko halusinasi: {hallucinationConfig.label}</span>
                </div>
              )}
            </div>
            
            <button
              onClick={() => setShowMetrics(!showMetrics)}
              className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1 no-print"
            >
              {showMetrics ? 'Sembunyikan' : 'Detail'}
              <svg className={`w-4 h-4 transition-transform ${showMetrics ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        )}
        
        {/* Expandable Metrics Panel */}
        {showMetrics && confidenceScore && (
          <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">Skor Tertinggi</div>
              <div className="font-bold text-lg text-slate-800">
                {(confidenceScore.top_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">Rata-rata Skor</div>
              <div className="font-bold text-lg text-slate-800">
                {(confidenceScore.avg_score * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">Jumlah Sumber</div>
              <div className="font-bold text-lg text-slate-800">
                {citations?.length || 0}
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200">
              <div className="text-slate-500 text-xs uppercase tracking-wide mb-1">Waktu Proses</div>
              <div className="font-bold text-lg text-slate-800">
                {processingTimeSec.toFixed(2)}s
              </div>
            </div>
          </div>
        )}

        {/* Validation Warnings */}
        {validation && validation.warnings.length > 0 && (
          <div className="mx-6 mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <p className="font-medium text-amber-800 mb-1">Peringatan Validasi</p>
                <ul className="text-sm text-amber-700 space-y-1">
                  {validation.warnings.map((warning, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-amber-500">•</span>
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Answer Content */}
        <div className="p-6" ref={answerRef}>
          <div className="prose prose-slate prose-lg max-w-none 
            prose-p:text-slate-700 prose-p:leading-relaxed prose-p:mb-4
            prose-strong:text-slate-800 prose-strong:font-semibold
            prose-ul:my-4 prose-ul:space-y-2
            prose-ol:my-4 prose-ol:space-y-2
            prose-li:text-slate-700
            prose-headings:text-slate-800 prose-headings:font-semibold
            prose-h2:text-xl prose-h2:mt-6 prose-h2:mb-3
            prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2
            prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
            prose-code:bg-slate-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
            prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:rounded-lg prose-pre:overflow-x-auto">
            <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
              {answer || (isStreaming ? '...' : '')}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-5 bg-blue-500 animate-pulse ml-1" />
            )}
          </div>
        </div>

        {/* Citations Section */}
        {citations.length > 0 && (
          <div className="border-t border-slate-200">
            <CitationList citations={citations} />
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="mt-6 p-5 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl print:bg-amber-50">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-amber-100 rounded-lg flex-shrink-0">
            <svg className="w-5 h-5 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <p className="font-medium text-amber-900 mb-1">Pemberitahuan Penting</p>
            <p className="text-sm text-amber-800 leading-relaxed">
              Informasi ini bersifat informatif dan bukan merupakan nasihat hukum resmi. 
              Untuk keperluan hukum yang mengikat, silakan konsultasikan dengan profesional hukum yang berkualifikasi.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
