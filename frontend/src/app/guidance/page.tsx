'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import Link from 'next/link';
import { getGuidance, GuidanceResponse } from '@/lib/api';
import CitationList from '@/components/CitationList';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import LaserFlow from '@/components/reactbits/LaserFlow';
import { toast } from 'sonner';

/* ─── Data ─── */
const BUSINESS_TYPES = [
  { value: 'pt', label: 'Perseroan Terbatas (PT)', short: 'PT', description: 'Badan usaha berbadan hukum dengan modal terbagi atas saham' },
  { value: 'cv', label: 'Commanditaire Vennootschap (CV)', short: 'CV', description: 'Persekutuan dengan sekutu aktif dan pasif' },
  { value: 'firma', label: 'Firma', short: 'Firma', description: 'Persekutuan perdata untuk menjalankan usaha bersama' },
  { value: 'ud', label: 'Usaha Dagang (UD)', short: 'UD', description: 'Usaha perorangan tanpa badan hukum' },
  { value: 'koperasi', label: 'Koperasi', short: 'Koperasi', description: 'Badan usaha beranggotakan orang-orang atau badan hukum' },
  { value: 'yayasan', label: 'Yayasan', short: 'Yayasan', description: 'Badan hukum untuk tujuan sosial, keagamaan, kemanusiaan' },
];

/* ─── Variants ─── */
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

/* ─── Icons (inline SVGs) ─── */
const IconBuilding = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
);
const IconPin = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
);
const IconBriefcase = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
);

