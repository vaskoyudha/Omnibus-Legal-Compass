'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import SearchBar from '@/components/SearchBar';
import AnswerCard from '@/components/AnswerCard';
import StreamingAnswerCard from '@/components/StreamingAnswerCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import DarkModeToggle from '@/components/DarkModeToggle';
import { 
  askQuestion, 
  askQuestionStream, 
  AskResponse, 
  CitationInfo, 
  ConfidenceScore, 
  ValidationResult 
} from '@/lib/api';

export default function Home() {
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Streaming state
  const [useStreaming, setUseStreaming] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<CitationInfo[]>([]);
  const [streamingConfidence, setStreamingConfidence] = useState<ConfidenceScore | null>(null);
  const [streamingValidation, setStreamingValidation] = useState<ValidationResult | null>(null);
  const [streamingProcessingTime, setStreamingProcessingTime] = useState(0);

  const handleSearch = useCallback(async (query: string) => {
    setError(null);
    setResponse(null);
    
    // Reset streaming state
    setStreamingAnswer('');
    setStreamingCitations([]);
    setStreamingConfidence(null);
    setStreamingValidation(null);
    setStreamingProcessingTime(0);
    
    if (useStreaming) {
      // Use streaming API
      setIsStreaming(true);
      setIsLoading(false);
      
      try {
        await askQuestionStream(query, {
          onMetadata: (metadata) => {
            setStreamingCitations(metadata.citations);
            setStreamingConfidence(metadata.confidence_score);
          },
          onChunk: (text) => {
            setStreamingAnswer(prev => prev + text);
          },
          onDone: (data) => {
            setStreamingValidation(data.validation);
            setStreamingProcessingTime(data.processing_time_ms);
            setIsStreaming(false);
          },
          onError: (err) => {
            setError(err.message);
            setIsStreaming(false);
          },
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Terjadi kesalahan saat memproses pertanyaan Anda');
        setIsStreaming(false);
      }
    } else {
      // Use regular API
      setIsLoading(true);
      
      try {
        const result = await askQuestion(query);
        setResponse(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Terjadi kesalahan saat memproses pertanyaan Anda');
      } finally {
        setIsLoading(false);
      }
    }
  }, [useStreaming]);

  const showStreamingResult = useStreaming && (isStreaming || streamingAnswer);
  const showRegularResult = !useStreaming && response && !isLoading;

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-950">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-800 to-blue-900 dark:from-blue-950 dark:to-indigo-950 text-white">
        {/* Navigation */}
        <nav className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between border-b border-blue-700 dark:border-blue-800">
          <Link href="/" className="font-semibold text-lg hover:text-blue-200 transition-colors">
            Omnibus Legal Compass
          </Link>
          <div className="flex items-center gap-3">
            <Link 
              href="/" 
              className="text-sm px-3 py-1.5 bg-blue-700 dark:bg-blue-800 rounded-lg hover:bg-blue-600 dark:hover:bg-blue-700 transition-colors"
            >
              Tanya Jawab
            </Link>
            <Link 
              href="/compliance" 
              className="text-sm px-3 py-1.5 bg-blue-700/50 dark:bg-blue-800/50 rounded-lg hover:bg-blue-600 dark:hover:bg-blue-700 transition-colors"
            >
              Pemeriksa Kepatuhan
            </Link>
            <Link 
              href="/guidance" 
              className="text-sm px-3 py-1.5 bg-blue-700/50 dark:bg-blue-800/50 rounded-lg hover:bg-blue-600 dark:hover:bg-blue-700 transition-colors"
            >
              Panduan Usaha
            </Link>
            <div className="ml-2 border-l border-blue-600 dark:border-blue-700 pl-3">
              <DarkModeToggle />
            </div>
          </div>
        </nav>
        
        {/* Hero */}
        <div className="py-10 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl font-bold mb-2">Tanya Jawab Hukum</h1>
            <p className="text-blue-200 dark:text-blue-300 text-lg">Sistem Tanya Jawab Hukum Indonesia</p>
            <p className="text-blue-300 dark:text-blue-400 text-sm mt-2">
              Didukung oleh AI untuk membantu Anda memahami peraturan perundang-undangan
            </p>
          </div>
        </div>
      </div>
      
      {/* Search Section */}
      <div className="max-w-4xl mx-auto px-4 -mt-6">
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 border border-transparent dark:border-slate-700">
          <SearchBar onSearch={handleSearch} isLoading={isLoading || isStreaming} />
          
          {/* Options Row */}
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-slate-400 mb-2">Contoh pertanyaan:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  'Apa syarat pendirian PT?',
                  'Bagaimana ketentuan PHK karyawan?',
                  'Apa itu RUPS?',
                ].map((question) => (
                  <button
                    key={question}
                    onClick={() => handleSearch(question)}
                    disabled={isLoading || isStreaming}
                    className="text-sm px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Streaming Toggle */}
            <div className="flex items-center gap-2 no-print">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={useStreaming}
                  onChange={(e) => setUseStreaming(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 dark:bg-slate-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
              <span className="text-xs text-gray-500 dark:text-slate-400">
                Streaming {useStreaming ? 'On' : 'Off'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Results Section */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {isLoading && <LoadingSpinner />}
        
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-6 py-4 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="font-medium">Terjadi Kesalahan</h3>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Streaming Result */}
        {showStreamingResult && (
          <StreamingAnswerCard
            answer={streamingAnswer}
            citations={streamingCitations}
            confidenceScore={streamingConfidence}
            validation={streamingValidation}
            processingTimeMs={streamingProcessingTime}
            isStreaming={isStreaming}
          />
        )}
        
        {/* Regular Result */}
        {showRegularResult && <AnswerCard response={response} />}
        
        {/* Empty State */}
        {!response && !isLoading && !error && !showStreamingResult && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-slate-100 mb-2">
              Tanyakan Pertanyaan Hukum Anda
            </h3>
            <p className="text-gray-500 dark:text-slate-400 max-w-md mx-auto">
              Ketik pertanyaan tentang peraturan perundang-undangan Indonesia, 
              dan sistem akan mencari jawaban dari dokumen hukum yang relevan.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-slate-800 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-gray-500 dark:text-slate-400">
            Omnibus Legal Compass - Sistem RAG untuk Dokumen Hukum Indonesia
          </p>
          <p className="text-center text-xs text-gray-400 dark:text-slate-500 mt-1">
            Jawaban yang diberikan bersifat informatif dan bukan merupakan nasihat hukum resmi
          </p>
        </div>
      </footer>
    </main>
  );
}
