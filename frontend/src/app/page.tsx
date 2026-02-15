'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import SearchBar from '@/components/SearchBar';
import DecryptedText from '@/components/reactbits/DecryptedText';
import CountUp from '@/components/reactbits/CountUp';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import TiltCard from '@/components/reactbits/TiltCard';
import GlowingOrb from '@/components/reactbits/GlowingOrb';
import ShinyText from '@/components/reactbits/ShinyText';

const LaserFlow = dynamic(() => import('@/components/reactbits/LaserFlow'), {
  ssr: false,
});

const exampleQuestions = [
  'Apa syarat pendirian PT?',
  'Bagaimana ketentuan PHK karyawan?',
  'Apa itu RUPS?',
  'Apa hak pekerja menurut UU Cipta Kerja?',
];

const featureCards = [
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: 'AI-Powered Answers',
    description: 'Jawaban akurat didukung oleh model AI yang memahami konteks hukum Indonesia',
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: 'Sumber Terverifikasi',
    description: 'Setiap jawaban dilengkapi kutipan dari undang-undang dan peraturan resmi',
  },
  {
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    title: 'Real-time Streaming',
    description: 'Dapatkan jawaban secara real-time dengan teknologi streaming yang responsif',
  },
];

const stats = [
  { value: 44, suffix: '', label: 'Regulasi Terindeks' },
  { value: 401, suffix: '', label: 'Segmen Dokumen' },
  { qualitative: true, label: 'Setiap jawaban disertai sumber hukum' },
];