export default function GuidancePage() {
  const [businessType, setBusinessType] = useState('');
  const [location, setLocation] = useState('');
  const [industry, setIndustry] = useState('');
  const [result, setResult] = useState<GuidanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!businessType) { toast.error('Pilih jenis badan usaha'); return; }
    setError(null); setResult(null); setIsLoading(true);
    try {
      const response = await getGuidance({ business_type: businessType, location: location || undefined, industry: industry || undefined });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      toast.error('Gagal mendapatkan panduan');
    } finally { setIsLoading(false); }
  }, [businessType, location, industry]);

  const selectedLabel = BUSINESS_TYPES.find(t => t.value === businessType)?.label || businessType;

  return (
    <div className="min-h-screen bg-[#050508] relative overflow-hidden flex flex-col lg:flex-row -mt-16 sm:-mt-20">
      {/* FILM GRAIN */}
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E")`,
          backgroundSize: '200px 200px',
        }}
      />

      {/* ═══ LEFT PANEL — HERO (Sticky on Desktop) ═══ */}
      <div className="relative w-full lg:w-1/2 min-h-[50vh] lg:min-h-screen lg:sticky lg:top-0 lg:left-0 flex flex-col justify-between overflow-hidden border-b lg:border-b-0 lg:border-r border-white/[0.05]">
        {/* LaserFlow Background */}
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
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#050508]/40 to-[#050508] z-10" />
          <div className="absolute inset-0 bg-gradient-to-b from-[#050508]/80 via-transparent to-[#050508]/80 z-10" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#050508_100%)] z-10 opacity-60" />
        </div>

        {/* Content */}
        <div className="relative z-20 flex-1 flex flex-col p-8 md:p-12 lg:p-16 xl:p-24 pt-24 lg:pt-32 justify-between h-full">
          <nav className="flex items-center gap-3 text-xs md:text-sm font-medium text-white/50 mb-12">
            <Link href="/" className="hover:text-[#AAFF00] transition-colors flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              Kembali
            </Link>
          </nav>

          <div className="max-w-xl">
            <motion.h1
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.1 }}
              className="text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tighter text-white mb-6 leading-[1.1]"
            >
              Panduan <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-br from-[#AAFF00] via-white to-white/40">
                Pendirian.
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
              className="text-white/60 text-lg md:text-xl font-light leading-relaxed max-w-md"
            >
              Dapatkan panduan komprehensif mendirikan badan usaha yang disesuaikan dengan peraturan perundang-undangan terkini di Indonesia.
            </motion.p>
          </div>

          {/* Bottom stats */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1, duration: 1 }}
            className="hidden lg:flex items-center gap-8 mt-12 pt-8 border-t border-white/[0.05]"
          >
            <div>
              <p className="text-[#AAFF00] font-mono text-2xl font-bold">6</p>
              <p className="text-xs text-white/40 uppercase tracking-widest font-semibold mt-1">Jenis Badan Usaha</p>
            </div>
            <div className="w-px h-10 bg-white/[0.05]" />
            <div>
              <p className="text-white font-mono text-2xl font-bold">AI-Powered</p>
              <p className="text-xs text-white/40 uppercase tracking-widest font-semibold mt-1">Analisis Regulasi</p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* ═══ RIGHT PANEL — FORM & RESULTS (Scrollable) ═══ */}
      <div className="w-full lg:w-1/2 min-h-screen bg-[#060609] relative z-20 overflow-y-auto custom-scrollbar shadow-[-20px_0_50px_rgba(0,0,0,0.5)]">
        <div className="absolute top-0 left-0 w-full h-[40vh] bg-gradient-to-b from-[#AAFF00]/[0.02] to-transparent pointer-events-none" />
        <div className="absolute top-1/3 right-0 w-1/2 h-[50vh] bg-[radial-gradient(ellipse_at_right,rgba(170,255,0,0.03),transparent_70%)] pointer-events-none" />

        <div className="relative p-5 md:p-8 lg:p-12 xl:p-16 pt-24 lg:pt-32 max-w-2xl mx-auto flex flex-col justify-center min-h-full">
          <div className="w-full relative">

            {/* ─── THE FORM ─── */}
            {!isLoading && !result && (
              <motion.div className="w-full" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>

                {/* Section Header */}
                <div className="mb-8 hidden lg:block">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-[#AAFF00]/10 border border-[#AAFF00]/20 flex items-center justify-center">
                      <svg className="w-4 h-4 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold text-white/90 tracking-tight">Mulai Panduan</h2>
                    </div>
                  </div>
                  <p className="text-white/35 text-sm leading-relaxed pl-11">Pilih entitas hukum dan detail spesifik untuk mendapatkan panduan pendirian yang akurat.</p>
                </div>

                {/* Form Card */}
                <div
                  className="rounded-2xl overflow-hidden"
                  style={{
                    background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    boxShadow: '0 0 0 1px rgba(0,0,0,0.3), 0 8px 40px rgba(0,0,0,0.3)',
                  }}
                >
                  <form onSubmit={handleSubmit}>
                    <div className="p-5 md:p-6">

                      {/* Business Type Label */}
                      <label className="block text-[11px] uppercase tracking-widest text-white/25 font-semibold mb-4">Jenis Badan Usaha</label>

                      {/* Business Type Grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-6">
                        {BUSINESS_TYPES.map((type) => {
                          const isActive = businessType === type.value;
                          return (
                            <motion.label
                              key={type.value}
                              className={`relative flex flex-col items-center text-center p-4 cursor-pointer rounded-xl border transition-all duration-200 ${isActive
                                  ? 'border-[#AAFF00]/40 bg-[#AAFF00]/[0.06]'
                                  : 'border-white/[0.06] bg-black/30 hover:border-white/[0.12] hover:bg-white/[0.02]'
                                }`}
                              whileHover={{ y: -2 }}
                              whileTap={{ scale: 0.97 }}
                            >
                              <input type="radio" name="businessType" value={type.value} checked={isActive} onChange={(e) => setBusinessType(e.target.value)} className="sr-only" />
                              {/* Type initial as icon */}
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black mb-2.5 transition-all ${isActive ? 'bg-[#AAFF00] text-[#0A0A0F] shadow-[0_0_15px_rgba(170,255,0,0.4)]' : 'bg-white/[0.04] text-white/40 border border-white/[0.06]'
                                }`}>
                                {type.short.substring(0, 2)}
                              </div>
                              <span className={`text-[11px] font-bold leading-tight transition-colors ${isActive ? 'text-[#AAFF00]' : 'text-white/60'}`}>
                                {type.short}
                              </span>
                              <span className="text-[9px] text-white/25 mt-1 leading-tight hidden sm:block">
                                {type.description.substring(0, 40)}...
                              </span>
                            </motion.label>
                          );
                        })}
                      </div>

                      {/* Selected Type Details */}
                      <AnimatePresence>
                        {businessType && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                            className="mb-6 overflow-hidden"
                          >
                            <div className="p-4 rounded-xl bg-[#AAFF00]/[0.04] border border-[#AAFF00]/20">
                              <div className="flex items-center gap-2.5 mb-1.5">
                                <div className="w-2 h-2 rounded-full bg-[#AAFF00] shadow-[0_0_6px_rgba(170,255,0,0.6)]" />
                                <span className="text-xs font-bold text-[#AAFF00]">{selectedLabel}</span>
                              </div>
                              <p className="text-[11px] text-white/40 leading-relaxed pl-[18px]">
                                {BUSINESS_TYPES.find(t => t.value === businessType)?.description}
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Optional fields */}
                      <label className="block text-[11px] uppercase tracking-widest text-white/25 font-semibold mb-3">Detail Opsional</label>
                      <div className="grid gap-3 sm:grid-cols-2 mb-6">
                        <div className="relative group">
                          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                            <span className="text-white/20 group-focus-within:text-[#AAFF00] transition-colors"><IconPin /></span>
                          </div>
                          <input
                            type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Lokasi"
                            className="w-full pl-11 pr-4 py-3 bg-black/40 border border-white/[0.06] rounded-xl text-white/90 placeholder:text-white/15 focus:outline-none focus:border-[#AAFF00]/30 focus:ring-1 focus:ring-[#AAFF00]/20 text-sm transition-all"
                          />
                        </div>
                        <div className="relative group">
                          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                            <span className="text-white/20 group-focus-within:text-[#AAFF00] transition-colors"><IconBriefcase /></span>
                          </div>
                          <input
                            type="text" value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Industri"
                            className="w-full pl-11 pr-4 py-3 bg-black/40 border border-white/[0.06] rounded-xl text-white/90 placeholder:text-white/15 focus:outline-none focus:border-[#AAFF00]/30 focus:ring-1 focus:ring-[#AAFF00]/20 text-sm transition-all"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Submit */}
                    <div className="px-5 md:px-6 pb-5 md:pb-6">
                      <motion.button
                        type="submit" disabled={isLoading || !businessType}
                        className="relative w-full py-4 rounded-xl font-semibold text-sm tracking-wide overflow-hidden group disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                        style={{
                          background: 'linear-gradient(135deg, #AAFF00 0%, #8BD800 50%, #AAFF00 100%)',
                          color: '#0A0A0F',
                          boxShadow: '0 2px 8px rgba(170,255,0,0.2), inset 0 1px 0 rgba(255,255,255,0.2)',
                        }}
                        whileHover={{ scale: 1.01, boxShadow: '0 4px 20px rgba(170,255,0,0.35), 0 0 60px rgba(170,255,0,0.08), inset 0 1px 0 rgba(255,255,255,0.25)' }}
                        whileTap={{ scale: 0.99 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                      >
                        <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-[1s] ease-in-out bg-gradient-to-r from-transparent via-white/30 to-transparent" />
                        <span className="relative z-10 flex items-center justify-center gap-2.5">
                          <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                          Dapatkan Panduan AI
                        </span>
                      </motion.button>
                    </div>
                  </form>
                </div>

                {/* Helper text */}
                <div className="flex items-center justify-center gap-4 mt-5">
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    Data aman
                  </span>
                  <span className="w-px h-3 bg-white/[0.06]" />
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    RAG Pipeline
                  </span>
                  <span className="w-px h-3 bg-white/[0.06]" />
                  <span className="flex items-center gap-1.5 text-[11px] text-white/15">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                    Sumber hukum
                  </span>
                </div>
              </motion.div>
            )}

            {/* ─── LOADING STATE ─── */}
            <AnimatePresence>
              {isLoading && (
                <motion.div className="w-full flex items-center justify-center min-h-[400px]" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.05 }}>
                  <div className="text-center w-full max-w-sm relative">
                    <div className="absolute inset-0 bg-[#AAFF00]/5 blur-[100px] rounded-full animate-pulse" />
                    <div className="w-32 h-32 mx-auto relative mb-10">
                      <div className="absolute inset-0 border border-white/5 rounded-full" />
                      <div className="absolute inset-0 border border-[#AAFF00]/30 rounded-full animate-ping" style={{ animationDuration: '3s' }} />
                      <div className="absolute inset-4 border-[2px] border-[#AAFF00]/80 rounded-full border-t-transparent animate-spin" style={{ animationDuration: '1.5s' }} />
                      <div className="absolute inset-8 border-[2px] border-white/30 rounded-full border-b-transparent animate-spin" style={{ animationDuration: '2s', animationDirection: 'reverse' }} />
                      <div className="absolute inset-0 flex items-center justify-center text-[#AAFF00]">
                        <svg className="w-8 h-8 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                      </div>
                    </div>
                    <h3 className="text-2xl font-black mb-3 tracking-wide text-white">Menganalisis Regulasi</h3>
                    <p className="text-white/40 text-sm font-light max-w-xs mx-auto leading-relaxed">AI sedang memetakan persyaratan hukum untuk {selectedLabel}...</p>
                    <div className="w-full mt-12 space-y-4 opacity-40">
                      <div className="h-1 bg-white/20 rounded-full w-full overflow-hidden">
                        <motion.div className="h-full bg-[#AAFF00]" animate={{ x: ['-100%', '200%'] }} transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }} />
                      </div>
                      <div className="h-1 bg-white/20 rounded-full w-3/4 overflow-hidden">
                        <motion.div className="h-full bg-white" animate={{ x: ['-100%', '200%'] }} transition={{ repeat: Infinity, duration: 2, ease: 'linear', delay: 0.2 }} />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ─── RESULTS DASHBOARD ─── */}
            {!isLoading && result && (
              <motion.div className="w-full flex flex-col gap-6 pb-20" variants={containerVariants} initial="hidden" animate="visible">
                {/* Header */}
                <div className="flex justify-between items-end mb-4">
                  <h2 className="text-2xl font-bold text-white tracking-tight">Panduan Pendirian</h2>
                  <button type="button" onClick={() => setResult(null)} className="text-xs font-bold uppercase tracking-widest text-[#AAFF00] hover:text-white transition-colors flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                    Uji Baru
                  </button>
                </div>

                {/* Summary Card */}
                <motion.div variants={itemVariants}>
                  <SpotlightCard className="p-8 border border-white/[0.08] bg-[#0A0A0F]/90 backdrop-blur-xl" spotlightColor="rgba(170, 255, 0, 0.06)">
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#AAFF00] to-[#669900] flex items-center justify-center shadow-[0_0_20px_rgba(170,255,0,0.3)]">
                        <svg className="w-7 h-7 text-[#0A0A0F]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                      </div>
                      <div>
                        <h2 className="text-xl font-black text-white">{selectedLabel}</h2>
                        <div className="flex items-center gap-4 mt-1">
                          {result.total_estimated_time && (
                            <span className="text-xs text-[#AAFF00] font-bold flex items-center gap-1">
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                              {result.total_estimated_time}
                            </span>
                          )}
                          {result.steps && (
                            <span className="text-xs text-white/50 font-bold">{result.steps.length} langkah</span>
                          )}
                          {result.required_permits && (
                            <span className="text-xs text-white/50 font-bold">{result.required_permits.length} izin</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {result.summary && (
                      <div className="pt-6 border-t border-white/[0.05]">
                        <h3 className="text-xs font-bold text-white/50 mb-3 uppercase tracking-widest">Ringkasan Eksekutif</h3>
                        <p className="text-white/80 leading-relaxed font-light text-sm">{result.summary}</p>
                      </div>
                    )}
                  </SpotlightCard>
                </motion.div>

                {/* Required Permits */}
                {result.required_permits && result.required_permits.length > 0 && (
                  <motion.div variants={itemVariants}>
                    <div className="rounded-3xl border border-teal-500/20 overflow-hidden bg-[#0A0A0F]/90 backdrop-blur-xl">
                      <div className="px-6 py-4 border-b border-teal-500/20 bg-teal-500/[0.05] flex justify-between items-center">
                        <h3 className="text-sm font-bold text-teal-100 flex items-center gap-2 uppercase tracking-wide">
                          <svg className="w-4 h-4 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                          Izin Diperlukan
                        </h3>
                        <span className="text-xs font-black text-teal-400 tracking-widest">{result.required_permits.length} ITEM</span>
                      </div>
                      <div className="p-4 flex flex-wrap gap-2">
                        {result.required_permits.map((permit, i) => (
                          <div key={i} className="flex items-center gap-2 px-3.5 py-2 bg-teal-500/[0.06] border border-teal-500/20 rounded-lg hover:border-teal-400/40 transition-colors">
                            <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
                            <span className="text-xs font-semibold text-teal-100">{permit}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Steps */}
                {result.steps && result.steps.length > 0 && (
                  <motion.div variants={itemVariants}>
                    <div className="rounded-3xl border border-[#AAFF00]/20 overflow-hidden bg-[#0A0A0F]/90 backdrop-blur-xl">
                      <div className="px-6 py-4 border-b border-[#AAFF00]/20 bg-[#AAFF00]/[0.05] flex justify-between items-center">
                        <h3 className="text-sm font-bold text-[#AAFF00] flex items-center gap-2 uppercase tracking-wide">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>
                          Prosedur Pendirian
                        </h3>
                        <span className="text-xs font-black text-[#AAFF00] tracking-widest">{result.steps.length} LANGKAH</span>
                      </div>
                      <div className="p-2 divide-y divide-white/[0.05]">
                        {result.steps.map((step, i) => (
                          <motion.div
                            key={i}
                            className="p-4 flex items-start gap-4 hover:bg-[#AAFF00]/[0.02] transition-colors rounded-xl"
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.1 + i * 0.05 }}
                          >
                            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#AAFF00]/10 border border-[#AAFF00]/20 flex items-center justify-center">
                              <span className="text-xs font-black text-[#AAFF00]">{String(i + 1).padStart(2, '0')}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-bold text-white mb-1">
                                {typeof step === 'string' ? step : step.title || `Langkah ${i + 1}`}
                              </h4>
                              {typeof step !== 'string' && step.description && (
                                <p className="text-xs text-white/50 leading-relaxed">{step.description}</p>
                              )}
                              {typeof step !== 'string' && step.estimated_time && (
                                <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded text-[10px] font-bold text-white/40 uppercase tracking-wider">
                                  <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                  {step.estimated_time}
                                </span>
                              )}
                            </div>
                          </motion.div>
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

      {/* Error Toast */}
      <AnimatePresence>
        {error && (
          <motion.div className="fixed bottom-6 right-6 z-50 w-full max-w-sm" initial={{ opacity: 0, y: 20, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}>
            <div className="bg-black/90 backdrop-blur-xl border border-red-500/30 rounded-2xl p-5 flex gap-4 shadow-[0_10px_40px_rgba(239,68,68,0.2)]">
              <svg className="w-6 h-6 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              <div>
                <h4 className="text-sm font-bold text-red-100">Gagal Memproses</h4>
                <p className="text-xs text-red-200/60 mt-1 leading-relaxed">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="absolute top-4 right-4 text-white/30 hover:text-white"><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg></button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
