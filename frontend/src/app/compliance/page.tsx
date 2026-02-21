'use client';

import { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { checkCompliance, ComplianceResponse } from '@/lib/api';
import CitationList from '@/components/CitationList';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import StarBorder from '@/components/reactbits/StarBorder';
import LaserFlow from '@/components/reactbits/LaserFlow';
import { toast } from 'sonner';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
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

type InputType = 'text' | 'pdf';

export default function CompliancePage() {
  const [inputType, setInputType] = useState<InputType>('text');
  const [businessDescription, setBusinessDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ComplianceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setResult(null);

    if (inputType === 'text' && !businessDescription.trim()) {
      toast.error('Silakan masukkan deskripsi bisnis');
      return;
    }

    if (inputType === 'pdf' && !selectedFile) {
      toast.error('Silakan pilih file PDF');
      return;
    }

    setIsLoading(true);
    try {
      let response: ComplianceResponse;
      if (inputType === 'pdf' && selectedFile) {
        response = await checkCompliance('', selectedFile);
      } else {
        response = await checkCompliance(businessDescription);
      }
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      toast.error('Gagal memeriksa kepatuhan');
    } finally {
      setIsLoading(false);
    }
  }, [inputType, businessDescription, selectedFile]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        toast.error('Hanya file PDF yang didukung');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error('Ukuran file maksimal 10MB');
        return;
      }
      setSelectedFile(file);
    }
  };

  const getStatusConfig = (compliant: boolean) => {
    if (compliant) return {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      gradient: 'from-emerald-500/20 to-transparent',
      label: 'Sesuai Regulasi',
      icon: <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    };
    return {
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      text: 'text-red-400',
      gradient: 'from-red-500/20 to-transparent',
      label: 'Tidak Sesuai',
      icon: <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    };
  };

  const getRiskConfig = (risk: string) => {
    const r = risk.toLowerCase();
    if (r === 'low' || r === 'rendah') return { text: 'text-emerald-400', bg: 'bg-emerald-500/15', border: 'border-emerald-500/30', label: 'Risiko Rendah' };
    if (r === 'medium' || r === 'sedang') return { text: 'text-amber-400', bg: 'bg-amber-500/15', border: 'border-amber-500/30', label: 'Risiko Sedang' };
    return { text: 'text-red-400', bg: 'bg-red-500/15', border: 'border-red-500/30', label: 'Risiko Tinggi' };
  };

  return (
    <div className="min-h-screen bg-[#050508] relative overflow-hidden flex flex-col lg:flex-row -mt-16 sm:-mt-20">
      {/* GLOBAL FILM GRAIN */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
          backgroundSize: '200px 200px',
        }}
      />

      {/* LEFT PANEL : HERO (Sticky on Desktop) */}
      <div className="relative w-full lg:w-1/2 min-h-[50vh] lg:min-h-screen lg:sticky lg:top-0 lg:left-0 flex flex-col justify-between overflow-hidden border-b lg:border-b-0 lg:border-r border-white/[0.05]">

        {/* Background Animation Container */}
        <div className="absolute inset-0 z-0 bg-black">
          <LaserFlow
            color="#AAFF00"
            flowSpeed={0.5}
            wispSpeed={20}
            wispIntensity={6}
            fogIntensity={0.6}
            horizontalSizing={1}
            verticalSizing={2}
          />
          {/* Vignette & Gradient Mask over LaserFlow */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#050508]/40 to-[#050508] z-10" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#050508]/80 via-transparent to-[#050508]/80 z-10" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#050508_100%)] z-10 opacity-60" />
        </div>

        {/* Left Panel Content */}
        <div className="relative z-20 flex-1 flex flex-col p-8 md:p-12 lg:p-16 xl:p-24 pt-24 lg:pt-32 justify-between h-full">

          <nav className="flex items-center gap-3 text-xs md:text-sm font-medium text-white/50 mb-12">
            <Link href="/" className="hover:text-[#AAFF00] transition-colors flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Kembali
            </Link>
          </nav>

          <div className="max-w-xl">
            <motion.h1
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.1 }}
              className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tighter text-white mb-6 leading-[1.1]"
            >
              Validasi <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-br from-[#AAFF00] via-white to-white/40">
                Kepatuhan.
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
              className="text-white/60 text-lg md:text-xl font-light leading-relaxed max-w-md"
            >
              Harmonisasi dokumen operasional dan rancangan bisnis Anda secara real-time terhadap pangkalan data hukum nasional.
            </motion.p>
          </div>

          {/* Bottom stats / subtle UI elements on hero side */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1, duration: 1 }}
            className="hidden lg:flex items-center gap-8 mt-12 pt-8 border-t border-white/[0.05]"
          >
            <div>
              <p className="text-[#AAFF00] font-mono text-2xl font-bold">14.2k</p>
              <p className="text-xs text-white/40 uppercase tracking-widest font-semibold mt-1">Regulasi Dipindai</p>
            </div>
            <div className="w-px h-10 bg-white/[0.05]"></div>
            <div>
              <p className="text-white font-mono text-2xl font-bold">&lt; 2s</p>
              <p className="text-xs text-white/40 uppercase tracking-widest font-semibold mt-1">Estimasi Waktu</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* RIGHT PANEL : INTERACTIVE FORM & RESULTS (Scrollable) */}
      <div className="w-full lg:w-1/2 min-h-screen bg-[#060609] relative z-20 overflow-y-auto custom-scrollbar shadow-[-20px_0_50px_rgba(0,0,0,0.5)]">
        {/* Subtle ambient gradient on right panel */}
        <div className="absolute top-0 left-0 w-full h-[40vh] bg-gradient-to-b from-[#AAFF00]/[0.02] to-transparent pointer-events-none" />
        <div className="absolute top-1/3 right-0 w-1/2 h-[50vh] bg-[radial-gradient(ellipse_at_right,rgba(170,255,0,0.03),transparent_70%)] pointer-events-none" />

        <div className="relative p-5 md:p-8 lg:p-12 xl:p-16 pt-24 lg:pt-32 max-w-2xl mx-auto flex flex-col justify-center min-h-full">

          {/* Content Wrapper */}
          <div className="w-full relative">

            {/* THE FORM */}
            {!isLoading && !result && (
              <motion.div
                className="w-full"
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}
              >
                {/* Header */}
                <div className="mb-8 hidden lg:block">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-[#AAFF00]/10 border border-[#AAFF00]/20 flex items-center justify-center">
                      <svg className="w-4 h-4 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-white/90 tracking-tight">Mulai Analisis</h2>
                    </div>
                  </div>
                  <p className="text-white/35 text-sm leading-relaxed pl-11">Pilih metode input dan deskripsikan bisnis Anda untuk analisis kepatuhan.</p>
                </div>

                {/* Unified Form Card */}
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    boxShadow: '0 0 0 1px rgba(0,0,0,0.3), 0 8px 40px rgba(0,0,0,0.3)',
                  }}
                >
                  {/* Tab Selector — integrated into card top */}
                  <div className="flex relative border-b border-white/[0.06]">
                    {(['text', 'pdf'] as const).map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setInputType(type)}
                        className={`relative flex-1 py-4 px-4 text-[13px] font-semibold transition-all z-10 outline-none ${inputType === type
                          ? 'text-[#AAFF00]'
                          : 'text-white/30 hover:text-white/60'
                          }`}
                      >
                        {inputType === type && (
                          <motion.div
                            layoutId="activeTabMode"
                            className="absolute inset-0 bg-[#AAFF00]/[0.06]"
                            initial={false}
                            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                          />
                        )}
                        {inputType === type && (
                          <motion.div
                            layoutId="activeTabIndicator"
                            className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#AAFF00]"
                            initial={false}
                            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                          />
                        )}
                        <span className="relative z-20 flex items-center justify-center gap-2">
                          {type === 'text' ? (
                            <>
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
                              </svg>
                              Input Teks
                            </>
                          ) : (
                            <>
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                              </svg>
                              Upload PDF
                            </>
                          )}
                        </span>
                      </button>
                    ))}
                  </div>

                  {/* Form Body */}
                  <form onSubmit={handleSubmit}>
                    <div className="p-5 md:p-6">
                      <AnimatePresence mode="wait">
                        {inputType === 'text' ? (
                          <motion.div
                            key="text-input"
                            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}
                          >
                            <label className="block text-[11px] uppercase tracking-widest text-white/25 font-semibold mb-3">Deskripsi Bisnis</label>
                            <textarea
                              value={businessDescription}
                              onChange={(e) => setBusinessDescription(e.target.value)}
                              placeholder="Jelaskan secara komprehensif: model bisnis, sektor industri, lokasi pendirian badan usaha, rencana kegiatan strategis, dan skala modal..."
                              className="w-full h-56 p-5 rounded-xl bg-black/40 border border-white/[0.06] text-white/90 placeholder:text-white/15 focus:outline-none focus:border-[#AAFF00]/30 focus:ring-1 focus:ring-[#AAFF00]/20 resize-none text-sm leading-relaxed transition-all"
                              disabled={isLoading}
                            />
                            <div className="flex items-center justify-between mt-2.5">
                              <span className="text-[11px] text-white/15">{businessDescription.length} karakter</span>
                              <span className="text-[11px] text-white/15">Min. 50 karakter disarankan</span>
                            </div>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="pdf-input"
                            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}
                          >
                            <label className="block text-[11px] uppercase tracking-widest text-white/25 font-semibold mb-3">Dokumen PDF</label>
                            <div
                              className={`relative group overflow-hidden border border-dashed rounded-xl p-10 text-center transition-all duration-300 cursor-pointer ${selectedFile
                                ? 'border-[#AAFF00]/30 bg-[#AAFF00]/[0.03]'
                                : 'border-white/[0.08] hover:border-[#AAFF00]/20 hover:bg-white/[0.01]'
                                }`}
                              onClick={() => fileInputRef.current?.click()}
                            >
                              <input
                                ref={fileInputRef}
                                type="file"
                                accept="application/pdf"
                                onChange={handleFileChange}
                                className="hidden"
                              />

                              <AnimatePresence mode="wait">
                                {selectedFile ? (
                                  <motion.div
                                    key="file-selected"
                                    initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
                                    className="flex flex-col items-center gap-4 relative z-10"
                                  >
                                    <div className="w-14 h-14 rounded-xl bg-[#AAFF00]/10 border border-[#AAFF00]/20 flex items-center justify-center">
                                      <svg className="w-7 h-7 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                      </svg>
                                    </div>
                                    <div className="text-center">
                                      <p className="font-semibold text-white text-sm max-w-xs truncate">{selectedFile.name}</p>
                                      <p className="text-[11px] text-[#AAFF00]/70 mt-1">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB • Siap dianalisis</p>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                                      className="text-[11px] text-white/30 hover:text-red-400 font-medium transition-colors px-4 py-1.5 rounded-lg hover:bg-red-500/10"
                                    >
                                      Hapus
                                    </button>
                                  </motion.div>
                                ) : (
                                  <motion.div
                                    key="no-file"
                                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                    className="relative z-10 flex flex-col items-center py-2"
                                  >
                                    <div className="w-14 h-14 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-4 group-hover:border-[#AAFF00]/20 group-hover:bg-[#AAFF00]/[0.04] transition-all">
                                      <svg className="w-6 h-6 text-white/20 group-hover:text-[#AAFF00]/60 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                                      </svg>
                                    </div>
                                    <p className="text-white/60 font-medium text-sm mb-1">Pilih atau seret file PDF</p>
                                    <p className="text-[11px] text-white/20">Maksimal 10MB</p>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Button Footer — inside card */}
                    <div className="px-5 md:px-6 pb-5 md:pb-6">
                      <motion.button
                        type="submit"
                        disabled={isLoading}
                        className="relative w-full py-4 rounded-xl font-semibold text-sm tracking-wide overflow-hidden group disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                        style={{
                          background: 'linear-gradient(135deg, #AAFF00 0%, #8BD800 50%, #AAFF00 100%)',
                          color: '#0A0A0F',
                          boxShadow: '0 2px 8px rgba(170,255,0,0.2), inset 0 1px 0 rgba(255,255,255,0.2)',
                        }}
                        whileHover={{
                          scale: 1.01,
                          boxShadow: '0 4px 20px rgba(170,255,0,0.35), 0 0 60px rgba(170,255,0,0.08), inset 0 1px 0 rgba(255,255,255,0.25)',
                        }}
                        whileTap={{ scale: 0.99 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                      >
                        {/* Shimmer */}
                        <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-[1s] ease-in-out bg-gradient-to-r from-transparent via-white/30 to-transparent" />
                        <span className="relative z-10 flex items-center justify-center gap-2.5">
                          <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                          Jalankan Analisis AI
                        </span>
                      </motion.button>
                    </div>
                  </form>
                </div>

                {/* Subtle helper text below card */}
                <div className="flex items-center justify-center gap-4 mt-5">
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    Data terenkripsi
                  </span>
                  <span className="w-px h-3 bg-white/[0.06]" />
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    Hasil ~2 detik
                  </span>
                  <span className="w-px h-3 bg-white/[0.06]" />
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                    RAG Pipeline
                  </span>
                </div>

              </motion.div>
            )}

            {/* SCANNING LOADER */}
            <AnimatePresence>
              {isLoading && (
                <motion.div
                  className="w-full flex items-center justify-center min-h-[400px]"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.05 }}
                >
                  <div className="text-center w-full max-w-sm relative">
                    {/* Vertical scanning pulse behind */}
                    <div className="absolute inset-0 bg-[#AAFF00]/5 blur-[100px] rounded-full animate-pulse" />

                    <div className="w-32 h-32 mx-auto relative mb-10">
                      <div className="absolute inset-0 border border-white/5 rounded-full" />
                      <div className="absolute inset-0 border border-[#AAFF00]/30 rounded-full animate-ping" style={{ animationDuration: '3s' }} />
                      <div className="absolute inset-4 border-[2px] border-[#AAFF00]/80 rounded-full border-t-transparent animate-spin" style={{ animationDuration: '1.5s' }} />
                      <div className="absolute inset-8 border-[2px] border-white/30 rounded-full border-b-transparent animate-spin" style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
                      <div className="absolute inset-0 flex items-center justify-center text-[#AAFF00]">
                        <svg className="w-8 h-8 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                    </div>

                    <h3 className="text-2xl font-black mb-3 tracking-wide text-white">Mengekstrak Konteks</h3>
                    <p className="text-white/40 text-sm font-light max-w-xs mx-auto leading-relaxed">
                      AI sedang melakukan pemetaan semantik terhadap perpustakaan regulasi Indonesia...
                    </p>

                    <div className="w-full mt-12 space-y-4 opacity-40">
                      <div className="h-1 bg-white/20 rounded-full w-full overflow-hidden">
                        <motion.div
                          className="h-full bg-[#AAFF00]"
                          animate={{ x: ['-100%', '200%'] }}
                          transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                        />
                      </div>
                      <div className="h-1 bg-white/20 rounded-full w-3/4 overflow-hidden">
                        <motion.div
                          className="h-full bg-white"
                          animate={{ x: ['-100%', '200%'] }}
                          transition={{ repeat: Infinity, duration: 2, ease: 'linear', delay: 0.2 }}
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* RESULTS DASHBOARD */}
            {!isLoading && result && (
              <motion.div
                className="w-full flex flex-col gap-6 pb-20"
                variants={containerVariants}
                initial="hidden"
                animate="visible"
              >
                <div className="flex justify-between items-end mb-4">
                  <h2 className="text-2xl font-bold text-white tracking-tight">Laporan AI</h2>
                  <button
                    type="button"
                    onClick={() => setResult(null)}
                    className="text-xs font-bold uppercase tracking-widest text-[#AAFF00] hover:text-white transition-colors flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                    Uji Baru
                  </button>
                </div>

                {/* Status Card - Ultra Premium */}
                <motion.div variants={itemVariants}>
                  <SpotlightCard className="p-8 border border-white/[0.08] bg-[#0A0A0F]/90 backdrop-blur-xl" spotlightColor="rgba(255, 255, 255, 0.05)">
                    {(() => {
                      const config = getStatusConfig(result.compliant);
                      return (
                        <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
                          <div className="relative shrink-0">
                            <div className={`absolute inset-0 bg-gradient-to-b ${config.gradient} blur-[20px] opacity-100 rounded-full`} />
                            <div className={`w-20 h-20 rounded-3xl ${config.bg} ${config.text} border ${config.border} flex items-center justify-center relative z-10 shadow-2xl`}>
                              {config.icon}
                            </div>
                          </div>
                          <div className="flex-1 text-center md:text-left">
                            <h2 className="text-3xl font-black text-white mb-3 tracking-tight">
                              {config.label}
                            </h2>
                            {result.risk_level && (
                              <div className="inline-flex items-center gap-3">
                                <span className="text-xs text-white/40 uppercase tracking-widest font-bold">Indeks Risiko</span>
                                {(() => {
                                  const riskConfig = getRiskConfig(result.risk_level!);
                                  return (
                                    <span className={`px-3 py-1 text-xs font-bold tracking-wide rounded-md border ${riskConfig.bg} ${riskConfig.border} ${riskConfig.text}`}>
                                      {riskConfig.label}
                                    </span>
                                  );
                                })()}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })()}

                    {/* Summary */}
                    {result.summary && (
                      <div className="mt-8 pt-8 border-t border-white/[0.05]">
                        <h3 className="text-xs font-bold text-white/50 mb-3 uppercase tracking-widest">Ringkasan Eksekutif</h3>
                        <p className="text-white/80 leading-relaxed font-light text-sm">
                          {result.summary}
                        </p>
                      </div>
                    )}
                  </SpotlightCard>
                </motion.div>

                {/* Findings (Issues) */}
                {result.issues && result.issues.length > 0 && (
                  <motion.div variants={itemVariants}>
                    <div className="rounded-3xl border border-red-500/20 overflow-hidden bg-[#0A0A0F]/90 backdrop-blur-xl">
                      <div className="px-6 py-4 border-b border-red-500/20 bg-red-500/[0.05] flex justify-between items-center">
                        <h3 className="text-sm font-bold text-red-100 flex items-center gap-2 uppercase tracking-wide">
                          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                          Temuan Pelanggaran
                        </h3>
                        <span className="text-xs font-black text-red-500 tracking-widest">{result.issues.length} ISSUE</span>
                      </div>
                      <div className="p-2 divide-y divide-white/[0.05]">
                        {result.issues.map((issue, i) => (
                          <div key={i} className="p-4 flex items-start gap-4 hover:bg-white/[0.02] transition-colors rounded-xl">
                            <span className="flex-shrink-0 mt-0.5 text-red-500/50 font-mono text-xs font-bold">{String(i + 1).padStart(2, '0')}</span>
                            <p className="text-white/70 text-sm leading-relaxed">{issue.issue}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Recommendations */}
                {result.recommendations && result.recommendations.length > 0 && (
                  <motion.div variants={itemVariants}>
                    <div className="rounded-3xl border border-[#AAFF00]/20 overflow-hidden bg-[#0A0A0F]/90 backdrop-blur-xl">
                      <div className="px-6 py-4 border-b border-[#AAFF00]/20 bg-[#AAFF00]/[0.05] flex justify-between items-center">
                        <h3 className="text-sm font-bold text-[#AAFF00] flex items-center gap-2 uppercase tracking-wide">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Rekomendasi Tindakan
                        </h3>
                      </div>
                      <div className="p-2 divide-y divide-white/[0.05]">
                        {result.recommendations.map((rec, i) => (
                          <div key={i} className="p-4 flex items-start gap-4 hover:bg-[#AAFF00]/[0.02] transition-colors rounded-xl">
                            <span className="flex-shrink-0 mt-0.5 text-[#AAFF00]/50 font-mono text-xs font-bold">R{i + 1}</span>
                            <p className="text-white/80 text-sm leading-relaxed">{rec}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Citations */}
                {result.citations && result.citations.length > 0 && (
                  <motion.div variants={itemVariants}>
                    <div className="rounded-3xl border border-white/[0.1] bg-[#0A0A0F]/90 backdrop-blur-xl overflow-hidden p-1">
                      <CitationList citations={result.citations} />
                    </div>
                  </motion.div>
                )}

              </motion.div>
            )}

          </div>
        </div>
      </div>

      {/* Error Toast / Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="fixed bottom-6 right-6 z-50 w-full max-w-sm"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <div className="bg-black/90 backdrop-blur-xl border border-red-500/30 rounded-2xl p-5 flex gap-4 shadow-[0_10px_40px_rgba(239,68,68,0.2)]">
              <svg className="w-6 h-6 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <h4 className="text-sm font-bold text-red-100">Analisis Gagal</h4>
                <p className="text-xs text-red-200/60 mt-1 leading-relaxed">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="absolute top-4 right-4 text-white/30 hover:text-white">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
