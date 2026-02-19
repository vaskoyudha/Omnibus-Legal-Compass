'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Image from 'next/image';
import { CitationInfo, ConfidenceScore, ValidationResult } from '@/lib/api';
import CitationList from '@/components/CitationList';
import InlineCitation from '@/components/chat/InlineCitation';
import { parseInlineCitations } from '@/lib/citation-parser';

// Icons
const SparklesIcon = ({ size = 12 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    </svg>
);

const CopyIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
);

const CheckIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
    </svg>
);

const ChevronDownIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="6 9 12 15 18 9" />
    </svg>
);

const ShieldIcon = () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
);

const AlertIcon = () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
);

const BookOpenIcon = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
);

const ClockIcon = () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
);

export interface ChatMessageData {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: CitationInfo[];
    confidence?: string;
    confidenceScore?: ConfidenceScore;
    validation?: ValidationResult;
    processingTime?: number;
    timestamp: Date;
}

interface ChatMessageProps {
    message: ChatMessageData;
    onCitationClick?: (index: number) => void;
    highlightedCitation?: number | null;
}

// ── Inline helper: renders text with embedded [N] citation superscripts ──────
interface ParsedContentProps {
    content: string;
    citations: CitationInfo[] | undefined;
    onCitationClick?: (index: number) => void;
    highlightedCitation?: number | null;
}

function ParsedContent({ content, citations, onCitationClick, highlightedCitation }: ParsedContentProps) {
    const citationCount = citations?.length ?? 0;
    const segments = parseInlineCitations(content, citationCount);

    return (
        <>
            {segments.map((seg, i) => {
                if (seg.type === 'citation' && seg.citationIndex !== undefined) {
                    const num = parseInt(seg.content, 10);
                    const cit = citations?.[seg.citationIndex];
                    const titleHint = cit ? (cit.citation ?? '') : '';
                    return (
                        <InlineCitation
                            key={i}
                            number={num}
                            citationIndex={seg.citationIndex}
                            onClick={onCitationClick}
                            isHighlighted={seg.citationIndex === highlightedCitation}
                            title={titleHint}
                        />
                    );
                }
                return (
                    <span key={i} style={{ whiteSpace: 'pre-wrap' }}>
                        {seg.content}
                    </span>
                );
            })}
        </>
    );
}

function getConfidenceColor(confidence: string) {
    const lower = confidence.toLowerCase();
    if (lower.includes('high') || lower.includes('tinggi')) return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20';
    if (lower.includes('medium') || lower.includes('sedang')) return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/20';
    return 'bg-red-500/15 text-red-300 border-red-500/20';
}