const trustBadges = [
  { icon: <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>, label: 'Grounding Verified' },
  { icon: <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>, label: 'Refuses If Unsure' },
  { icon: <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>, label: 'Verified Sources' },
  { icon: <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21V3h18v18H3zm3-3h12M6 6h12" /></svg>, label: 'Indonesian Law' },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

// FAQ Component
function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqs = [
    {
      question: 'Apakah jawaban dari AI ini bisa dipercaya?',
      answer: 'Ya. Setiap jawaban melalui proses verifikasi berlapis: (1) Hybrid search menemukan dokumen hukum yang relevan, (2) CrossEncoder reranking menyaring hasil, (3) AI menghasilkan jawaban dengan kutipan sumber, (4) LLM-as-judge memverifikasi grounding, (5) Sistem menolak menjawab jika kepercayaan rendah (<30%). Semua jawaban dilengkapi sumber pasal dan ayat yang bisa Anda verifikasi sendiri.',
    },
    {
      question: 'Regulasi apa saja yang sudah terindeks?',
      answer: '44 regulasi utama Indonesia sudah terindeks, mencakup UU Cipta Kerja, UU Perseroan Terbatas, UU Ketenagakerjaan, PP terkait perizinan usaha, Perpres OSS, dan regulasi sektoral lainnya. Total 401 segmen dokumen yang telah dipecah dan diindeks untuk pencarian presisi tinggi. Kami terus menambah regulasi baru secara berkala.',
    },
    {
      question: 'Apakah platform ini gratis?',
      answer: 'Ya, 100% gratis dan open source dengan lisensi MIT. Tidak ada biaya tersembunyi, tidak perlu akun premium, dan tidak ada batasan jumlah pertanyaan. Kode sumber terbuka di GitHub sehingga Anda bisa audit sendiri atau bahkan self-host. Kami percaya akses ke informasi hukum harus demokratis dan transparan.',
    },
    {
      question: 'Bagaimana AI menjaga akurasi jawaban?',
      answer: 'Omnibus menggunakan arsitektur RAG (Retrieval-Augmented Generation) dengan safety guardrails: Hybrid search (BM25 + dense vector) untuk recall tinggi, CrossEncoder reranking untuk precision, LLM-as-judge grounding verification untuk validasi post-generation, confidence threshold refusal (<0.30), dan embedding retrieval evaluation menggunakan 58 golden QA pairs. Kami juga menjalankan red-team adversarial testing dengan 25 trick questions untuk menguji failure modes.',
    },
    {
      question: 'Apakah data saya aman?',
      answer: 'Ya. Kami tidak menyimpan log pertanyaan atau data pribadi Anda. Tidak ada tracking, tidak ada cookies, tidak ada autentikasi yang memerlukan email/password. Session chat hanya disimpan sementara di browser Anda dan bisa dihapus kapan saja. Platform ini open-source sehingga Anda bisa verify sendiri tidak ada telemetry atau data collection. Pre-commit hooks mencegah secrets bocor ke repository.',
    },
    {
      question: 'Apa perbedaan mode Sintesis dan Kutipan Langsung?',
      answer: 'Mode Sintesis (default): AI merangkum jawaban dari multiple sources dalam bahasa yang mudah dipahami, dengan footnote citations. Cocok untuk quick understanding. Mode Kutipan Langsung (verbatim): AI menampilkan kutipan pasal/ayat yang relevan secara verbatim tanpa parafrase. Cocok untuk riset formal atau verifikasi presisi tinggi. Kedua mode tetap menyertakan sumber dan grounding score.',
    },
  ];

  return (
    <motion.div
      className="max-w-4xl mx-auto px-4 mt-20"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 3.5, duration: 0.6 }}
    >
      <div className="text-center mb-10">
        <motion.p
          className="text-xs uppercase tracking-widest text-text-muted mb-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 3.6 }}
        >
          Pertanyaan yang Sering Diajukan
        </motion.p>
        <motion.h2
          className="text-3xl font-bold text-text-primary mb-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 3.7 }}
        >
          FAQ
        </motion.h2>
      </div>

      <div className="space-y-3">
        {faqs.map((faq, i) => {
          const isOpen = openIndex === i;
          return (
            <motion.div
              key={i}
              className={`glass-strong rounded-xl border transition-all ${
                isOpen ? 'border-[#AAFF00]/40' : 'border-white/10'
              }`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 3.7 + i * 0.05 }}
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-white/[0.02] transition-colors rounded-xl"
              >
                <span className="text-sm font-semibold text-text-primary pr-4">{faq.question}</span>
                <motion.svg
                  className="w-5 h-5 text-[#AAFF00] flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  animate={{ rotate: isOpen ? 180 : 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </motion.svg>
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
                    className="overflow-hidden"
                  >
                    <div className="px-6 pb-4 pt-2 text-sm text-text-secondary leading-relaxed border-t border-white/5">
                      {faq.answer}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

export default function Home() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const hasRedirected = useRef(false);

  const handleSearch = useCallback(async (query: string) => {
    // Prevent multiple redirects
    if (hasRedirected.current) return;
    hasRedirected.current = true;
    
    // Redirect to chat page with question as query param
    const encodedQuestion = encodeURIComponent(query);
    router.push(`/chat?question=${encodedQuestion}`);
  }, [router]);

  return (
    <div className="min-h-screen">
      {/* Hero + LaserFlow combined zone — beam origin at bottom, search card overlaps it */}
      <div className="relative overflow-hidden" style={{ paddingBottom: '220px' }}>
        {/* LaserFlow — absolute background layer */}
        <div
          className="absolute inset-0 pointer-events-none z-[1]"
          aria-hidden="true"
        >
          <LaserFlow
            horizontalBeamOffset={0.0}
            verticalBeamOffset={-0.32}
            color="#AAFF00"
            verticalSizing={2.0}
            horizontalSizing={0.55}
            wispDensity={1.5}
            wispSpeed={12}
            wispIntensity={5.0}
            flowSpeed={0.35}
            flowStrength={0.25}
            fogIntensity={0.45}
            fogScale={0.3}
            fogFallSpeed={0.6}
            decay={1.1}
            falloffStart={1.2}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
          />
        </div>

        {/* Hero content ON TOP of the beam */}
        <motion.div
          className="relative z-[5] pt-20 pb-6 px-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <div className="max-w-4xl mx-auto text-center">
            {/* AI Badge */}
            <motion.div className="mb-6" variants={itemVariants}>
              <span className="ai-badge">
                <span>✦</span> AI Powered System
              </span>
            </motion.div>

            {/* Hero Title with DecryptedText */}
            <motion.h1
              className="text-hero text-gradient mb-4"
              variants={itemVariants}
            >
              <DecryptedText
                text="OMNIBUS ⚡ Intelligence"
                animateOn="view"
                speed={40}
                sequential
                revealDirection="center"
                className="text-gradient"
                encryptedClassName="text-text-muted"
              />
            </motion.h1>

            <motion.p
              className="text-lg text-text-secondary mb-2"
              variants={itemVariants}
            >
              Sistem Harmonisasi & Intelijen Hukum Terpadu
            </motion.p>
            <motion.p
              className="text-sm text-text-muted mb-8"
              variants={itemVariants}
            >
              Didukung oleh AI untuk membantu Anda memahami peraturan perundang-undangan
            </motion.p>

            {/* Animated Stats */}
            <motion.div
              className="flex items-center justify-center gap-6 sm:gap-10 mb-8"
              variants={itemVariants}
            >
              {stats.map((stat, i) => (
                <div key={stat.label} className="text-center">
                  {'qualitative' in stat ? (
                    // Qualitative stat - show icon + text instead of animated number
                    <div className="flex flex-col items-center">
                      <div className="flex items-center gap-2 mb-1">
                        <svg className="w-6 h-6 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        <span className="text-2xl sm:text-3xl font-bold text-[#AAFF00]">Terverifikasi</span>
                      </div>
                      <div className="text-xs text-text-muted mt-1">{stat.label}</div>
                    </div>
                  ) : (
                    // Quantitative stat - show animated number
                    <div>
                      <div className="text-2xl sm:text-3xl font-bold text-[#AAFF00]">
                        <CountUp
                          to={stat.value}
                          from={0}
                          duration={2}
                          delay={0.3 + i * 0.2}
                          separator=","
                          className="text-2xl sm:text-3xl font-bold"
                        />
                        <span className="text-[#AAFF00]">{stat.suffix}</span>
                      </div>
                      <div className="text-xs text-text-muted mt-1">{stat.label}</div>
                    </div>
                  )}
                </div>
              ))}
            </motion.div>

            {/* Trust Badges */}
            <motion.div
              className="flex items-center justify-center gap-3 sm:gap-5 flex-wrap"
              variants={itemVariants}
            >
              {trustBadges.map((badge) => (
                <div
                  key={badge.label}
                  className="flex items-center gap-1.5 px-3 py-1.5 glass rounded-full text-xs text-text-muted"
                >
                  <span>{badge.icon}</span>
                  <span>{badge.label}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>
      </div>

      {/* Search Section — z-10 to ensure it paints ABOVE the beam convergence point */}
      <motion.div
        className="relative z-[20] max-w-4xl mx-auto px-4"
        style={{ marginTop: '-8rem' }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
      >
          {/* Glow aura BEHIND the card — where beam meets card border */}
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 pointer-events-none z-[-1]"
            style={{
              width: '70%',
              height: '5rem',
              marginTop: '-2rem',
              background: 'radial-gradient(ellipse at center bottom, rgba(170,255,0,0.45) 0%, rgba(170,255,0,0.12) 35%, transparent 65%)',
              filter: 'blur(16px)',
            }}
          />
          {/* Card with green glowing border — brighter at top */}
          <div
            className="relative rounded-2xl p-6"
            style={{
              background: 'rgba(10, 10, 15, 0.92)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '2px solid rgba(170, 255, 0, 0.55)',
              borderTopColor: 'rgba(170, 255, 0, 0.85)',
              boxShadow: '0 0 25px rgba(170,255,0,0.18), 0 0 50px rgba(170,255,0,0.1), inset 0 1px 0 rgba(170,255,0,0.25)',
            }}
          >
              <SearchBar onSearch={handleSearch} isLoading={isLoading} />

              {/* Example Questions */}
              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-sm text-text-muted mb-2.5">Contoh pertanyaan:</p>
                <div className="flex flex-wrap gap-2">
                  {exampleQuestions.map((question, i) => (
                    <motion.button
                      key={question}
                      onClick={() => handleSearch(question)}
                      disabled={isLoading}
                      className="text-sm px-4 py-2 glass rounded-full text-text-secondary hover:text-[#AAFF00] hover:border-[#AAFF00]/30 border border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 + i * 0.05, duration: 0.4 }}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                    >
                      {question}
                    </motion.button>
                  ))}
              </div>
            </div>
          </div>
        </motion.div>

      {/* Feature Cards with TiltCard — Premium 3D effect */}
      <motion.div
        className="max-w-4xl mx-auto px-4 mt-10 relative"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
      >
        {/* Background Glow Orb */}
        <GlowingOrb 
          color="#AAFF00" 
          size={400} 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-20 pointer-events-none"
          duration={10}
        />

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 relative z-10">
          {featureCards.map((card, i) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <TiltCard 
                className="h-full group"
                tiltAmount={12}
                glareEnabled={true}
                glareColor="rgba(170, 255, 0, 0.15)"
              >
                <div className="relative p-6 rounded-xl glass-strong border border-white/10 hover:border-[#AAFF00]/30 transition-all h-full overflow-hidden">
                  {/* Animated gradient border on hover */}
                  <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                    style={{
                      background: 'linear-gradient(135deg, rgba(170,255,0,0.2) 0%, transparent 50%, rgba(170,255,0,0.2) 100%)',
                      backgroundSize: '200% 200%',
                      animation: 'gradient-shift 3s ease infinite'
                    }}
                  />

                  {/* Bottom accent bar */}
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#AAFF00] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                  {/* ShinyText label */}
                  <div className="mb-3">
                    <ShinyText 
                      text={i === 0 ? 'Core Feature' : i === 1 ? 'Fitur Utama' : 'Advanced'}
                      className="text-[10px] uppercase tracking-widest text-[#AAFF00]/70 font-bold"
                    />
                  </div>

                  {/* Large animated icon with glow */}
                  <div className="relative w-16 h-16 mb-5">
                    {/* Glowing background circle */}
                    <motion.div 
                      className="absolute inset-0 rounded-full bg-[#AAFF00]/20 blur-xl"
                      animate={{ 
                        scale: [1, 1.2, 1],
                        opacity: [0.3, 0.5, 0.3]
                      }}
                      transition={{ 
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                    />
                    <div className="relative w-16 h-16 rounded-xl bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] group-hover:bg-[#AAFF00]/20 transition-all">
                      <div className="w-10 h-10">
                        {card.icon}
                      </div>
                    </div>
                  </div>

                  <h3 className="text-text-primary font-bold mb-2 text-lg">{card.title}</h3>
                  <p className="text-sm text-text-muted leading-relaxed">{card.description}</p>
                </div>
              </TiltCard>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Methodology Transparency — Premium Trust Section */}
      <motion.div
        className="max-w-4xl mx-auto px-4 mt-16"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        <div className="text-center mb-8">
          <p className="text-xs uppercase tracking-widest text-text-muted">Mengapa Anda bisa percaya</p>
        </div>

        {/* Trust Badges with Proper SVG Icons */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-12">
          {[
            { 
              label: 'Open Source', 
              desc: 'Kode sumber terbuka di GitHub',
              icon: (
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              )
            },
            { 
              label: 'MIT Licensed', 
              desc: 'Lisensi bebas & transparan',
              icon: (
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              )
            },
            { 
              label: 'Grounding Verified', 
              desc: 'Setiap jawaban diverifikasi AI',
              icon: (
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              )
            },
            { 
              label: '360+ Tests', 
              desc: 'Teruji otomatis secara menyeluruh',
              icon: (
                <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              )
            },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
            >
              <SpotlightCard className="h-full group" spotlightColor="rgba(170, 255, 0, 0.12)">
                <div className="p-5 text-center">
                  <div className="relative w-14 h-14 mx-auto mb-3">
                    {/* Glowing circle background */}
                    <div className="absolute inset-0 rounded-full bg-[#AAFF00]/20 group-hover:bg-[#AAFF00]/30 transition-colors duration-300" />
                    <div className="relative w-14 h-14 rounded-full bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] group-hover:scale-110 transition-transform duration-300">
                      {item.icon}
                    </div>
                  </div>
                  <div className="text-sm font-bold text-text-primary mb-1">{item.label}</div>
                  <div className="text-xs text-text-muted leading-tight">{item.desc}</div>
                </div>
              </SpotlightCard>
            </motion.div>
          ))}
        </div>

        {/* Visual Pipeline — How We Ensure Accuracy */}
        <div className="glass-strong rounded-2xl p-8 max-w-3xl mx-auto relative overflow-hidden">
          {/* Background glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#AAFF00]/5 rounded-full blur-3xl pointer-events-none" />

          <h3 className="text-lg font-bold text-text-primary text-center mb-8 relative z-10">
            Bagaimana Kami Menjaga Akurasi
          </h3>

          {/* Desktop: Horizontal Pipeline */}
          <div className="hidden lg:flex items-center justify-between gap-2 relative">
            {[
              { 
                step: '1', 
                text: 'Pencarian hybrid (BM25 + vektor semantik)',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )
              },
              { 
                step: '2', 
                text: 'CrossEncoder reranking',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                )
              },
              { 
                step: '3', 
                text: 'AI menghasilkan jawaban',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                )
              },
              { 
                step: '4', 
                text: 'LLM-as-judge memverifikasi',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                )
              },
              { 
                step: '5', 
                text: 'Sistem menolak jika tidak yakin',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )
              },
            ].map((item, i, arr) => (
              <motion.div
                key={item.step}
                className="flex items-center gap-2"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.5 }}
              >
                {/* Step Node */}
                <div className="flex flex-col items-center">
                  <motion.div 
                    className="relative w-12 h-12 rounded-full bg-[#AAFF00]/20 border-2 border-[#AAFF00] flex items-center justify-center"
                    animate={{ 
                      boxShadow: ['0 0 0px rgba(170,255,0,0.5)', '0 0 20px rgba(170,255,0,0.8)', '0 0 0px rgba(170,255,0,0.5)']
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      delay: i * 0.4
                    }}
                  >
                    <div className="text-[#AAFF00]">{item.icon}</div>
                    <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#0A0A0F] border border-[#AAFF00] flex items-center justify-center text-[10px] font-bold text-[#AAFF00]">
                      {item.step}
                    </div>
                  </motion.div>
                  <p className="text-[10px] text-text-muted text-center mt-2 max-w-[80px] leading-tight">{item.text}</p>
                </div>

                {/* Connecting Line with Pulse Animation */}
                {i < arr.length - 1 && (
                  <div className="relative w-12 h-0.5 bg-white/10">
                    <motion.div 
                      className="absolute inset-0 h-full bg-gradient-to-r from-[#AAFF00] to-transparent"
                      initial={{ scaleX: 0 }}
                      whileInView={{ scaleX: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.15 + 0.3, duration: 0.5 }}
                      style={{ transformOrigin: 'left' }}
                    />
                    {/* Pulsing dot traveling along line */}
                    <motion.div
                      className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[#AAFF00]"
                      animate={{ 
                        left: ['0%', '100%']
                      }}
                      transition={{ 
                        duration: 1.5,
                        repeat: Infinity,
                        delay: i * 0.3,
                        ease: 'linear'
                      }}
                    />
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          {/* Mobile: Vertical Pipeline */}
          <div className="lg:hidden space-y-4">
            {[
              { 
                step: '1', 
                text: 'Pencarian hybrid (BM25 + vektor semantik) menemukan dokumen hukum yang paling relevan',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )
              },
              { 
                step: '2', 
                text: 'CrossEncoder reranking menyaring hasil agar presisi tinggi',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                )
              },
              { 
                step: '3', 
                text: 'AI menghasilkan jawaban beserta kutipan pasal dan ayat',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                )
              },
              { 
                step: '4', 
                text: 'LLM-as-judge memverifikasi apakah jawaban benar-benar didukung sumber',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                )
              },
              { 
                step: '5', 
                text: 'Jika kepercayaan rendah, sistem menolak menjawab daripada memberikan informasi salah',
                icon: (
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )
              },
            ].map((item, i, arr) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
              >
                <div className="flex items-start gap-4">
                  <motion.div 
                    className="relative flex-shrink-0 w-10 h-10 rounded-full bg-[#AAFF00]/20 border-2 border-[#AAFF00] flex items-center justify-center"
                    animate={{ 
                      boxShadow: ['0 0 0px rgba(170,255,0,0.5)', '0 0 15px rgba(170,255,0,0.8)', '0 0 0px rgba(170,255,0,0.5)']
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      delay: i * 0.4
                    }}
                  >
                    <div className="text-[#AAFF00]">{item.icon}</div>
                    <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#0A0A0F] border border-[#AAFF00] flex items-center justify-center text-[10px] font-bold text-[#AAFF00]">
                      {item.step}
                    </div>
                  </motion.div>
                  <p className="text-sm text-text-secondary leading-relaxed pt-1">{item.text}</p>
                </div>
                {/* Connecting line */}
                {i < arr.length - 1 && (
                  <div className="relative ml-5 h-6 w-0.5 bg-white/10">
                    <motion.div 
                      className="absolute inset-0 w-full bg-gradient-to-b from-[#AAFF00] to-transparent"
                      initial={{ scaleY: 0 }}
                      whileInView={{ scaleY: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.1 + 0.3, duration: 0.4 }}
                      style={{ transformOrigin: 'top' }}
                    />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* ============================================
          1. USE CASES — Siapa yang Menggunakan
          ============================================ */}
      <motion.div
        className="max-w-6xl mx-auto px-4 mt-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.0, duration: 0.6 }}
      >
        <div className="text-center mb-10">
          <motion.p
            className="text-xs uppercase tracking-widest text-text-muted mb-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1 }}
          >
            Siapa yang Menggunakan
          </motion.p>
          <motion.h2
            className="text-3xl font-bold text-text-primary mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
          >
            Dibangun untuk Profesional Hukum
          </motion.h2>
          <motion.p
            className="text-text-secondary max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.3 }}
          >
            Dari firma hukum hingga mahasiswa, Omnibus melayani beragam kebutuhan riset hukum Indonesia
          </motion.p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              icon: (
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              ),
              title: 'Firma Hukum',
              description: 'Riset cepat untuk kasus klien, analisis regulasi terkini, dan verifikasi dasar hukum',
              example: '"Apa ketentuan PHK dalam UU Cipta Kerja?"',
            },
            {
              icon: (
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              ),
              title: 'Startup & UMKM',
              description: 'Compliance check sebelum ekspansi, panduan legalitas bisnis, dan izin usaha',
              example: '"Bagaimana cara mendirikan PT di Jakarta?"',
            },
            {
              icon: (
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              ),
              title: 'Compliance Officers',
              description: 'Audit kepatuhan regulasi, monitoring perubahan UU, dan gap analysis',
              example: '"Regulasi apa yang berlaku untuk fintech?"',
            },
            {
              icon: (
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              ),
              title: 'Mahasiswa Hukum',
              description: 'Belajar regulasi Indonesia, riset tugas kuliah, dan persiapan ujian',
              example: '"Apa perbedaan UU dan PP?"',
            },
          ].map((useCase, i) => (
            <motion.div
              key={useCase.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.3 + i * 0.1, duration: 0.5 }}
            >
              <SpotlightCard className="h-full" spotlightColor="rgba(170, 255, 0, 0.12)">
                <div className="p-6 flex flex-col h-full">
                  <div className="w-14 h-14 rounded-xl bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] mb-4">
                    {useCase.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-text-primary mb-2">{useCase.title}</h3>
                  <p className="text-sm text-text-secondary leading-relaxed mb-4 flex-grow">
                    {useCase.description}
                  </p>
                  <div className="mt-auto pt-3 border-t border-white/5">
                    <p className="text-xs text-[#AAFF00]/70 italic">"{useCase.example}"</p>
                  </div>
                </div>
              </SpotlightCard>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* ============================================
          2. TECH STACK — Arsitektur Platform
          ============================================ */}
      <motion.div
        className="max-w-6xl mx-auto px-4 mt-20 relative"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
      >
        {/* Background Glow Orb */}
        <GlowingOrb 
          color="#AAFF00" 
          size={500} 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-10 pointer-events-none"
          duration={12}
        />

        <div className="text-center mb-10 relative z-10">
          <motion.p
            className="text-xs uppercase tracking-widest text-text-muted mb-2"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            Teknologi Enterprise-Grade
          </motion.p>
          <motion.h2
            className="text-3xl font-bold text-text-primary mb-3"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
          >
            Arsitektur yang Anda Bisa Percaya
          </motion.h2>
          <motion.p
            className="text-text-secondary max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            Stack teknologi produksi dengan AI state-of-the-art dan infrastruktur yang telah teruji
          </motion.p>
        </div>

        {/* Tech Pipeline Visual — Animated Glass Cards */}
        <div className="glass-strong rounded-2xl p-8 mb-8 relative z-10 overflow-hidden">
          <div className="flex items-center justify-between gap-3 overflow-x-auto pb-2">
            {[
              { 
                label: 'Pertanyaan Anda',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )
              },
              { 
                label: 'Hybrid Search', 
                sublabel: 'BM25 + Dense',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )
              },
              { 
                label: 'CrossEncoder Reranking', 
                sublabel: 'Precision++',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                )
              },
              { 
                label: 'NVIDIA NIM AI', 
                sublabel: 'Kimi K2',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                )
              },
              { 
                label: 'Jawaban Terverifikasi',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )
              },
            ].map((step, i, arr) => (
              <motion.div
                key={step.label}
                className="flex items-center gap-3 min-w-fit"
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
              >
                {/* Glass card node */}
                <div className="glass rounded-xl p-4 border border-white/10 hover:border-[#AAFF00]/30 transition-all group">
                  <div className="flex flex-col items-center text-center">
                    <motion.div 
                      className="w-12 h-12 rounded-lg bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] mb-2 group-hover:bg-[#AAFF00]/20 transition-colors"
                      whileHover={{ scale: 1.1 }}
                    >
                      {step.icon}
                    </motion.div>
                    <div className="text-xs font-semibold text-text-primary whitespace-nowrap">{step.label}</div>
                    {step.sublabel && (
                      <div className="text-[10px] text-text-muted whitespace-nowrap mt-0.5">{step.sublabel}</div>
                    )}
                  </div>
                </div>

                {/* Animated connecting arrow */}
                {i < arr.length - 1 && (
                  <div className="relative">
                    {/* Arrow SVG with animated gradient */}
                    <svg className="w-8 h-8 text-[#AAFF00]/50 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                    {/* Traveling pulse */}
                    <motion.div
                      className="absolute top-1/2 left-0 w-2 h-2 rounded-full bg-[#AAFF00]"
                      animate={{
                        x: [0, 32],
                        opacity: [0, 1, 0]
                      }}
                      transition={{
                        duration: 1.5,
                        repeat: Infinity,
                        delay: i * 0.3,
                        ease: 'linear'
                      }}
                    />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Tech Stack Pills — Proper SVG Icons + 2-Row Grid */}
        <div className="relative z-10">
          {/* AI & Search Row */}
          <div className="mb-4">
            <p className="text-xs uppercase tracking-widest text-text-muted text-center mb-3">AI & Search</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { 
                  name: 'NVIDIA NIM', 
                  role: 'Kimi K2 LLM',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  )
                },
                { 
                  name: 'Qdrant', 
                  role: 'Vector Database',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                    </svg>
                  )
                },
                { 
                  name: 'CrossEncoder', 
                  role: 'Reranking',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                    </svg>
                  )
                },
                { 
                  name: 'Hybrid Search', 
                  role: 'BM25 + Dense',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  )
                },
              ].map((tech, i) => (
                <motion.div
                  key={tech.name}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                >
                  <TiltCard className="h-full group" tiltAmount={8} glareEnabled={true}>
                    <div className="glass-strong rounded-xl px-5 py-4 border border-white/10 hover:border-[#AAFF00]/40 transition-all h-full">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] flex-shrink-0 group-hover:bg-[#AAFF00]/20 transition-colors">
                          {tech.icon}
                        </div>
                        <div>
                          <div className="text-sm font-bold text-text-primary">{tech.name}</div>
                          <div className="text-xs text-text-muted">{tech.role}</div>
                        </div>
                      </div>
                    </div>
                  </TiltCard>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Frontend & Dev Row */}
          <div>
            <p className="text-xs uppercase tracking-widest text-text-muted text-center mb-3">Frontend & Dev</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { 
                  name: 'FastAPI', 
                  role: 'Backend API',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                    </svg>
                  )
                },
                { 
                  name: 'Next.js 16', 
                  role: 'Frontend',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                    </svg>
                  )
                },
                { 
                  name: 'Framer Motion', 
                  role: 'Animations',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                    </svg>
                  )
                },
                { 
                  name: 'Tailwind CSS', 
                  role: 'Styling',
                  icon: (
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                    </svg>
                  )
                },
              ].map((tech, i) => (
                <motion.div
                  key={tech.name}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05 + 0.2, duration: 0.4 }}
                >
                  <TiltCard className="h-full group" tiltAmount={8} glareEnabled={true}>
                    <div className="glass-strong rounded-xl px-5 py-4 border border-white/10 hover:border-[#AAFF00]/40 transition-all h-full">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] flex-shrink-0 group-hover:bg-[#AAFF00]/20 transition-colors">
                          {tech.icon}
                        </div>
                        <div>
                          <div className="text-sm font-bold text-text-primary">{tech.name}</div>
                          <div className="text-xs text-text-muted">{tech.role}</div>
                        </div>
                      </div>
                    </div>
                  </TiltCard>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ============================================
          3. PLATFORM METRICS — Social Proof
          ============================================ */}
      <motion.div
        className="max-w-6xl mx-auto px-4 mt-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.2, duration: 0.6 }}
      >
        <div className="glass-strong rounded-2xl p-10 border border-white/10">
          {/* Large Metrics Row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-6 mb-8">
            {[
              { value: 360, suffix: '+', label: 'Tests Passing' },
              { value: 91, suffix: '%', label: 'Code Coverage' },
              { value: 44, suffix: '', label: 'Regulasi' },
              { value: 401, suffix: '', label: 'Segmen Dokumen' },
              { value: 58, suffix: '', label: 'QA Pairs Evaluated' },
              { qualitative: 'MIT', label: 'Open Source' },
            ].map((metric, i) => (
              <motion.div
                key={metric.label}
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 2.3 + i * 0.08 }}
              >
                {'qualitative' in metric ? (
                  <div className="text-3xl font-bold text-[#AAFF00] mb-1">{metric.qualitative}</div>
                ) : (
                  <div className="text-3xl font-bold text-[#AAFF00] mb-1">
                    <CountUp
                      to={metric.value}
                      from={0}
                      duration={2.5}
                      delay={2.4 + i * 0.08}
                      separator=","
                    />
                    <span>{metric.suffix}</span>
                  </div>
                )}
                <div className="text-xs text-text-muted leading-tight">{metric.label}</div>
              </motion.div>
            ))}
          </div>

          {/* Trust Indicators */}
          <motion.div
            className="flex items-center justify-center gap-6 flex-wrap pt-6 border-t border-white/10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2.8 }}
          >
            {[
              { icon: (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              ), label: 'GitHub Open Source' },
              { icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              ), label: 'CI/CD Automated' },
              { icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              ), label: 'Security Audited' },
            ].map((indicator, i) => (
              <motion.div
                key={indicator.label}
                className="flex items-center gap-2 text-text-secondary"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 2.9 + i * 0.1 }}
              >
                <div className="text-[#AAFF00]">{indicator.icon}</div>
                <span className="text-sm font-medium">{indicator.label}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.div>

      {/* ============================================
          4. COMPETITIVE ADVANTAGE — Mengapa Berbeda
          ============================================ */}
      <motion.div
        className="max-w-6xl mx-auto px-4 mt-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 3.0, duration: 0.6 }}
      >
        <div className="text-center mb-10">
          <motion.p
            className="text-xs uppercase tracking-widest text-text-muted mb-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 3.1 }}
          >
            Keunggulan Kompetitif
          </motion.p>
          <motion.h2
            className="text-3xl font-bold text-text-primary mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 3.2 }}
          >
            Mengapa Omnibus Berbeda
          </motion.h2>
          <motion.p
            className="text-text-secondary max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 3.3 }}
          >
            Bukan sekadar chatbot hukum — sistem intelijen legal yang komprehensif
          </motion.p>
        </div>

        <div className="glass-strong rounded-2xl overflow-hidden border border-white/10">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Fitur</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-[#AAFF00]">Omnibus</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-text-muted">Legal Chatbot Generik</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { feature: 'Hybrid Search (BM25 + Dense)', omnibus: true, competitor: false },
                  { feature: 'CrossEncoder Reranking', omnibus: true, competitor: false },
                  { feature: 'Knowledge Graph Visualization', omnibus: true, competitor: false },
                  { feature: 'Grounding Verification (LLM-as-Judge)', omnibus: true, competitor: false },
                  { feature: 'Confidence Threshold Refusal', omnibus: true, competitor: false },
                  { feature: 'Source Citations on Every Answer', omnibus: true, competitor: false },
                  { feature: 'Multi-Turn Chat with Session Memory', omnibus: true, competitor: false },
                  { feature: 'Compliance Dashboard & Analytics', omnibus: true, competitor: false },
                  { feature: 'Open Source & Fully Auditable', omnibus: true, competitor: false },
                ].map((row, i) => (
                  <motion.tr
                    key={row.feature}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 3.4 + i * 0.05 }}
                  >
                    <td className="px-6 py-4 text-sm text-text-secondary">{row.feature}</td>
                    <td className="px-6 py-4 text-center">
                      {row.omnibus ? (
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#AAFF00]/20 text-[#AAFF00]">
                          ✓
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-red-500/20 text-red-400">
                          ✗
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {row.competitor ? (
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-[#AAFF00]/20 text-[#AAFF00]">
                          ✓
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-red-500/20 text-red-400">
                          ✗
                        </span>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>

      {/* ============================================
          5. FAQ — Frequently Asked Questions
          ============================================ */}
      <FAQSection />

      {/* ============================================
          6. CTA BANNER — Call to Action
          ============================================ */}
      <motion.div
        className="max-w-6xl mx-auto px-4 mt-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 3.8, duration: 0.6 }}
      >
        <div className="relative overflow-hidden rounded-2xl p-12 text-center"
          style={{
            background: 'linear-gradient(135deg, rgba(170, 255, 0, 0.15) 0%, rgba(170, 255, 0, 0.05) 100%)',
            border: '2px solid rgba(170, 255, 0, 0.3)',
            boxShadow: '0 0 60px rgba(170, 255, 0, 0.15), inset 0 1px 0 rgba(170, 255, 0, 0.2)',
          }}
        >
          {/* Animated background glow */}
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] opacity-30 blur-3xl pointer-events-none animate-pulse-glow"
            style={{
              background: 'radial-gradient(circle, rgba(170, 255, 0, 0.4) 0%, transparent 70%)',
            }}
          />

          <motion.div
            className="relative z-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 3.9 }}
          >
            <h2 className="text-4xl font-bold text-text-primary mb-4">
              Mulai Eksplorasi Hukum Indonesia
            </h2>
            <p className="text-lg text-text-secondary mb-8 max-w-2xl mx-auto">
              Platform open-source dan gratis. Tidak perlu akun, tidak perlu kartu kredit. 
              Langsung tanya dan dapatkan jawaban hukum yang terverifikasi.
            </p>
            <motion.button
              onClick={() => router.push('/chat')}
              className="inline-flex items-center gap-3 px-8 py-4 bg-[#AAFF00] text-[#0A0A0F] rounded-xl font-bold text-lg hover:bg-[#88CC00] transition-all shadow-lg hover:shadow-xl"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Mulai Sekarang
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </motion.button>
            <p className="text-xs text-text-muted mt-4 flex items-center justify-center gap-1 flex-wrap">
              <svg className="w-3.5 h-3.5 text-[#AAFF00] inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              <span>Powered by NVIDIA NIM</span>
              <span className="mx-1">•</span>
              <svg className="w-3.5 h-3.5 text-[#AAFF00] inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
              <span>Sumber Terverifikasi</span>
              <span className="mx-1">•</span>
              <svg className="w-3.5 h-3.5 text-[#AAFF00] inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21V3h18v18H3zm3-3h12M6 6h12" /></svg>
              <span>100% Fokus Hukum Indonesia</span>
            </p>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
