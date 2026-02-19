'use client';

import { motion } from 'framer-motion';
import Image from 'next/image';

const SUGGESTIONS = [
    {
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#AAFF00]">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
            </svg>
        ),
        text: 'Apa syarat pendirian PT?',
    },
    {
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#AAFF00]">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
        ),
        text: 'Jelaskan UU Cipta Kerja terkait UMKM',
    },
    {
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#AAFF00]">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
        ),
        text: 'Apa itu Nomor Induk Berusaha (NIB)?',
    },
    {
        icon: (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#AAFF00]">
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="2" />
            </svg>
        ),
        text: 'Bagaimana prosedur mendirikan CV?',
    },
];

const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: { staggerChildren: 0.08, delayChildren: 0.3 },
    },
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
    },
};

interface ChatWelcomeProps {
    onSuggestionClick: (text: string) => void;
}

export default function ChatWelcome({ onSuggestionClick }: ChatWelcomeProps) {
    return (
        <div className="flex-1 flex items-center justify-center p-6">
            <motion.div
                variants={containerVariants}
                initial="hidden"
                animate="visible"
                className="flex flex-col items-center text-center max-w-2xl w-full"
            >
                {/* Logo with glow */}
                <motion.div variants={itemVariants} className="relative mb-6">
                    <div className="absolute inset-0 rounded-2xl bg-[#AAFF00]/10 blur-2xl scale-150" />
                    <div className="relative w-16 h-16 rounded-2xl overflow-hidden border border-[#AAFF00]/20 shadow-lg shadow-[#AAFF00]/10">
                        <Image src="/logo.png" alt="OMNIBUS" width={64} height={64} className="w-full h-full object-cover" />
                    </div>
                </motion.div>

                {/* Greeting */}
                <motion.h2
                    variants={itemVariants}
                    className="text-2xl md:text-3xl font-bold text-white/90 mb-2"
                >
                    Halo, ada yang bisa saya bantu?
                </motion.h2>
                <motion.p
                    variants={itemVariants}
                    className="text-sm text-white/40 mb-8 max-w-md"
                >
                    Tanya apa saja tentang hukum dan regulasi Indonesia. Saya akan mencari referensi dari dokumen peraturan resmi.
                </motion.p>

                {/* Suggestion Cards */}
                <motion.div
                    variants={itemVariants}
                    className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg"
                >
                    {SUGGESTIONS.map((suggestion, idx) => (
                        <motion.button
                            key={idx}
                            variants={itemVariants}
                            whileHover={{ scale: 1.02, y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => onSuggestionClick(suggestion.text)}
                            className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:border-[#AAFF00]/20 hover:bg-[#AAFF00]/[0.03] transition-all text-left group"
                        >
                            <div className="mt-0.5 flex-shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                                {suggestion.icon}
                            </div>
                            <span className="text-xs text-white/60 group-hover:text-white/80 transition-colors leading-relaxed">
                                {suggestion.text}
                            </span>
                        </motion.button>
                    ))}
                </motion.div>
            </motion.div>
        </div>
    );
}
