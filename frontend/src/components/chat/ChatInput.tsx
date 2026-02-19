'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';

const SendIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
);

interface ChatInputProps {
    value: string;
    onChange: (value: string) => void;
    onSend: () => void;
    isLoading: boolean;
    placeholder?: string;
}

export default function ChatInput({
    value,
    onChange,
    onSend,
    isLoading,
    placeholder = 'Ketik pertanyaan hukum Anda...',
}: ChatInputProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [isFocused, setIsFocused] = useState(false);

    // Auto-resize textarea
    useEffect(() => {
        const ta = textareaRef.current;
        if (ta) {
            ta.style.height = 'auto';
            ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
        }
    }, [value]);

    // Focus on mount
    useEffect(() => {
        setTimeout(() => textareaRef.current?.focus(), 300);
    }, []);

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !isLoading) {
                onSend();
            }
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="border-t border-white/[0.04] bg-[#0A0A0F]/90 backdrop-blur-xl"
        >
            <div className="max-w-3xl mx-auto px-4 py-3">
                <div
                    className={`
            relative flex items-end gap-2 rounded-2xl border transition-all duration-200
            ${isFocused
                            ? 'bg-white/[0.06] border-[#AAFF00]/20 shadow-lg shadow-[#AAFF00]/5'
                            : 'bg-white/[0.03] border-white/[0.06] hover:border-white/[0.1]'
                        }
          `}
                >
                    <textarea
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        placeholder={placeholder}
                        disabled={isLoading}
                        rows={1}
                        className="flex-1 bg-transparent px-4 py-3 text-sm text-white/90 placeholder:text-white/25 focus:outline-none resize-none disabled:opacity-50 disabled:cursor-not-allowed custom-scrollbar leading-relaxed"
                        style={{ maxHeight: '200px' }}
                    />

                    <div className="p-1.5 pr-2 pb-2">
                        <button
                            onClick={onSend}
                            disabled={!value.trim() || isLoading}
                            className={`
                flex items-center justify-center w-9 h-9 rounded-xl transition-all
                ${value.trim() && !isLoading
                                    ? 'bg-[#AAFF00] text-black hover:bg-[#BBFF33] shadow-md shadow-[#AAFF00]/20 active:scale-95'
                                    : 'bg-white/[0.06] text-white/20 cursor-not-allowed'
                                }
              `}
                        >
                            {isLoading ? (
                                <div className="w-4 h-4 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                            ) : (
                                <SendIcon />
                            )}
                        </button>
                    </div>
                </div>

                {/* Disclaimer */}
                <p className="text-center text-[10px] text-white/20 mt-2">
                    AI dapat membuat kesalahan. Mohon verifikasi dengan dokumen asli.
                </p>
            </div>
        </motion.div>
    );
}