function getHallucinationConfig(risk: string) {
    switch (risk) {
        case 'low': return { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/15', label: 'Risiko Rendah', icon: '✓' };
        case 'medium': return { color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/15', label: 'Risiko Sedang', icon: '⚠' };
        case 'high': return { color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/15', label: 'Risiko Tinggi', icon: '✗' };
        case 'refused': return { color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/15', label: 'Ditolak', icon: '—' };
        default: return { color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/15', label: risk, icon: '?' };
    }
}

export default function ChatMessage({ message, onCitationClick, highlightedCitation }: ChatMessageProps) {
    const [copied, setCopied] = useState(false);
    const [showCitations, setShowCitations] = useState(true); // Auto-expanded by default
    const [showValidation, setShowValidation] = useState(false);
    const [isHovered, setIsHovered] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(message.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const isUser = message.role === 'user';
    const hasCitations = message.citations && message.citations.length > 0;
    const hasValidation = message.validation;
    const hasConfidenceScore = message.confidenceScore;

    if (isUser) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
                className="flex justify-end mb-6"
            >
                <div className="max-w-[80%] md:max-w-[65%]">
                    <div className="px-4 py-3 rounded-2xl rounded-br-md bg-[#AAFF00]/10 border border-[#AAFF00]/15 text-sm text-white/90 leading-relaxed">
                        <div className="whitespace-pre-wrap">{message.content}</div>
                    </div>
                    <div className="flex justify-end mt-1 pr-1">
                        <span className="text-[10px] text-white/20">
                            {message.timestamp.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </div>
                </div>
            </motion.div>
        );
    }

    // Assistant message
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
            className="flex gap-3 mb-8"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* Avatar */}
            <div className="flex-shrink-0 mt-1">
                <div className="w-7 h-7 rounded-lg overflow-hidden border border-[#AAFF00]/15 shadow-sm shadow-[#AAFF00]/10">
                    <Image src="/logo.png" alt="AI" width={28} height={28} className="w-full h-full object-cover" />
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                {/* Answer text */}
                <div className="text-sm text-white/85 leading-relaxed whitespace-pre-wrap">
                    <ParsedContent
                        content={message.content}
                        citations={message.citations}
                        onCitationClick={onCitationClick}
                        highlightedCitation={highlightedCitation}
                    />
                </div>

                {/* ═══════════ Metadata Bar ═══════════ */}
                <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-white/[0.04]">
                    {/* Confidence Badge */}
                    {message.confidence && (
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${getConfidenceColor(message.confidence)}`}>
                            <SparklesIcon size={11} />
                            Kepercayaan: {message.confidence}
                        </span>
                    )}

                    {/* Confidence Score (Numeric) */}
                    {hasConfidenceScore && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.04] border border-white/[0.06] text-white/50">
                            <span className="text-[#AAFF00] font-bold">{Math.round(hasConfidenceScore.numeric * 100)}%</span>
                            <span className="text-white/25">|</span>
                            Top: {Math.round(hasConfidenceScore.top_score * 100)}%
                            <span className="text-white/25">|</span>
                            Avg: {Math.round(hasConfidenceScore.avg_score * 100)}%
                        </span>
                    )}

                    {/* Hallucination Risk */}
                    {hasValidation && (
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium border ${getHallucinationConfig(hasValidation.hallucination_risk).bg}`}>
                            <ShieldIcon />
                            <span className={getHallucinationConfig(hasValidation.hallucination_risk).color}>
                                {getHallucinationConfig(hasValidation.hallucination_risk).label}
                            </span>
                        </span>
                    )}

                    {/* Grounding Score */}
                    {hasValidation && hasValidation.grounding_score != null && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.04] border border-white/[0.06] text-white/50">
                            Grounding: <span className="text-[#AAFF00] font-bold">{Math.round(hasValidation.grounding_score * 100)}%</span>
                        </span>
                    )}

                    {/* Processing Time */}
                    {message.processingTime && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-white/25">
                            <ClockIcon />
                            {(message.processingTime / 1000).toFixed(1)}s
                        </span>
                    )}

                    {/* Timestamp */}
                    <span className="text-[10px] text-white/20">
                        {message.timestamp.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
                    </span>

                    {/* Action buttons — show on hover */}
                    <motion.div
                        initial={false}
                        animate={{ opacity: isHovered ? 1 : 0 }}
                        className="flex items-center gap-1 ml-auto"
                    >
                        <button
                            onClick={handleCopy}
                            className="p-1.5 rounded-md text-white/25 hover:text-white/60 hover:bg-white/[0.06] transition-all"
                            title="Salin jawaban"
                        >
                            {copied ? <CheckIcon /> : <CopyIcon />}
                        </button>
                    </motion.div>
                </div>

                {/* ═══════════ Validation Details ═══════════ */}
                {hasValidation && (
                    <div className="mt-3">
                        <button
                            onClick={() => setShowValidation(!showValidation)}
                            className="flex items-center gap-1.5 text-[11px] text-white/30 hover:text-white/50 transition-colors"
                        >
                            <motion.div
                                animate={{ rotate: showValidation ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <ChevronDownIcon />
                            </motion.div>
                            <ShieldIcon />
                            Detail Validasi
                        </button>
                        <AnimatePresence>
                            {showValidation && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="mt-2 p-3 rounded-xl bg-white/[0.02] border border-white/[0.05]"
                                >
                                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-[10px]">
                                        {/* Is Valid */}
                                        <div className="flex flex-col gap-1">
                                            <span className="text-white/25 uppercase tracking-wide font-medium">Status</span>
                                            <span className={`font-semibold ${hasValidation.is_valid ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {hasValidation.is_valid ? '✓ Valid' : '✗ Tidak Valid'}
                                            </span>
                                        </div>

                                        {/* Citation Coverage */}
                                        <div className="flex flex-col gap-1">
                                            <span className="text-white/25 uppercase tracking-wide font-medium">Cakupan Sitasi</span>
                                            <div className="flex items-center gap-2">
                                                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full bg-[#AAFF00] transition-all"
                                                        style={{ width: `${Math.round(hasValidation.citation_coverage * 100)}%` }}
                                                    />
                                                </div>
                                                <span className="text-white/50 font-bold">{Math.round(hasValidation.citation_coverage * 100)}%</span>
                                            </div>
                                        </div>

                                        {/* Hallucination Risk */}
                                        <div className="flex flex-col gap-1">
                                            <span className="text-white/25 uppercase tracking-wide font-medium">Risiko Halusinasi</span>
                                            <span className={`font-semibold ${getHallucinationConfig(hasValidation.hallucination_risk).color}`}>
                                                {getHallucinationConfig(hasValidation.hallucination_risk).icon} {getHallucinationConfig(hasValidation.hallucination_risk).label}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Warnings */}
                                    {hasValidation.warnings && hasValidation.warnings.length > 0 && (
                                        <div className="mt-3 pt-2 border-t border-white/[0.04]">
                                            <div className="flex items-center gap-1 text-[10px] text-amber-400/70 font-medium mb-1">
                                                <AlertIcon />
                                                Peringatan
                                            </div>
                                            <ul className="space-y-1">
                                                {hasValidation.warnings.map((w, i) => (
                                                    <li key={i} className="text-[10px] text-white/40 pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-amber-400/40">
                                                        {w}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Ungrounded Claims */}
                                    {hasValidation.ungrounded_claims && hasValidation.ungrounded_claims.length > 0 && (
                                        <div className="mt-3 pt-2 border-t border-white/[0.04]">
                                            <div className="flex items-center gap-1 text-[10px] text-red-400/70 font-medium mb-1">
                                                <AlertIcon />
                                                Klaim Tidak Berdasar
                                            </div>
                                            <ul className="space-y-1">
                                                {hasValidation.ungrounded_claims.map((claim, i) => (
                                                    <li key={i} className="text-[10px] text-white/40 pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-red-400/40">
                                                        {claim}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                )}

                {/* ═══════════ Citations (Auto-expanded) ═══════════ */}
                {hasCitations && (
                    <div className="mt-4">
                        <button
                            onClick={() => setShowCitations(!showCitations)}
                            className="flex items-center gap-2 text-[12px] text-[#AAFF00]/80 hover:text-[#AAFF00] transition-colors font-medium"
                        >
                            <motion.div
                                animate={{ rotate: showCitations ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <ChevronDownIcon />
                            </motion.div>
                            <BookOpenIcon />
                            {message.citations!.length} Sumber Referensi
                        </button>
                        <AnimatePresence>
                            {showCitations && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.25 }}
                                    className="mt-2 rounded-xl overflow-hidden bg-white/[0.015] border border-white/[0.05]"
                                >
                                    <CitationList citations={message.citations!} />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                )}
            </div>
        </motion.div>
    );
}
