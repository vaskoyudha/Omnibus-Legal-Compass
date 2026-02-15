'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import SearchBar from '@/components/SearchBar';
import DecryptedText from '@/components/reactbits/DecryptedText';
import CountUp from '@/components/reactbits/CountUp';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import {
  askQuestion,
  AskResponse,
} from '@/lib/api';

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
  { value: 28, suffix: '', label: 'Regulasi Terindeks' },
  { value: 272, suffix: '', label: 'Segmen Dokumen' },
  { qualitative: true, label: 'Setiap jawaban disertai sumber hukum' },
];

const trustBadges = [
  { icon: '🔍', label: 'Grounding Verified' },
  { icon: '🛡️', label: 'Refuses If Unsure' },
  { icon: '✅', label: 'Verified Sources' },
  { icon: '🇮🇩', label: 'Indonesian Law' },
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

      {/* Feature Cards with SpotlightCard */}
      <motion.div
        className="max-w-4xl mx-auto px-4 mt-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {featureCards.map((card, i) => (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + i * 0.1, duration: 0.4 }}
              >
                <SpotlightCard className="h-full" spotlightColor="rgba(170, 255, 0, 0.12)">
                  <div className="p-6">
                    <div className="w-12 h-12 rounded-xl bg-[#AAFF00]/10 flex items-center justify-center text-[#AAFF00] mb-4">
                      {card.icon}
                    </div>
                    <h3 className="text-text-primary font-semibold mb-1.5">{card.title}</h3>
                    <p className="text-sm text-text-muted leading-relaxed">{card.description}</p>
                  </div>
                </SpotlightCard>
              </motion.div>
            ))}
          </div>
        </motion.div>

      {/* Methodology Transparency */}
      <motion.div
        className="max-w-4xl mx-auto px-4 mt-12"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
        >
          <div className="text-center mb-6">
            <p className="text-xs uppercase tracking-widest text-text-muted">Mengapa Anda bisa percaya</p>
          </div>
          <div className="flex items-center justify-center gap-4 sm:gap-8 flex-wrap">
            {[
              { icon: '📂', label: 'Open Source', desc: 'Kode sumber terbuka di GitHub' },
              { icon: '📜', label: 'MIT Licensed', desc: 'Lisensi bebas & transparan' },
              { icon: '🔍', label: 'Grounding Verified', desc: 'Setiap jawaban diverifikasi AI' },
              { icon: '🧪', label: '360+ Tests', desc: 'Teruji otomatis secara menyeluruh' },
            ].map((item) => (
              <div key={item.label} className="flex flex-col items-center text-center max-w-[120px]">
                <span className="text-2xl mb-1">{item.icon}</span>
                <span className="text-sm font-semibold text-text-primary">{item.label}</span>
                <span className="text-xs text-text-muted leading-tight mt-0.5">{item.desc}</span>
              </div>
            ))}
          </div>

          {/* How It Works — replaces fake testimonial */}
          <div className="mt-8 glass-strong rounded-2xl p-6 max-w-2xl mx-auto">
            <h3 className="text-sm font-semibold text-text-primary text-center mb-4">Bagaimana Kami Menjaga Akurasi</h3>
            <div className="space-y-3">
              {[
                { step: '1', text: 'Pencarian hybrid (BM25 + vektor semantik) menemukan dokumen hukum yang paling relevan' },
                { step: '2', text: 'CrossEncoder reranking menyaring hasil agar presisi tinggi' },
                { step: '3', text: 'AI menghasilkan jawaban beserta kutipan pasal dan ayat' },
                { step: '4', text: 'LLM-as-judge memverifikasi apakah jawaban benar-benar didukung sumber' },
                { step: '5', text: 'Jika kepercayaan rendah, sistem menolak menjawab daripada memberikan informasi salah' },
              ].map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#AAFF00]/10 text-[#AAFF00] text-xs font-bold flex items-center justify-center">{item.step}</span>
                  <p className="text-sm text-text-secondary leading-relaxed">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

      {/* Results Section - Redirects to chat */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Empty State */}
        {!isLoading && (
          <motion.div
            className="text-center py-12"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            <div className="w-20 h-20 mx-auto mb-5 glass-strong rounded-2xl flex items-center justify-center shadow-md">
              <svg className="w-10 h-10 text-[#AAFF00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-text-primary mb-2">
              Tanyakan Pertanyaan Hukum Anda
            </h3>
            <p className="text-text-secondary max-w-md mx-auto leading-relaxed">
              Ketik pertanyaan tentang peraturan perundang-undangan Indonesia,
              dan sistem akan mencari jawaban dari dokumen hukum yang relevan.
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
