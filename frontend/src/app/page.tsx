'use client';

import { useState } from 'react';
import Link from 'next/link';
import SearchBar from '@/components/SearchBar';
import AnswerCard from '@/components/AnswerCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { askQuestion, AskResponse } from '@/lib/api';

export default function Home() {
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setError(null);
    setResponse(null);
    
    try {
      const result = await askQuestion(query);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan saat memproses pertanyaan Anda');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-800 to-blue-900 text-white">
        {/* Navigation */}
        <nav className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between border-b border-blue-700">
          <Link href="/" className="font-semibold text-lg hover:text-blue-200 transition-colors">
            Omnibus Legal Compass
          </Link>
          <div className="flex gap-4">
            <Link 
              href="/" 
              className="text-sm px-3 py-1.5 bg-blue-700 rounded-lg hover:bg-blue-600 transition-colors"
            >
              Tanya Jawab
            </Link>
            <Link 
              href="/compliance" 
              className="text-sm px-3 py-1.5 bg-blue-700/50 rounded-lg hover:bg-blue-600 transition-colors"
            >
              Pemeriksa Kepatuhan
            </Link>
          </div>
        </nav>
        
        {/* Hero */}
        <div className="py-10 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl font-bold mb-2">Tanya Jawab Hukum</h1>
            <p className="text-blue-200 text-lg">Sistem Tanya Jawab Hukum Indonesia</p>
            <p className="text-blue-300 text-sm mt-2">
              Didukung oleh AI untuk membantu Anda memahami peraturan perundang-undangan
            </p>
          </div>
        </div>
      </div>
      
      {/* Search Section */}
      <div className="max-w-4xl mx-auto px-4 -mt-6">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
          
          {/* Example Questions */}
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-sm text-gray-500 mb-2">Contoh pertanyaan:</p>
            <div className="flex flex-wrap gap-2">
              {[
                'Apa syarat pendirian PT?',
                'Bagaimana ketentuan PHK karyawan?',
                'Apa itu RUPS?',
              ].map((question) => (
                <button
                  key={question}
                  onClick={() => handleSearch(question)}
                  disabled={isLoading}
                  className="text-sm px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Results Section */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {isLoading && <LoadingSpinner />}
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg">
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
        
        {response && !isLoading && <AnswerCard response={response} />}
        
        {/* Empty State */}
        {!response && !isLoading && !error && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Tanyakan Pertanyaan Hukum Anda
            </h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Ketik pertanyaan tentang peraturan perundang-undangan Indonesia, 
              dan sistem akan mencari jawaban dari dokumen hukum yang relevan.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-gray-500">
            Omnibus Legal Compass - Sistem RAG untuk Dokumen Hukum Indonesia
          </p>
          <p className="text-center text-xs text-gray-400 mt-1">
            Jawaban yang diberikan bersifat informatif dan bukan merupakan nasihat hukum resmi
          </p>
        </div>
      </footer>
    </main>
  );
}
