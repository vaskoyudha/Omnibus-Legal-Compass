'use client';

import React, { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { toast } from 'sonner';
import { askQuestion, AskResponse, fetchChatHistory, deleteChatSession, CitationInfo } from '@/lib/api';
import { useConversationStore, saveMessages, loadMessages } from '@/hooks/useConversationStore';
import ChatSidebar from '@/components/chat/ChatSidebar';
import ChatHeader from '@/components/chat/ChatHeader';
import ChatWelcome from '@/components/chat/ChatWelcome';
import ChatInput from '@/components/chat/ChatInput';
import ChatMessage, { ChatMessageData } from '@/components/chat/ChatMessage';
import CitationPanel from '@/components/chat/CitationPanel';
import SkeletonLoader from '@/components/SkeletonLoader';
import ProviderSelector from '@/components/ProviderSelector';
import { motion } from 'framer-motion';

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-[#0A0A0F]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-8 h-8 border-2 border-[#AAFF00]/30 border-t-[#AAFF00] rounded-full animate-spin" />
            <p className="text-white/40 text-sm">Memuat percakapan...</p>
          </div>
        </div>
      }
    >
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const searchParams = useSearchParams();
  const {
    grouped,
    activeId,
    addConversation,
    updateConversation,
    deleteConversation: deleteConversationMeta,
    setActiveConversation,
  } = useConversationStore();

  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [responseMode, setResponseMode] = useState<'synthesized' | 'verbatim'>('synthesized');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');

  // Citation panel state
  const [activeCitationIndex, setActiveCitationIndex] = useState<number | null>(null);
  const [panelCitations, setPanelCitations] = useState<CitationInfo[]>([]);
  const [activeMsgId, setActiveMsgId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasAutoSubmitted = useRef(false);

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // Auto-submit from URL query param
  useEffect(() => {
    const question = searchParams.get('question');
    if (question && !hasAutoSubmitted.current) {
      hasAutoSubmitted.current = true;
      const decoded = decodeURIComponent(question);
      setInputValue(decoded);
      setTimeout(() => {
        handleSendMessage(decoded);
      }, 500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Load conversation when activeId changes
  useEffect(() => {
    if (activeId && activeId !== sessionId) {
      loadConversation(activeId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  const loadConversation = async (sid: string) => {
    // 1. Try client-side cache first (has full metadata: citations, confidence, validation)
    const cached = loadMessages(sid);
    if (cached && cached.length > 0) {
      setMessages(cached);
      setSessionId(sid);
      return;
    }

    // 2. Fall back to backend (only has role + content, no metadata)
    try {
      const history = await fetchChatHistory(sid);
      const parsed: ChatMessageData[] = history.messages.map((msg, idx) => ({
        id: `${sid}-${idx}`,
        role: msg.role,
        content: msg.content,
        timestamp: new Date(),
      }));
      setMessages(parsed);
      setSessionId(sid);
    } catch {
      // If backend doesn't have this session either, start fresh
      setMessages([]);
      setSessionId(sid);
    }
  };

  const handleSendMessage = useCallback(
    async (text: string = inputValue) => {
      if (!text.trim() || isLoading) return;

      const userMessage: ChatMessageData = {
        id: Date.now().toString(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue('');
      setIsLoading(true);

      try {
        const response: AskResponse = await askQuestion(
          text,
          5,
          sessionId || undefined,
          responseMode,
          selectedProvider || undefined,
          selectedModel || undefined
        );

        // Update session ID
        const newSessionId = response.session_id || sessionId;
        if (response.session_id) {
          setSessionId(response.session_id);
        }

        // If this is a new conversation, add it to the store
        if (!sessionId && newSessionId) {
          const title = text.slice(0, 60);
          addConversation(newSessionId, title);
        } else if (newSessionId) {
          // Touch the updatedAt
          updateConversation(newSessionId, {});
        }

        const botMessage: ChatMessageData = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          confidence: response.confidence,
          confidenceScore: response.confidence_score,
          validation: response.validation,
          processingTime: response.processing_time_ms,
          timestamp: new Date(),
        };

        // Update citation panel with the latest bot message's citations
        if (response.citations && response.citations.length > 0) {
          setPanelCitations(response.citations);
          setActiveMsgId(botMessage.id);
          setActiveCitationIndex(null);
        }

        setMessages((prev) => {
          const updated = [...prev, botMessage];
          // Cache messages with full metadata to localStorage
          const sid = response.session_id || sessionId;
          if (sid) saveMessages(sid, updated);
          return updated;
        });
      } catch {
        toast.error('Gagal mengirim pertanyaan. Silakan coba lagi.');
      } finally {
        setIsLoading(false);
      }
    },
    [inputValue, isLoading, sessionId, responseMode, selectedProvider, selectedModel, addConversation, updateConversation]
  );

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setInputValue('');
    setActiveConversation(null);
    setPanelCitations([]);
    setActiveCitationIndex(null);
    setActiveMsgId(null);
    toast.success('Percakapan baru dimulai');
  }, [setActiveConversation]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      if (id === sessionId) return;
      setActiveConversation(id);
      // Close sidebar on mobile
      if (window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      }
    },
    [sessionId, setActiveConversation]
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await deleteChatSession(id);
      } catch {
        // Backend might not have it — that's fine
      }
      deleteConversationMeta(id);
      if (id === sessionId) {
        setMessages([]);
        setSessionId(null);
      }
      toast.success('Percakapan dihapus');
    },
    [deleteConversationMeta, sessionId]
  );

  const handleSuggestionClick = useCallback(
    (text: string) => {
      handleSendMessage(text);
    },
    [handleSendMessage]
  );

  return (
    <div className="flex h-screen bg-[#0A0A0F] overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        grouped={grouped}
        activeId={activeId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
      />

      {/* Main content + Citation Panel wrapper */}
      <div className="flex flex-1 min-w-0 h-screen overflow-hidden">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 h-screen">
          {/* Header */}
          <ChatHeader
            isSidebarOpen={isSidebarOpen}
            onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            responseMode={responseMode}
            onToggleMode={() =>
              setResponseMode((m) => (m === 'synthesized' ? 'verbatim' : 'synthesized'))
            }
            onNewChat={handleNewChat}
          />

          {/* Provider Selector toolbar */}
          <div
            className="flex items-center justify-end px-4 py-2 border-b border-white/[0.04]"
            style={{ background: 'rgba(255,255,255,0.01)' }}
          >
            <ProviderSelector
              onProviderChange={(provider, model) => {
                setSelectedProvider(provider);
                setSelectedModel(model);
              }}
            />
          </div>

          {/* Messages Area */}
          {messages.length === 0 ? (
            <ChatWelcome onSuggestionClick={handleSuggestionClick} />
          ) : (
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="max-w-3xl mx-auto px-4 py-6">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    onCitationClick={msg.role === 'assistant' ? (idx) => {
                      setPanelCitations(msg.citations ?? []);
                      setActiveMsgId(msg.id);
                      setActiveCitationIndex(idx);
                    } : undefined}
                    highlightedCitation={
                      msg.role === 'assistant' && activeMsgId === msg.id
                        ? activeCitationIndex
                        : null
                    }
                  />
                ))}

                {/* Loading indicator */}
                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-3 mb-6"
                  >
                    <div className="w-7 h-7 rounded-lg bg-[#AAFF00]/10 border border-[#AAFF00]/15 flex items-center justify-center flex-shrink-0">
                      <div className="w-3 h-3 rounded-full bg-[#AAFF00] animate-pulse" />
                    </div>
                    <div className="flex-1 max-w-[75%]">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[11px] text-[#AAFF00]/70 font-medium">
                          Sedang menganalisis peraturan...
                        </span>
                      </div>
                      <SkeletonLoader variant="text" lines={3} />
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>
          )}

          {/* Input */}
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSend={() => handleSendMessage()}
            isLoading={isLoading}
          />
        </div>

        {/* Citation Panel (desktop only) */}
        <CitationPanel
          citations={panelCitations}
          activeCitationIndex={activeCitationIndex}
          onCitationClick={(idx) => setActiveCitationIndex(idx)}
        />
      </div>
    </div>
  );
}
