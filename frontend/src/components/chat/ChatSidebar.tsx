'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { ConversationMeta, GroupedConversations } from '@/hooks/useConversationStore';

// Icons
const PlusIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
);

const SearchIcon = () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
);

const TrashIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
);

const MessageSquareIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
);

const HomeIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
    </svg>
);

const ChevronLeftIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="11 17 6 12 11 7" /><polyline points="18 17 13 12 18 7" />
    </svg>
);

interface ChatSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    grouped: GroupedConversations[];
    activeId: string | null;
    onSelectConversation: (id: string) => void;
    onNewChat: () => void;
    onDeleteConversation: (id: string) => void;
}

export default function ChatSidebar({
    isOpen,
    onClose,
    grouped,
    activeId,
    onSelectConversation,
    onNewChat,
    onDeleteConversation,
}: ChatSidebarProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [hoveredId, setHoveredId] = useState<string | null>(null);

    const filteredGroups = useMemo(() => {
        if (!searchQuery.trim()) return grouped;
        const q = searchQuery.toLowerCase();
        return grouped
            .map((group) => ({
                ...group,
                conversations: group.conversations.filter((c) =>
                    c.title.toLowerCase().includes(q)
                ),
            }))
            .filter((group) => group.conversations.length > 0);
    }, [grouped, searchQuery]);

    const formatTime = (iso: string) => {
        const d = new Date(iso);
        return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    };

    const sidebarContent = (
        <div className="flex flex-col h-full bg-[#0A0A0F] border-r border-white/[0.06]">
            {/* Header */}
            <div className="p-4 pb-3">
                <div className="flex items-center justify-between mb-4">
                    <Link href="/" className="flex items-center gap-2.5 group">
                        <div className="w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center border border-[#AAFF00]/20 shadow-md shadow-[#AAFF00]/10">
                            <Image src="/logo.png" alt="OMNIBUS" width={32} height={32} className="w-full h-full object-cover" />
                        </div>
                        <span className="font-bold text-sm text-white/90 tracking-tight">OMNIBUS</span>
                    </Link>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/5 transition-all lg:block hidden"
                        title="Tutup sidebar"
                    >
                        <ChevronLeftIcon />
                    </button>
                </div>

                {/* New Chat Button */}
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#AAFF00]/10 border border-[#AAFF00]/20 text-[#AAFF00] text-sm font-semibold hover:bg-[#AAFF00]/15 hover:border-[#AAFF00]/30 hover:shadow-lg hover:shadow-[#AAFF00]/5 transition-all active:scale-[0.98]"
                >
                    <PlusIcon />
                    Percakapan Baru
                </button>
            </div>

            {/* Search */}
            <div className="px-4 pb-3">
                <div className="relative">
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30">
                        <SearchIcon />
                    </div>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Cari percakapan..."
                        className="w-full bg-white/[0.04] border border-white/[0.06] rounded-lg pl-9 pr-3 py-2 text-xs text-white/80 placeholder:text-white/25 focus:outline-none focus:border-[#AAFF00]/30 focus:bg-white/[0.06] transition-all"
                    />
                </div>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto px-2 pb-3 custom-scrollbar">
                {filteredGroups.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="w-10 h-10 rounded-xl bg-white/[0.04] flex items-center justify-center mb-3">
                            <MessageSquareIcon />
                        </div>
                        <p className="text-xs text-white/30">
                            {searchQuery ? 'Tidak ditemukan' : 'Belum ada percakapan'}
                        </p>
                    </div>
                ) : (
                    filteredGroups.map((group) => (
                        <div key={group.label} className="mb-4">
                            <p className="px-2 py-1.5 text-[10px] font-semibold text-white/25 uppercase tracking-wider">
                                {group.label}
                            </p>
                            <div className="space-y-0.5">
                                {group.conversations.map((conv) => (
                                    <div
                                        key={conv.id}
                                        onMouseEnter={() => setHoveredId(conv.id)}
                                        onMouseLeave={() => setHoveredId(null)}
                                        onClick={() => onSelectConversation(conv.id)}
                                        className={`
                      group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all text-sm
                      ${activeId === conv.id
                                                ? 'bg-[#AAFF00]/8 text-white border-l-2 border-[#AAFF00]/60'
                                                : 'text-white/60 hover:bg-white/[0.04] hover:text-white/80 border-l-2 border-transparent'
                                            }
                    `}
                                    >
                                        <MessageSquareIcon />
                                        <div className="flex-1 min-w-0">
                                            <p className="truncate text-xs font-medium leading-tight">{conv.title}</p>
                                            <p className="text-[10px] text-white/25 mt-0.5">{formatTime(conv.updatedAt)}</p>
                                        </div>

                                        {/* Delete button */}
                                        <AnimatePresence>
                                            {hoveredId === conv.id && (
                                                <motion.button
                                                    initial={{ opacity: 0, scale: 0.8 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                    exit={{ opacity: 0, scale: 0.8 }}
                                                    transition={{ duration: 0.15 }}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        onDeleteConversation(conv.id);
                                                    }}
                                                    className="p-1 rounded-md text-white/30 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                                                    title="Hapus percakapan"
                                                >
                                                    <TrashIcon />
                                                </motion.button>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-white/[0.04]">
                <Link
                    href="/"
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-white/40 hover:text-white/70 hover:bg-white/[0.04] transition-all"
                >
                    <HomeIcon />
                    <span>Kembali ke Beranda</span>
                </Link>
                <div className="flex items-center gap-2 px-3 mt-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.5)]" />
                    <span className="text-[10px] text-white/25">Sistem Online</span>
                </div>
            </div>
        </div>
    );

    return (
        <>
            {/* Desktop sidebar */}
            <AnimatePresence>
                {isOpen && (
                    <motion.aside
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                        className="hidden lg:block h-screen overflow-hidden flex-shrink-0"
                    >
                        <div className="w-[280px] h-full">
                            {sidebarContent}
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>

            {/* Mobile overlay */}
            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
                            onClick={onClose}
                        />
                        <motion.aside
                            initial={{ x: '-100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '-100%' }}
                            transition={{ type: 'spring', bounce: 0.1, duration: 0.35 }}
                            className="fixed top-0 left-0 bottom-0 w-[280px] z-50 lg:hidden"
                        >
                            {sidebarContent}
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </>
    );
}
