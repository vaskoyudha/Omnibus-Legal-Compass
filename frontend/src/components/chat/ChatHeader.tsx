'use client';

import { motion } from 'framer-motion';

const MenuIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
);

const SparklesIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    </svg>
);

const PlusIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
);

interface ChatHeaderProps {
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
    responseMode: 'synthesized' | 'verbatim';
    onToggleMode: () => void;
    onNewChat: () => void;
}

export default function ChatHeader({
    isSidebarOpen,
    onToggleSidebar,
    responseMode,
    onToggleMode,
    onNewChat,
}: ChatHeaderProps) {
    return (
        <motion.header
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex items-center justify-between px-4 py-3 border-b border-white/[0.04] bg-[#0A0A0F]/80 backdrop-blur-xl"
        >
            {/* Left — Sidebar Toggle */}
            <div className="flex items-center gap-3">
                {!isSidebarOpen && (
                    <motion.button
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        onClick={onToggleSidebar}
                        className="p-2 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-all"
                        title="Buka sidebar"
                    >
                        <MenuIcon />
                    </motion.button>
                )}

                {/* Mobile-only toggle (always visible) */}
                <button
                    onClick={onToggleSidebar}
                    className="p-2 rounded-lg text-white/50 hover:text-white/80 hover:bg-white/[0.06] transition-all lg:hidden"
                    title="Menu"
                >
                    <MenuIcon />
                </button>
            </div>

            {/* Center — Model Badge */}
            <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
                    <SparklesIcon />
                    <span className="text-xs font-semibold text-white/70 tracking-wide">OMNIBUS Legal AI</span>
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>
            </div>

            {/* Right — Mode Toggle + New Chat */}
            <div className="flex items-center gap-2">
                {/* Response mode toggle */}
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.03] border border-white/[0.05]">
                    <span className={`text-[10px] font-medium transition-colors ${responseMode === 'synthesized' ? 'text-[#AAFF00]' : 'text-white/30'}`}>
                        Sintesis
                    </span>
                    <button
                        onClick={onToggleMode}
                        className="relative w-8 h-4 rounded-full bg-white/10 border border-white/10 transition-colors"
                    >
                        <div
                            className={`absolute top-0.5 w-3 h-3 rounded-full bg-[#AAFF00] transition-transform shadow-sm ${responseMode === 'verbatim' ? 'translate-x-4' : 'translate-x-0.5'
                                }`}
                        />
                    </button>
                    <span className={`text-[10px] font-medium transition-colors ${responseMode === 'verbatim' ? 'text-[#AAFF00]' : 'text-white/30'}`}>
                        Kutipan
                    </span>
                </div>

                {/* New Chat shortcut */}
                <button
                    onClick={onNewChat}
                    className="p-2 rounded-lg text-white/50 hover:text-[#AAFF00] hover:bg-[#AAFF00]/5 transition-all"
                    title="Percakapan Baru"
                >
                    <PlusIcon />
                </button>
            </div>
        </motion.header>
    );
}
