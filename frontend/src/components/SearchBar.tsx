'use client';

import { useState, FormEvent, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export default function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  }, [query]);

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex items-start gap-3">
        {/* AI Avatar */}
        <div className="flex-shrink-0 mt-1">
          <motion.div
            className="w-10 h-10 rounded-xl flex items-center justify-center relative"
            style={{
              background: 'linear-gradient(135deg, rgba(170, 255, 0, 0.2), rgba(170, 255, 0, 0.05))',
              border: '1px solid rgba(170, 255, 0, 0.3)',
            }}
            animate={isFocused ? {
              boxShadow: ['0 0 12px rgba(170,255,0,0.2)', '0 0 20px rgba(170,255,0,0.35)', '0 0 12px rgba(170,255,0,0.2)'],
            } : {}}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <svg className="w-5 h-5 text-[#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
            </svg>
            {/* Pulse indicator */}
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#AAFF00] animate-pulse-online" />
          </motion.div>
        </div>

        {/* Input Area */}
        <div className="flex-1 relative">
          <div
            className="relative rounded-2xl transition-all duration-300"
            style={{
              background: isFocused
                ? 'rgba(170, 255, 0, 0.03)'
                : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${isFocused ? 'rgba(170, 255, 0, 0.3)' : 'rgba(255, 255, 255, 0.08)'}`,
              boxShadow: isFocused
                ? '0 0 20px rgba(170, 255, 0, 0.08), inset 0 1px 0 rgba(170, 255, 0, 0.1)'
                : 'none',
            }}
          >
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder="Tanyakan seputar hukum Indonesia..."
              rows={1}
              className="w-full px-5 py-4 pr-14 text-[15px] leading-relaxed bg-transparent text-white placeholder-gray-500 outline-none resize-none"
              style={{ minHeight: '56px', maxHeight: '120px' }}
              disabled={isLoading}
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="absolute right-3 bottom-3 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed group"
              style={{
                background: query.trim() && !isLoading
                  ? 'linear-gradient(135deg, #AAFF00, #88CC00)'
                  : 'rgba(255, 255, 255, 0.06)',
              }}
            >
              {isLoading ? (
                <svg className="animate-spin h-4.5 w-4.5 text-[#0A0A0F]" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg
                  className={`w-[18px] h-[18px] transition-colors ${query.trim() ? 'text-[#0A0A0F]' : 'text-gray-500'}`}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              )}
            </button>
          </div>

          {/* Helper text */}
          <p className="mt-2 text-[11px] text-gray-600 flex items-center gap-1.5 pl-1">
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-white/5 border border-white/10 text-gray-500">Enter</kbd>
            untuk mengirim
            <span className="text-gray-700 mx-1">·</span>
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-white/5 border border-white/10 text-gray-500">Shift+Enter</kbd>
            baris baru
          </p>
        </div>
      </div>
    </form>
  );
}
