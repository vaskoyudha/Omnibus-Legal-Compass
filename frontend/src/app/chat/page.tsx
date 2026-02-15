'use client';

import React, { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { toast } from 'sonner';
import { askQuestion, AskResponse, CitationInfo } from '@/lib/api';
import CitationList from '@/components/CitationList';
import SkeletonLoader from '@/components/SkeletonLoader';

// Icons
const SendIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
    <path d="M3 3v5h5"></path>
    <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
    <path d="M16 21h5v-5"></path>
  </svg>
);

const MessageIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
  </svg>
);

const BotIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="11" width="18" height="10" rx="2"></rect>
    <circle cx="12" cy="5" r="2"></circle>
    <path d="M12 7v4"></path>
    <line x1="8" y1="16" x2="8" y2="16"></line>
    <line x1="16" y1="16" x2="16" y2="16"></line>
  </svg>
);

const SparklesIcon = ({ className }: { className?: string }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path>
  </svg>
);

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationInfo[];
  confidence?: string;
  processingTime?: number;
  timestamp: Date;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } 
  },
};

const SUGGESTIONS = [
  "Apa syarat pendirian PT?",
  "Jelaskan UU Cipta Kerja terkait UMKM",
  "Apa itu Nomor Induk Berusaha (NIB)?",
  "Bagaimana prosedur mendirikan CV?",
];

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen pt-24 pb-10 px-4">
        <div className="max-w-4xl mx-auto flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-8 h-8 border-2 border-[#AAFF00]/30 border-t-[#AAFF00] rounded-full animate-spin" />
            <p className="text-text-muted text-sm">Memuat percakapan...</p>
          </div>
        </div>
      </div>
    }>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [responseMode, setResponseMode] = useState<'synthesized' | 'verbatim'>('synthesized');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoSubmitted = useRef(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Auto-submit question from query param
  useEffect(() => {
    const question = searchParams.get('question');
    if (question && !hasAutoSubmitted.current) {
      hasAutoSubmitted.current = true;
      const decodedQuestion = decodeURIComponent(question);
      setInputValue(decodedQuestion);
      // Small delay to ensure UI is ready, then submit
      setTimeout(() => {
        handleSendMessage(decodedQuestion);
      }, 500);
    }
  }, [searchParams]);

  const handleSendMessage = useCallback(async (text: string = inputValue) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response: AskResponse = await askQuestion(text, 5, sessionId || undefined, responseMode);
      
      if (response.session_id) {
        setSessionId(response.session_id);
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence,
        processingTime: response.processing_time_ms,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      // Error sending message handled by toast notification
      toast.error('Gagal mengirim pertanyaan. Silakan coba lagi.');
    } finally {
      setIsLoading(false);
      // Keep focus on input unless we just clicked a suggestion
      if (text === inputValue) {
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    }
  }, [inputValue, isLoading, sessionId]);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setInputValue('');
    toast.success('Percakapan baru dimulai');
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getConfidenceColor = (confidence: string) => {
    const lower = confidence.toLowerCase();
    if (lower.includes('high') || lower.includes('tinggi')) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    if (lower.includes('medium') || lower.includes('sedang')) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
    return 'bg-red-500/20 text-red-300 border-red-500/30';
  };

  return (
    <div className="min-h-screen pt-24 pb-10 px-4">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-center justify-between gap-4"
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-text-muted mb-1">
              <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
              <span>/</span>
              <span className="text-text-primary">Percakapan</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="ai-badge flex items-center gap-2">
                <MessageIcon className="w-4 h-4" />
                <span>Multi-turn Chat</span>
              </div>
            </div>
            <h1 className="text-3xl font-bold text-text-primary">Percakapan Hukum</h1>
            <p className="text-text-secondary max-w-2xl">
              Tanya jawab hukum dengan konteks percakapan berkelanjutan. AI akan mengingat konteks pertanyaan sebelumnya.
            </p>
          </div>

          <button
            onClick={handleNewChat}
            className="flex items-center gap-2 px-4 py-2 rounded-lg glass border border-white/10 hover:bg-white/5 transition-all text-text-primary text-sm font-medium whitespace-nowrap"
          >
            <RefreshIcon />
            Percakapan Baru
          </button>
        </motion.div>

        {/* Chat Area */}
        <div className="glass-strong rounded-2xl min-h-[600px] flex flex-col relative overflow-hidden border border-white/5">
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-8 py-20">
                <div className="w-20 h-20 rounded-2xl bg-[#AAFF00]/10 flex items-center justify-center mb-4">
                  <BotIcon className="w-10 h-10 text-[#AAFF00]" />
                </div>
                <div className="space-y-2 max-w-md">
                  <h3 className="text-xl font-bold text-text-primary">Mulai Percakapan</h3>
                  <p className="text-text-secondary">
                    Ajukan pertanyaan hukum Anda. Sistem akan mencari referensi dari ribuan dokumen peraturan Indonesia.
                  </p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                  {SUGGESTIONS.map((suggestion, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(suggestion)}
                      className="text-left p-4 rounded-xl glass border border-white/5 hover:border-[#AAFF00]/30 hover:bg-[#AAFF00]/5 transition-all group"
                    >
                      <span className="text-text-primary text-sm group-hover:text-[#AAFF00] transition-colors">
                        {suggestion}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <AnimatePresence initial={false}>
                <motion.div
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="space-y-6"
                >
                  {messages.map((msg) => (
                    <motion.div
                      key={msg.id}
                      variants={itemVariants}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div className={`max-w-[85%] md:max-w-[75%] space-y-2 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                        {/* Message Bubble */}
                        <div
                          className={`
                            p-4 md:p-5 rounded-2xl text-sm md:text-base leading-relaxed
                            ${msg.role === 'user' 
                              ? 'bg-[#AAFF00]/10 border border-[#AAFF00]/20 text-text-primary rounded-tr-sm' 
                              : 'glass-strong border border-white/10 text-text-primary rounded-tl-sm shadow-xl'
                            }
                          `}
                        >
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        </div>

                        {/* Metadata (Assistant only) */}
                        {msg.role === 'assistant' && (
                          <div className="w-full space-y-3 pl-1">
                            {/* Stats Row */}
                            <div className="flex flex-wrap items-center gap-3 text-xs">
                              {msg.confidence && (
                                <span className={`px-2 py-0.5 rounded-full border ${getConfidenceColor(msg.confidence)} flex items-center gap-1`}>
                                  <SparklesIcon className="w-3 h-3" />
                                  Conf: {msg.confidence}
                                </span>
                              )}
                              {msg.processingTime && (
                                <span className="text-text-muted">
                                  {(msg.processingTime / 1000).toFixed(1)}s
                                </span>
                              )}
                              <span className="text-text-muted">
                                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>

                            {/* Citations */}
                            {msg.citations && msg.citations.length > 0 && (
                              <div className="mt-2">
                                <CitationList citations={msg.citations} />
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Timestamp (User only) */}
                        {msg.role === 'user' && (
                          <span className="text-xs text-text-muted pr-1">
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </AnimatePresence>
            )}

            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="max-w-[75%] bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm p-4 w-full">
                  <div className="flex items-center gap-2 mb-3 text-xs text-[#AAFF00] font-medium">
                    <div className="w-2 h-2 rounded-full bg-[#AAFF00] animate-pulse" />
                    Sedang menganalisis peraturan...
                  </div>
                  <SkeletonLoader variant="text" lines={3} />
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 bg-black/40 border-t border-white/10 backdrop-blur-md">
            {/* Mode Toggle */}
            <div className="flex items-center justify-center gap-2 mb-3">
              <span className={`text-xs ${responseMode === 'synthesized' ? 'text-[#AAFF00]' : 'text-text-muted'}`}>Sintesis</span>
              <button
                onClick={() => setResponseMode(responseMode === 'synthesized' ? 'verbatim' : 'synthesized')}
                className="relative w-12 h-6 rounded-full bg-white/10 border border-white/20 transition-colors"
              >
                <div
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-[#AAFF00] transition-transform shadow-md ${
                    responseMode === 'verbatim' ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
              <span className={`text-xs ${responseMode === 'verbatim' ? 'text-[#AAFF00]' : 'text-text-muted'}`}>Kutipan Langsung</span>
            </div>
            
            <div className="flex gap-3 relative">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ketik pertanyaan hukum Anda..."
                disabled={isLoading}
                className="flex-1 bg-white/5 border border-white/10 hover:border-white/20 focus:border-[#AAFF00]/50 rounded-xl px-4 py-3 text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={!inputValue.trim() || isLoading}
                className="px-5 rounded-xl bg-gradient-to-r from-[#AAFF00] to-[#77CC00] text-black font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-[#AAFF00]/10"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                ) : (
                  <SendIcon />
                )}
              </button>
            </div>
            <div className="text-center mt-2">
               <p className="text-[10px] text-text-muted">
                 AI dapat membuat kesalahan. Mohon verifikasi dengan dokumen asli.
               </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
