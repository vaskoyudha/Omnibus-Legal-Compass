'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import SearchBar from '@/components/SearchBar';
import DecryptedText from '@/components/reactbits/DecryptedText';
import CountUp from '@/components/reactbits/CountUp';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import ProviderSelector from '@/components/ProviderSelector';

const LaserFlow = dynamic(() => import('@/components/reactbits/LaserFlow'), {
  ssr: false,
});

import JumbotronBackground from '@/components/JumbotronBackground';

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
  { value: 11974, suffix: '+', label: 'Segmen Dokumen' },
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
      answer: '44 regulasi utama Indonesia sudah terindeks, mencakup UU Cipta Kerja, UU Perseroan Terbatas, UU Ketenagakerjaan, PP terkait perizinan usaha, Perpres OSS, dan regulasi sektoral lainnya. Total lebih dari 11.974 segmen dokumen yang telah dipecah dan diindeks untuk pencarian presisi tinggi. Kami terus menambah regulasi baru secara berkala.',
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
          className="text-xs uppercase tracking-widest text-[#AAFF00]/60 font-mono mb-3"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
        >
          Pertanyaan yang Sering Diajukan
        </motion.p>
        <motion.h2
          className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-4"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
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
              className={`group relative overflow-hidden rounded-2xl transition-all duration-500 border ${isOpen
                ? 'bg-[#0A0A0F]/80 border-[#AAFF00]/30 shadow-[0_0_30px_rgba(170,255,0,0.05)]'
                : 'bg-[#0A0A0F]/40 border-white/5 hover:border-white/10 hover:bg-[#0A0A0F]/60'
                } backdrop-blur-md`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ delay: i * 0.1 }}
            >
              {/* Active left border indicator */}
              <div
                className={`absolute left-0 top-0 bottom-0 w-1 bg-[#AAFF00] transition-transform duration-500 origin-top ${isOpen ? 'scale-y-100' : 'scale-y-0'
                  }`}
              />

              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full px-6 py-5 flex items-center justify-between text-left relative z-10"
              >
                <span className={`text-[15px] md:text-base font-semibold pr-6 transition-colors duration-300 ${isOpen ? 'text-[#AAFF00]' : 'text-white group-hover:text-gray-200'
                  }`}>
                  {faq.question}
                </span>

                {/* Animated Icon Container */}
                <div className={`relative flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 ${isOpen ? 'bg-[#AAFF00]/20 rotate-180' : 'bg-white/5 group-hover:bg-white/10'
                  }`}>
                  <motion.svg
                    className={`w-4 h-4 ${isOpen ? 'text-[#AAFF00]' : 'text-gray-400 group-hover:text-white'}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </motion.svg>
                </div>
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="px-6 pb-6 pt-1">
                      <p className="text-[15px] text-gray-400 leading-relaxed font-light">
                        {faq.answer}
                      </p>
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
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');

  const handleSearch = useCallback(async (query: string) => {
    // Prevent multiple redirects
    if (hasRedirected.current) return;
    hasRedirected.current = true;

    // Redirect to chat page with question as query param
    const encodedQuestion = encodeURIComponent(query);
    router.push(`/chat?question=${encodedQuestion}`);
  }, [router]);

  return (
    <div className="min-h-screen relative bg-[#0A0A0F] -mt-16 sm:-mt-20">
      {/* Beams background — ONLY covers hero jumbotron (first viewport) */}
      <div
        className="absolute top-0 left-0 w-full pointer-events-none z-[0] overflow-hidden"
        style={{ height: '120vh' }}
        aria-hidden="true"
      >
        <JumbotronBackground />
        {/* Bottom fade — large vignette for smooth blend into page */}
        <div
          className="absolute bottom-0 left-0 w-full pointer-events-none"
          style={{
            height: '40%',
            background: 'linear-gradient(to bottom, transparent 0%, transparent 50%, rgba(10,10,15,0.3) 65%, rgba(10,10,15,0.7) 80%, #0A0A0F 100%)',
          }}
        />
      </div>

      {/* Full-page dark ambient gradients — visible atmospheric depth throughout */}
      <div className="absolute inset-0 pointer-events-none z-[0]" aria-hidden="true">
        {/* Transition from hero into content — dark gradient with green tint */}
        <div className="absolute w-full" style={{ top: '110vh', height: '100vh', background: 'radial-gradient(ellipse 100% 60% at 50% 0%, rgba(18,20,26,0.95) 0%, rgba(10,10,15,0) 70%)' }} />
        <div className="absolute w-full" style={{ top: '110vh', height: '100vh', background: 'radial-gradient(ellipse 60% 40% at 30% 40%, rgba(170,255,0,0.05) 0%, transparent 70%)' }} />
        {/* Mid-page — dark base with teal undertone */}
        <div className="absolute w-full" style={{ top: '160vh', height: '100vh', background: 'radial-gradient(ellipse 100% 60% at 50% 50%, rgba(13,16,21,0.9) 0%, rgba(10,10,15,0) 70%)' }} />
        <div className="absolute w-full" style={{ top: '180vh', height: '80vh', background: 'radial-gradient(ellipse 50% 40% at 70% 50%, rgba(0,200,180,0.04) 0%, transparent 70%)' }} />
        {/* Lower sections — alternating subtle glows */}
        <div className="absolute w-full" style={{ top: '260vh', height: '100vh', background: 'radial-gradient(ellipse 70% 50% at 35% 50%, rgba(170,255,0,0.04) 0%, transparent 70%)' }} />
        <div className="absolute w-full" style={{ top: '340vh', height: '100vh', background: 'radial-gradient(ellipse 100% 60% at 50% 50%, rgba(15,17,23,0.85) 0%, rgba(10,10,15,0) 70%)' }} />
        <div className="absolute w-full" style={{ top: '360vh', height: '80vh', background: 'radial-gradient(ellipse 50% 40% at 65% 50%, rgba(0,200,180,0.035) 0%, transparent 70%)' }} />
        {/* Bottom of page */}
        <div className="absolute w-full" style={{ top: '440vh', height: '100vh', background: 'radial-gradient(ellipse 60% 50% at 40% 50%, rgba(170,255,0,0.03) 0%, transparent 70%)' }} />
      </div>

      {/* All content — above the nebula background */}
      <div className="relative z-[1]">
        {/* Hero + LaserFlow combined zone — beam origin at bottom, search card overlaps it */}
        <div className="relative overflow-hidden" style={{ paddingBottom: '200px' }}>

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
            className="relative z-[5] pt-32 sm:pt-40 pb-6 px-4"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            <div className="max-w-4xl mx-auto text-center">
              {/* Hero Title with DecryptedText */}
              <motion.h1
                className="text-hero text-gradient mb-6 text-5xl sm:text-7xl md:text-8xl lg:text-9xl tracking-tighter"
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
                className="text-lg text-white mb-2"
                variants={itemVariants}
              >
                Sistem Harmonisasi & Intelijen Hukum Terpadu
              </motion.p>
              <motion.p
                className="text-sm text-gray-200 mb-8"
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
                        <div className="text-xs text-gray-300 mt-1">{stat.label}</div>
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
                        <div className="text-xs text-gray-300 mt-1">{stat.label}</div>
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
                    className="flex items-center gap-1.5 px-3 py-1.5 glass rounded-full text-xs text-[#AAFF00]"
                  >
                    <span>{badge.icon}</span>
                    <span>{badge.label}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </motion.div>
        </div>

        {/* Chat Section — z-10 to ensure it paints ABOVE the beam convergence point */}
        <motion.div
          className="relative z-[20] mx-auto px-3 sm:px-4 lg:px-6"
          style={{ marginTop: '-8rem' }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
        >
          {/* Glow aura BEHIND the card — where beam meets card border */}
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 pointer-events-none z-[-1]"
            style={{
              width: '80%',
              height: '6rem',
              marginTop: '-2.5rem',
              background: 'radial-gradient(ellipse at center bottom, rgba(170,255,0,0.45) 0%, rgba(170,255,0,0.12) 35%, transparent 65%)',
              filter: 'blur(20px)',
            }}
          />
          {/* Card with green glowing border — chatbot style */}
          <div
            className="relative rounded-2xl overflow-hidden flex"
            style={{
              background: 'rgba(10, 10, 15, 0.92)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '1.5px solid rgba(170, 255, 0, 0.4)',
              borderTopColor: 'rgba(170, 255, 0, 0.7)',
              boxShadow: '0 0 30px rgba(170,255,0,0.15), 0 0 60px rgba(170,255,0,0.08), inset 0 1px 0 rgba(170,255,0,0.2)',
              minHeight: '420px',
            }}
          >
            {/* ═══ Sidebar ═══ */}
            <div
              className="hidden md:flex flex-col w-[260px] flex-shrink-0 border-r border-white/[0.06]"
              style={{ background: 'rgba(255, 255, 255, 0.015)' }}
            >
              {/* Sidebar Header — New Chat */}
              <div className="px-4 py-4">
                <button
                  className="w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm font-medium text-white transition-all hover:bg-white/[0.06]"
                  style={{
                    background: 'rgba(170, 255, 0, 0.08)',
                    border: '1px solid rgba(170, 255, 0, 0.2)',
                  }}
                >
                  <svg className="w-4 h-4 text-[#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  Chat Baru
                </button>
              </div>

              {/* Chat History */}
              <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-4">
                {/* Today */}
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-600 font-medium px-2 mb-1.5">Hari ini</p>
                  <div className="space-y-0.5">
                    {[
                      'Syarat pendirian PT baru',
                      'Ketentuan PHK karyawan',
                    ].map((title, i) => (
                      <div
                        key={i}
                        className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] cursor-pointer transition-all ${i === 0 ? 'bg-white/[0.05] text-white' : 'text-gray-500 hover:bg-white/[0.03] hover:text-gray-300'}`}
                      >
                        <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                        <span className="truncate">{title}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Yesterday */}
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-600 font-medium px-2 mb-1.5">Kemarin</p>
                  <div className="space-y-0.5">
                    {[
                      'Hak pekerja UU Cipta Kerja',
                      'Prosedur RUPS tahunan',
                      'Izin usaha OSS-RBA',
                    ].map((title, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-gray-500 hover:bg-white/[0.03] hover:text-gray-300 cursor-pointer transition-all"
                      >
                        <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                        <span className="truncate">{title}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 7 days */}
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-600 font-medium px-2 mb-1.5">7 hari lalu</p>
                  <div className="space-y-0.5">
                    {[
                      'Perpajakan UMKM',
                      'Perlindungan konsumen',
                    ].map((title, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-gray-500 hover:bg-white/[0.03] hover:text-gray-300 cursor-pointer transition-all"
                      >
                        <svg className="w-3.5 h-3.5 flex-shrink-0 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                        </svg>
                        <span className="truncate">{title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Sidebar Footer */}
              <div className="px-4 py-3 border-t border-white/[0.04]">
                <div className="flex items-center gap-2.5 px-2">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold text-[#0A0A0F]"
                    style={{ background: 'linear-gradient(135deg, #AAFF00, #88CC00)' }}
                  >
                    U
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] text-gray-400 truncate">Pengguna</p>
                    <p className="text-[10px] text-gray-600 truncate">Free Plan</p>
                  </div>
                  <svg className="w-4 h-4 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM12.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM18.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
                  </svg>
                </div>
              </div>
            </div>

            {/* ═══ Main Chat Area ═══ */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Chat Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]"
                style={{
                  background: 'linear-gradient(180deg, rgba(170, 255, 0, 0.04) 0%, transparent 100%)',
                }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{
                      background: 'linear-gradient(135deg, rgba(170, 255, 0, 0.2), rgba(170, 255, 0, 0.05))',
                      border: '1px solid rgba(170, 255, 0, 0.25)',
                    }}
                  >
                    <svg className="w-4 h-4 text-[#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">Omnibus AI Assistant</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#AAFF00] animate-pulse-online" />
                      <span className="text-[11px] text-gray-500">Online • Siap menjawab</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ProviderSelector
                    onProviderChange={(provider, model) => {
                      setSelectedProvider(provider);
                      setSelectedModel(model);
                    }}
                  />
                </div>
              </div>

              {/* Chat Body */}
              <div className="flex-1 px-6 py-5">
                {/* Welcome message bubble */}
                <div className="flex items-start gap-3 mb-6">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{
                      background: 'linear-gradient(135deg, rgba(170, 255, 0, 0.15), rgba(170, 255, 0, 0.03))',
                      border: '1px solid rgba(170, 255, 0, 0.2)',
                    }}
                  >
                    <svg className="w-3.5 h-3.5 text-[#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-[13px] text-gray-400 leading-relaxed">
                      Hai! Saya asisten hukum AI Omnibus. Tanyakan apa saja tentang peraturan perundang-undangan Indonesia — saya akan menjawab dengan kutipan sumber resmi.
                    </p>
                  </div>
                </div>

                {/* Search Input */}
                <SearchBar onSearch={handleSearch} isLoading={isLoading} />
              </div>

              {/* Example Questions — Footer */}
              <div className="px-6 py-4 border-t border-white/[0.04]"
                style={{
                  background: 'rgba(255, 255, 255, 0.015)',
                }}
              >
                <p className="text-[11px] uppercase tracking-wider text-gray-600 mb-3 font-medium">Coba tanyakan</p>
                <div className="flex flex-wrap gap-2">
                  {exampleQuestions.map((question, i) => (
                    <motion.button
                      key={question}
                      onClick={() => handleSearch(question)}
                      disabled={isLoading}
                      className="group text-[13px] px-4 py-2 rounded-xl text-gray-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                      }}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 + i * 0.05, duration: 0.4 }}
                      whileHover={{
                        scale: 1.02,
                        borderColor: 'rgba(170, 255, 0, 0.3)',
                        color: '#AAFF00',
                        background: 'rgba(170, 255, 0, 0.05)',
                      }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <svg className="w-3.5 h-3.5 opacity-40 group-hover:opacity-80 transition-opacity" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                      </svg>
                      {question}
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── Visual Transition: Search → Features ── */}
        <div className="relative max-w-5xl mx-auto px-4 mt-16 mb-8">
          {/* Fading center line */}
          <motion.div
            className="mx-auto h-px w-full max-w-xs"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(170,255,0,0.3), transparent)',
            }}
            initial={{ scaleX: 0, opacity: 0 }}
            whileInView={{ scaleX: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
          {/* Vertical drop line */}
          <motion.div
            className="mx-auto w-px h-10"
            style={{
              background: 'linear-gradient(180deg, rgba(170,255,0,0.3), transparent)',
            }}
            initial={{ scaleY: 0, opacity: 0 }}
            whileInView={{ scaleY: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
          />
          {/* Glowing dot at intersection */}
          <motion.div
            className="mx-auto w-2 h-2 rounded-full bg-[#AAFF00]"
            style={{ boxShadow: '0 0 12px rgba(170,255,0,0.6), 0 0 30px rgba(170,255,0,0.2)' }}
            initial={{ scale: 0, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6 }}
          />
        </div>

        {/* Feature Cards — Editorial Layout with SpotlightCards */}
        <motion.div
          className="max-w-5xl mx-auto px-4 mt-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          {/* Section Heading */}
          <div className="text-center mb-14">
            <motion.p
              className="text-xs uppercase tracking-widest text-[#AAFF00]/60 font-mono mb-3"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              Fitur Utama
            </motion.p>
            <motion.h2
              className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.05 }}
            >
              <span className="text-white">Built for </span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#AAFF00] to-white drop-shadow-[0_0_30px_rgba(170,255,0,0.3)]">
                Legal Precision
              </span>
            </motion.h2>
            <motion.p
              className="text-base text-gray-400 mt-3 max-w-lg mx-auto"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              Platform intelijen hukum dengan fitur yang dirancang untuk akurasi dan kecepatan
            </motion.p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {featureCards.map((card, i) => (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{
                  duration: 0.6,
                  ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
                  delay: i * 0.12
                }}
              >
                <SpotlightCard
                  className="h-full group"
                  spotlightColor="rgba(170, 255, 0, 0.15)"
                >
                  <div className="relative p-8 h-full rounded-2xl flex flex-col overflow-hidden transition-all duration-500 bg-[#0A0A0F]/60 hover:bg-[#0A0A0F]/40 border border-white/[0.04] hover:border-white/[0.1] backdrop-blur-md z-10 w-full">

                    {/* Top ambient glow */}
                    <div
                      className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-[#AAFF00]/10 blur-[50px] opacity-10 group-hover:opacity-40 transition-opacity duration-700 pointer-events-none"
                    />

                    <div className="flex items-center justify-between mb-8">
                      {/* Step number */}
                      <span className="text-xs font-mono text-white/20 uppercase tracking-widest font-bold">
                        0{i + 1}
                      </span>
                      {/* Top right subtle line */}
                      <div className="h-px w-12 bg-gradient-to-r from-transparent to-white/10 group-hover:to-[#AAFF00]/40 transition-colors duration-500" />
                    </div>

                    {/* Icon Container with glow */}
                    <div className="relative w-14 h-14 rounded-2xl flex items-center justify-center mb-6 shadow-xl flex-shrink-0 bg-gradient-to-br from-white/[0.05] to-[#AAFF00]/10 border border-[#AAFF00]/20 text-[#AAFF00]">
                      <div className="absolute inset-0 blur-md opacity-40 group-hover:opacity-70 transition-opacity duration-500 bg-[#AAFF00]/30 rounded-2xl" />
                      <motion.div
                        className="relative z-10 text-current"
                        whileHover={{ scale: 1.15, rotate: -5 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 15 }}
                      >
                        {card.icon}
                      </motion.div>
                    </div>

                    {/* Title */}
                    <h3 className="text-xl md:text-2xl font-bold text-white mb-3 tracking-tight transition-all duration-500">
                      {card.title}
                    </h3>

                    {/* Description */}
                    <p className="text-[15px] text-gray-400 leading-relaxed font-light">
                      {card.description}
                    </p>

                  </div>
                </SpotlightCard>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Trust Badges — Horizontal Scrolling Marquee */}
        <motion.div
          className="max-w-full mx-auto mt-16 border-y border-white/5 relative overflow-hidden"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          {/* Edge fade gradients */}
          <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-[#0A0A0F] to-transparent z-10 pointer-events-none" />
          <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-[#0A0A0F] to-transparent z-10 pointer-events-none" />

          <div className="py-8">
            <motion.div
              className="flex items-center gap-8 whitespace-nowrap"
              animate={{ x: [0, -1200] }}
              transition={{
                duration: 30,
                repeat: Infinity,
                ease: "linear"
              }}
            >
              {/* Duplicate array for seamless infinite scroll */}
              {[...Array(2)].map((_, groupIndex) => (
                <div key={groupIndex} className="flex items-center gap-8">
                  {[
                    {
                      label: 'Open Source',
                      desc: 'Kode sumber terbuka di GitHub',
                      icon: (
                        <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                        </svg>
                      )
                    },
                    {
                      label: 'MIT Licensed',
                      desc: 'Lisensi bebas & transparan',
                      icon: (
                        <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      )
                    },
                    {
                      label: 'Grounding Verified',
                      desc: 'Setiap jawaban diverifikasi AI',
                      icon: (
                        <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                      )
                    },
                    {
                      label: '459+ Tests',
                      desc: 'Teruji otomatis secara menyeluruh',
                      icon: (
                        <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                        </svg>
                      )
                    },
                  ].map((item, i) => (
                    <div key={`${groupIndex}-${i}`}>
                      <div className="inline-flex items-center gap-4">
                        {/* Icon */}
                        <div className="text-white/40">
                          {item.icon}
                        </div>

                        {/* Label + description */}
                        <div className="flex flex-col">
                          <span className="text-4xl font-bold uppercase tracking-tighter text-white">
                            {item.label}
                          </span>
                          <span className="text-sm font-mono text-gray-500 mt-1">
                            {item.desc}
                          </span>
                        </div>
                      </div>

                      {/* Dot divider */}
                      <span className="inline-block mx-8 text-white/20 text-2xl">•</span>
                    </div>
                  ))}
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>

        {/* Accuracy Pipeline — Immersive Vertical Flow */}
        <motion.div
          className="relative max-w-5xl mx-auto px-4 mt-24 mb-8"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          {/* Section Heading */}
          <div className="text-center mb-14">
            <motion.p
              className="text-xs uppercase tracking-widest text-[#AAFF00]/60 font-mono mb-3"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              5-Stage Pipeline
            </motion.p>
            <motion.h2
              className="text-4xl md:text-5xl font-bold tracking-tight"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.05 }}
            >
              <span className="text-white">Bagaimana Kami Menjaga </span>
              <span className="text-[#AAFF00]">Akurasi</span>
            </motion.h2>
            <motion.p
              className="text-base text-gray-400 mt-3 max-w-lg mx-auto"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              Setiap jawaban melewati 5 tahap verifikasi sebelum sampai ke Anda
            </motion.p>
          </div>

          {/* Pipeline Steps */}
          <div className="relative">
            {/* Central animated connecting line (desktop) - Upgraded to Neon Pulse Track */}
            <div className="hidden md:block absolute left-1/2 top-0 bottom-0 -translate-x-1/2 w-[2px] overflow-hidden rounded-full shadow-[0_0_15px_rgba(170,255,0,0.5)]">
              <div className="h-full w-full bg-gradient-to-b from-[#AAFF00]/60 via-cyan-400/50 to-purple-500/40" />
              {/* Traveling neon pulse */}
              <motion.div
                className="absolute left-1/2 -translate-x-1/2 w-[4px] h-32 rounded-full"
                style={{
                  background: 'linear-gradient(to bottom, transparent, #AAFF00, #AAFF00, transparent)',
                  boxShadow: '0 0 20px #AAFF00, 0 0 40px #AAFF00'
                }}
                animate={{ top: ['-10%', '110%'] }}
                transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
              />
            </div>
            {/* Mobile connecting line */}
            <div className="md:hidden absolute left-6 top-0 bottom-0 w-[2px] bg-gradient-to-b from-[#AAFF00]/50 via-cyan-400/30 to-purple-500/20 shadow-[0_0_10px_rgba(170,255,0,0.3)]" />

            {[
              {
                step: '01',
                title: 'Pencarian Hybrid',
                subtitle: 'BM25 + Vektor Semantik',
                description: 'Menemukan dokumen hukum yang paling relevan menggunakan kombinasi pencarian keyword dan pemahaman makna.',
                accent: '#AAFF00',
                accentBg: 'rgba(170, 255, 0, 0.08)',
                accentBorder: 'rgba(170, 255, 0, 0.25)',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                ),
                metric: { value: '2x', label: 'Metode Pencarian' },
              },
              {
                step: '02',
                title: 'CrossEncoder Reranking',
                subtitle: 'Presisi Tinggi',
                description: 'Menyaring dan mengurutkan ulang hasil pencarian dengan model AI khusus untuk memastikan relevansi maksimal.',
                accent: '#00D4FF',
                accentBg: 'rgba(0, 212, 255, 0.08)',
                accentBorder: 'rgba(0, 212, 255, 0.25)',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                ),
                metric: { value: 'Top-K', label: 'Hasil Tersaring' },
              },
              {
                step: '03',
                title: 'AI Menghasilkan Jawaban',
                subtitle: 'Dengan Kutipan Sumber',
                description: 'Model bahasa besar menganalisis konteks hukum dan menghasilkan jawaban beserta kutipan pasal dan ayat yang spesifik.',
                accent: '#A855F7',
                accentBg: 'rgba(168, 85, 247, 0.08)',
                accentBorder: 'rgba(168, 85, 247, 0.25)',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                ),
                metric: { value: '100%', label: 'Kutipan Sumber' },
              },
              {
                step: '04',
                title: 'LLM-as-Judge Verifikasi',
                subtitle: 'Grounding Check',
                description: 'Jawaban diperiksa ulang oleh model AI kedua — memastikan setiap klaim benar-benar didukung oleh sumber hukum.',
                accent: '#F59E0B',
                accentBg: 'rgba(245, 158, 11, 0.08)',
                accentBorder: 'rgba(245, 158, 11, 0.25)',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                ),
                metric: { value: '0-1', label: 'Grounding Score' },
              },
              {
                step: '05',
                title: 'Menolak Jika Tidak Yakin',
                subtitle: 'Confidence Threshold',
                description: 'Sistem memilih untuk tidak menjawab daripada memberikan informasi yang salah. Threshold konfidiensi < 0.30 = penolakan.',
                accent: '#EF4444',
                accentBg: 'rgba(239, 68, 68, 0.08)',
                accentBorder: 'rgba(239, 68, 68, 0.25)',
                icon: (
                  <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                ),
                metric: { value: '<0.3', label: 'Auto Reject' },
              },
            ].map((item, i) => {
              const isEven = i % 2 === 0;
              return (
                <motion.div
                  key={item.step}
                  className="relative mb-8 last:mb-0"
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ delay: i * 0.1, duration: 0.4 }}
                >
                  {/* Desktop: alternating left/right layout */}
                  <div className={`hidden md:grid md:grid-cols-[1fr_60px_1fr] items-center gap-0`}>
                    {/* Left content (even steps) or empty */}
                    <div className={isEven ? 'order-1' : 'order-3'}>
                      <motion.div
                        initial={{ opacity: 0, x: isEven ? -60 : 60, scale: 0.95 }}
                        whileInView={{ opacity: 1, x: 0, scale: 1 }}
                        viewport={{ once: true, margin: '-60px' }}
                        transition={{
                          delay: i * 0.15 + 0.1,
                          duration: 0.7,
                          ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
                        }}
                      >
                        <SpotlightCard className="h-full group" spotlightColor={item.accentBg}>
                          <div
                            className="relative p-7 rounded-2xl border transition-all duration-500 overflow-hidden break-inside-avoid"
                            style={{
                              background: 'rgba(10,10,15,0.85)',
                              backdropFilter: 'blur(24px)',
                              WebkitBackdropFilter: 'blur(24px)',
                              borderColor: 'rgba(255,255,255,0.06)',
                            }}
                          >
                            {/* Top ambient glow */}
                            <div
                              className="absolute -top-12 -right-12 w-48 h-48 rounded-full blur-[60px] opacity-10 group-hover:opacity-30 transition-opacity duration-700 pointer-events-none"
                              style={{ background: item.accent }}
                            />

                            {/* Top accent line */}
                            <motion.div
                              className="absolute top-0 left-6 right-6 h-[2px]"
                              style={{ background: `linear-gradient(to right, transparent, ${item.accent}, transparent)` }}
                              initial={{ scaleX: 0, opacity: 0 }}
                              whileInView={{ scaleX: 1, opacity: 0.8 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.4, duration: 0.8, ease: 'easeOut' }}
                            />

                            {/* Step label + Icon row */}
                            <motion.div
                              className="flex items-center gap-4 mb-4"
                              initial={{ opacity: 0, y: 10 }}
                              whileInView={{ opacity: 1, y: 0 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.2, duration: 0.5 }}
                            >
                              <motion.div
                                className="relative w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg"
                                style={{
                                  background: `linear-gradient(135deg, ${item.accent}20, rgba(0,0,0,0.4))`,
                                  border: `1px solid ${item.accentBorder}`,
                                  color: item.accent,
                                }}
                                initial={{ scale: 0, rotate: -20 }}
                                whileInView={{ scale: 1, rotate: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.15 + 0.3, type: 'spring', stiffness: 250, damping: 18 }}
                                whileHover={{ scale: 1.15, rotate: 5, boxShadow: `0 0 20px ${item.accentBg}` }}
                              >
                                <div className="absolute inset-0 blur-md opacity-50 group-hover:opacity-80 transition-opacity duration-500 rounded-xl" style={{ background: item.accentBg }} />
                                <div className="relative z-10 text-current">{item.icon}</div>
                              </motion.div>
                              <span className="text-xs font-mono tracking-widest uppercase opacity-70 font-semibold" style={{ color: item.accent }}>
                                Step {item.step}
                              </span>
                            </motion.div>

                            {/* Title */}
                            <motion.h4
                              className="text-xl font-bold text-white mb-1 group-hover:text-white transition-colors"
                              initial={{ opacity: 0, y: 8 }}
                              whileInView={{ opacity: 1, y: 0 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.3, duration: 0.5 }}
                            >
                              {item.title}
                            </motion.h4>
                            <motion.p
                              className="text-sm font-semibold mb-3 tracking-wide"
                              style={{ color: item.accent, opacity: 0.9 }}
                              initial={{ opacity: 0 }}
                              whileInView={{ opacity: 1 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.35, duration: 0.5 }}
                            >
                              {item.subtitle}
                            </motion.p>
                            <motion.p
                              className="text-[15px] text-gray-400 leading-relaxed mb-5"
                              initial={{ opacity: 0, y: 6 }}
                              whileInView={{ opacity: 1, y: 0 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.4, duration: 0.5 }}
                            >
                              {item.description}
                            </motion.p>

                            {/* Metric badge */}
                            <motion.div
                              className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-sm font-mono shadow-inner"
                              style={{
                                background: `linear-gradient(135deg, ${item.accentBg}, rgba(0,0,0,0.5))`,
                                border: `1px solid ${item.accentBorder}`,
                                color: item.accent,
                              }}
                              initial={{ opacity: 0, scale: 0.8, y: 8 }}
                              whileInView={{ opacity: 1, scale: 1, y: 0 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.5, type: 'spring', stiffness: 300, damping: 20 }}
                            >
                              <span className="text-base font-bold drop-shadow-[0_0_8px_currentColor]">{item.metric.value}</span>
                              <span className="opacity-70 text-gray-300 font-sans tracking-wide">{item.metric.label}</span>
                            </motion.div>

                            {/* Connector arrow pointing to center */}
                            <motion.div
                              className={`absolute top-1/2 -translate-y-1/2 w-8 h-[2px] ${isEven ? '-right-8' : '-left-8'}`}
                              style={{ background: `linear-gradient(to ${isEven ? 'right' : 'left'}, ${item.accent}, transparent)` }}
                              initial={{ scaleX: 0, opacity: 0 }}
                              whileInView={{ scaleX: 1, opacity: 0.6 }}
                              viewport={{ once: true }}
                              transition={{ delay: i * 0.15 + 0.5, duration: 0.5 }}
                            />
                          </div>
                        </SpotlightCard>
                      </motion.div>
                    </div>

                    {/* Center node */}
                    <div className="order-2 flex flex-col items-center justify-center relative z-10">
                      <motion.div
                        className="relative w-14 h-14 rounded-full flex items-center justify-center font-mono text-base font-bold shadow-xl backdrop-blur-md"
                        style={{
                          background: `radial-gradient(circle at center, ${item.accentBg} 0%, rgba(10,10,15,0.9) 70%)`,
                          border: `2px solid ${item.accent}`,
                          color: item.accent,
                          boxShadow: `0 0 20px ${item.accentBg}, inset 0 0 10px ${item.accentBg}`,
                        }}
                        initial={{ scale: 0, opacity: 0 }}
                        whileInView={{ scale: 1, opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: i * 0.15 + 0.15, type: 'spring', stiffness: 300, damping: 20 }}
                        whileHover={{ scale: 1.15, boxShadow: `0 0 30px ${item.accentBg}, inset 0 0 15px ${item.accentBg}` }}
                      >
                        {item.step}
                        {/* Outer Pulse ring */}
                        <motion.div
                          className="absolute inset-0 rounded-full"
                          style={{ border: `1px solid ${item.accent}` }}
                          animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
                          transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.2 }}
                        />
                        {/* Inner Glowing core */}
                        <div className="absolute inset-0 rounded-full blur-[8px] opacity-40 mix-blend-screen pointer-events-none" style={{ background: item.accent }} />
                      </motion.div>
                    </div>

                    {/* Right content (odd steps) or empty */}
                    <div className={isEven ? 'order-3' : 'order-1'} />
                  </div>

                  {/* Mobile: stacked layout with left line */}
                  <div className="md:hidden relative pl-16">
                    {/* Step node on the line */}
                    <motion.div
                      className="absolute left-0 top-6 -translate-y-1/2 w-12 h-12 rounded-full flex items-center justify-center font-mono text-sm font-bold z-20 shadow-lg"
                      style={{
                        background: `radial-gradient(circle at center, ${item.accentBg} 0%, rgba(10,10,15,0.95) 70%)`,
                        border: `2px solid ${item.accent}`,
                        color: item.accent,
                        boxShadow: `0 0 15px ${item.accentBg}`,
                      }}
                      initial={{ scale: 0, opacity: 0 }}
                      whileInView={{ scale: 1, opacity: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.12 + 0.1, type: 'spring', stiffness: 300, damping: 20 }}
                    >
                      {item.step}
                      {/* Pulse ring */}
                      <motion.div
                        className="absolute inset-0 rounded-full"
                        style={{ border: `1px solid ${item.accent}` }}
                        animate={{ scale: [1, 1.6], opacity: [0.5, 0] }}
                        transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.3 }}
                      />
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, x: 30, scale: 0.95 }}
                      whileInView={{ opacity: 1, x: 0, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.12 + 0.15, duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
                    >
                      <SpotlightCard className="h-full group" spotlightColor={item.accentBg}>
                        <div
                          className="relative p-6 rounded-2xl border transition-all duration-300 overflow-hidden"
                          style={{
                            background: 'rgba(10,10,15,0.85)',
                            backdropFilter: 'blur(16px)',
                            WebkitBackdropFilter: 'blur(16px)',
                            borderColor: 'rgba(255,255,255,0.06)',
                          }}
                        >
                          {/* Top ambient glow */}
                          <div
                            className="absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[40px] opacity-10 pointer-events-none"
                            style={{ background: item.accent }}
                          />

                          <motion.div className="flex items-center gap-3 mb-3" initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.25, duration: 0.4 }}>
                            <motion.div
                              className="flex items-center justify-center w-10 h-10 rounded-xl"
                              style={{ background: `linear-gradient(135deg, ${item.accent}20, rgba(0,0,0,0.3))`, border: `1px solid ${item.accentBorder}`, color: item.accent }}
                              initial={{ scale: 0, rotate: -15 }} whileInView={{ scale: 1, rotate: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.3, type: 'spring', stiffness: 250, damping: 18 }}
                            >
                              <div className="absolute inset-0 blur-sm opacity-40 bg-current rounded-xl" />
                              <div className="relative z-10 text-current">{item.icon}</div>
                            </motion.div>
                            <span className="text-xs font-mono tracking-widest uppercase opacity-60 font-semibold" style={{ color: item.accent }}>Step {item.step}</span>
                          </motion.div>
                          <motion.h4 className="text-lg font-bold text-white mb-1" initial={{ opacity: 0, y: 6 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.3, duration: 0.4 }}>{item.title}</motion.h4>
                          <motion.p className="text-[13px] font-semibold mb-2 tracking-wide" style={{ color: item.accent, opacity: 0.9 }} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.35, duration: 0.4 }}>{item.subtitle}</motion.p>
                          <motion.p className="text-sm text-gray-400 leading-relaxed mb-4" initial={{ opacity: 0, y: 4 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.4, duration: 0.4 }}>{item.description}</motion.p>
                          <motion.div
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono shadow-inner"
                            style={{ background: `linear-gradient(135deg, ${item.accentBg}, rgba(0,0,0,0.5))`, border: `1px solid ${item.accentBorder}`, color: item.accent }}
                            initial={{ opacity: 0, scale: 0.8 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.12 + 0.45, type: 'spring', stiffness: 300, damping: 20 }}
                          >
                            <span className="text-sm font-bold drop-shadow-[0_0_5px_currentColor]">{item.metric.value}</span>
                            <span className="opacity-70 text-gray-300 font-sans">{item.metric.label}</span>
                          </motion.div>
                        </div>
                      </SpotlightCard>
                    </motion.div>
                  </div>
                </motion.div>
              );
            })}

            {/* Bottom completion indicator - Upgraded */}
            <motion.div
              className="hidden md:flex flex-col items-center mt-12 relative z-10"
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.8 }}
            >
              <div className="w-12 h-12 rounded-full border-[2px] border-[#AAFF00] bg-[#AAFF00]/10 flex items-center justify-center shadow-[0_0_20px_rgba(170,255,0,0.3),inset_0_0_15px_rgba(170,255,0,0.2)] backdrop-blur-md">
                <svg className="w-6 h-6 text-[#AAFF00] drop-shadow-[0_0_5px_#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm font-mono text-[#AAFF00] font-bold mt-3 tracking-[0.2em] drop-shadow-[0_0_8px_rgba(170,255,0,0.5)]">JAWABAN TERVERIFIKASI</p>
            </motion.div>
          </div>
        </motion.div>


        {/* ============================================
          1. USE CASES — Siapa yang Menggunakan
          ============================================ */}
        <motion.div
          className="max-w-7xl mx-auto px-4 mt-32"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.8 }}
        >
          <div className="text-center mb-16 relative">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-[#AAFF00]/5 blur-[120px] rounded-full pointer-events-none" />

            <motion.div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 backdrop-blur-md mb-6"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <div className="w-2 h-2 rounded-full bg-[#AAFF00] animate-pulse" />
              <span className="text-xs font-mono uppercase tracking-widest text-gray-300">Siapa yang Menggunakan</span>
            </motion.div>

            <motion.h2
              className="text-4xl md:text-5xl font-bold tracking-tight mb-4"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <span className="text-white">Dibangun untuk </span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-300 to-gray-500">Profesional Hukum</span>
            </motion.h2>

            <motion.p
              className="text-lg text-gray-400 max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
            >
              Dari firma hukum hingga mahasiswa, Omnibus hadir melayani beragam kebutuhan ekosistem riset hukum di Indonesia secara instan dan akurat.
            </motion.p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                ),
                title: 'Firma Hukum',
                description: 'Riset instan untuk kasus klien, monitor regulasi terkini, dan analisis gap hukum dengan presisi.',
                example: 'Apa saja ketentuan cuti panjang dalam UU Cipta Kerja terbaru?',
                color: '#AAFF00', // Lime
                bgClass: 'rgba(170, 255, 0, 0.08)'
              },
              {
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                ),
                title: 'Startup & UMKM',
                description: 'Validasi kepatuhan operasional, panduan legalitas pendirian, dan mitigasi risiko izin usaha.',
                example: 'Bagaimana prosedur mendirikan PT Perorangan di sistem OSS?',
                color: '#00D4FF', // Cyan
                bgClass: 'rgba(0, 212, 255, 0.08)'
              },
              {
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                ),
                title: 'Compliance Officers',
                description: 'Audit regulasi internal, pengawasan kewajiban lapor, serta pemetaan aturan sektoral terpadu.',
                example: 'Aturan apa saja terkait perlindungan data pribadi untuk sektor Fintech?',
                color: '#A855F7', // Purple
                bgClass: 'rgba(168, 85, 247, 0.08)'
              },
              {
                icon: (
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                ),
                title: 'Mahasiswa Hukum',
                description: 'Akselerasi literature review, komparasi produk hukum, dan persiapan ujian akademis.',
                example: 'Jelaskan perbedaan mendasar antara UU Perlindungan Konsumen dan PP turunannya.',
                color: '#FFB800', // Amber
                bgClass: 'rgba(255, 184, 0, 0.08)'
              },
            ].map((useCase, i) => (
              <motion.div
                key={useCase.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{
                  delay: 0.4 + i * 0.1,
                  duration: 0.6,
                  ease: [0.22, 1, 0.36, 1] as [number, number, number, number]
                }}
              >
                <SpotlightCard className="h-full group" spotlightColor={useCase.bgClass}>
                  <div className="relative p-7 flex flex-col h-full rounded-2xl overflow-hidden transition-all duration-500 bg-[#0A0A0F]/60 hover:bg-[#0A0A0F]/40 border border-white/[0.04] hover:border-white/[0.1] backdrop-blur-md z-10 w-full">

                    {/* Top ambient glow mapped to accent color */}
                    <div
                      className="absolute -top-10 -right-10 w-40 h-40 rounded-full blur-[50px] opacity-10 group-hover:opacity-30 transition-opacity duration-700 pointer-events-none"
                      style={{ background: useCase.color }}
                    />

                    {/* Icon Container with subtle gradient */}
                    <div
                      className="relative w-12 h-12 rounded-xl flex items-center justify-center mb-6 shadow-xl flex-shrink-0"
                      style={{
                        background: `linear-gradient(135deg, rgba(255,255,255,0.05), ${useCase.color}20)`,
                        border: `1px solid ${useCase.color}30`,
                        color: useCase.color
                      }}
                    >
                      {/* Inner glow */}
                      <div className="absolute inset-0 blur-md opacity-40 group-hover:opacity-60 transition-opacity duration-500" style={{ background: useCase.color }} />
                      <div className="relative z-10 transform group-hover:scale-110 group-hover:-rotate-6 transition-transform duration-500 text-current">
                        {useCase.icon}
                      </div>
                    </div>

                    <h3 className="text-xl font-bold text-white mb-3 tracking-tight transition-all duration-500 leading-snug">
                      {useCase.title}
                    </h3>

                    <p className="text-[14px] text-gray-400 leading-relaxed mb-8 flex-grow">
                      {useCase.description}
                    </p>

                    {/* Elevated Prompt Example */}
                    <div className="mt-auto relative rounded-xl bg-black/40 border border-white/5 group-hover:border-white/10 transition-colors duration-500 overflow-hidden">
                      {/* Highlight bar on left */}
                      <div className="absolute top-0 bottom-0 left-0 w-1 opacity-50 transition-colors duration-300" style={{ backgroundColor: useCase.color }} />

                      <div className="px-4 py-3 flex gap-3 items-start">
                        <svg className="w-4 h-4 mt-0.5 opacity-60 flex-shrink-0" style={{ color: useCase.color }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        <p className="text-[13px] text-gray-300 italic align-top group-hover:text-white transition-colors duration-300 line-clamp-3">
                          "{useCase.example}"
                        </p>
                      </div>
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
          className="max-w-7xl mx-auto px-4 mt-32"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.8 }}
        >
          <div className="text-center mb-16 relative">
            {/* Ambient Back Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[250px] bg-[#AAFF00]/10 blur-[100px] rounded-full pointer-events-none" />

            <motion.div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 backdrop-blur-md mb-6"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <svg className="w-3.5 h-3.5 text-[#AAFF00]" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              <span className="text-xs font-mono uppercase tracking-widest text-gray-300">Teknologi Enterprise-Grade</span>
            </motion.div>

            <motion.h2
              className="text-4xl md:text-5xl font-bold tracking-tight mb-4"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <span className="text-white">Arsitektur yang Anda </span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#AAFF00] via-[#88CC00] to-[#559900]">Bisa Percaya</span>
            </motion.h2>

            <motion.p
              className="text-lg text-gray-400 max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
            >
              Stack teknologi produksi dengan performa tinggi, dirancang khusus untuk memproses big data hukum dengan latensi minimal.
            </motion.p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
            {/* ── MODULE 1: AI & SEARCH ENGINE ── */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4, duration: 0.7 }}
            >
              <div className="relative p-[1px] rounded-3xl overflow-hidden bg-gradient-to-br from-[#AAFF00]/20 via-[#AAFF00]/10 to-transparent group">
                <div className="absolute inset-0 bg-[#AAFF00]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-2xl" />
                <div className="relative bg-[#0A0A0F]/90 backdrop-blur-xl rounded-[23px] p-8 h-full border border-white/5">
                  <div className="flex items-center gap-4 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#AAFF00]/20 to-[#88CC00]/20 border border-[#AAFF00]/30 flex items-center justify-center text-[#AAFF00] shadow-[0_0_20px_rgba(170,255,0,0.2)]">
                      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-white tracking-tight">AI & Knowledge Engine</h3>
                      <p className="text-sm text-[#AAFF00]/80 font-mono mt-1">CORE PERCEPTION LAYER</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {[
                      {
                        name: 'NVIDIA NIM', role: 'Kimi K2 LLM',
                        color: '#AAFF00', // NVIDIA Green adjusted to theme
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      },
                      {
                        name: 'Qdrant', role: 'Vector Database',
                        color: '#AAFF00', // Pinkish Red adjusted to theme
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                      },
                      {
                        name: 'CrossEncoder', role: 'Neural Reranking',
                        color: '#AAFF00', // Cyan adjusted to theme
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                      },
                      {
                        name: 'Hybrid Search', role: 'BM25 + Semantic',
                        color: '#AAFF00', // Purple adjusted to theme
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      },
                    ].map((tech) => (
                      <div key={tech.name} className="group/item relative overflow-hidden rounded-xl border border-white/5 bg-black/40 hover:bg-black/80 transition-all duration-300">
                        {/* Hover edge highlight */}
                        <div className="absolute left-0 top-0 bottom-0 w-1 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{ backgroundColor: tech.color }} />

                        <div className="p-4 flex items-center gap-4 relative z-10">
                          <div className="w-10 h-10 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover/item:scale-110" style={{ background: `${tech.color}15`, color: tech.color, border: `1px solid ${tech.color}30` }}>
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                              {tech.icon}
                            </svg>
                          </div>
                          <div className="flex-1">
                            <h4 className="text-base font-bold text-white group-hover/item:text-white transition-colors">{tech.name}</h4>
                            <p className="text-xs text-gray-500 font-mono mt-0.5 group-hover/item:text-gray-400 transition-colors">— {tech.role}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>

            {/* ── MODULE 2: FRONTEND & API GATEWAY ── */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.6, duration: 0.7 }}
            >
              <div className="relative p-[1px] rounded-3xl overflow-hidden bg-gradient-to-bl from-[#AAFF00]/20 via-[#88CC00]/10 to-transparent group h-full">
                <div className="absolute inset-0 bg-[#AAFF00]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-2xl" />
                <div className="relative bg-[#0A0A0F]/90 backdrop-blur-xl rounded-[23px] p-8 h-full border border-white/5">
                  <div className="flex items-center gap-4 mb-8">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#AAFF00]/20 to-[#88CC00]/20 border border-[#AAFF00]/30 flex items-center justify-center text-[#AAFF00] shadow-[0_0_20px_rgba(170,255,0,0.2)]">
                      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-white tracking-tight">Frontend & API Gateway</h3>
                      <p className="text-sm text-[#AAFF00]/80 font-mono mt-1">USER EXPERIENCE LAYER</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {[
                      {
                        name: 'FastAPI', role: 'Backend Async API',
                        color: '#AAFF00', // Teal adjusted
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                      },
                      {
                        name: 'Next.js 16', role: 'React Framework',
                        color: '#AAFF00', // White adjusted
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                      },
                      {
                        name: 'Framer Motion', role: 'Fluid Layout Animations',
                        color: '#AAFF00', // Fuchsia adjusted
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                      },
                      {
                        name: 'Tailwind CSS', role: 'Utility Styling',
                        color: '#AAFF00', // Light Blue adjusted
                        icon: <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                      },
                    ].map((tech) => (
                      <div key={tech.name} className="group/item relative overflow-hidden rounded-xl border border-white/5 bg-black/40 hover:bg-black/80 transition-all duration-300">
                        <div className="absolute left-0 top-0 bottom-0 w-1 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" style={{ backgroundColor: tech.color }} />
                        <div className="p-4 flex items-center gap-4 relative z-10">
                          <div className="w-10 h-10 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover/item:scale-110" style={{ background: `${tech.color}15`, color: tech.color, border: `1px solid ${tech.color}30` }}>
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                              {tech.icon}
                            </svg>
                          </div>
                          <div className="flex-1">
                            <h4 className="text-base font-bold text-white group-hover/item:text-white transition-colors">{tech.name}</h4>
                            <p className="text-xs text-gray-500 font-mono mt-0.5 group-hover/item:text-gray-400 transition-colors">— {tech.role}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
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
                {
                  icon: (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                  ), label: 'GitHub Open Source'
                },
                {
                  icon: (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  ), label: 'CI/CD Automated'
                },
                {
                  icon: (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  ), label: 'Security Audited'
                },
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

          <div className="relative mt-16 max-w-5xl mx-auto">
            {/* Background ambient glow for Omnibus column */}
            <div className="absolute top-0 bottom-0 left-1/2 md:left-[50%] right-0 md:right-[25%] bg-gradient-to-b from-[#AAFF00]/5 via-[#AAFF00]/2 to-transparent rounded-3xl pointer-events-none hidden md:block" />

            {/* Header Row */}
            <div className="hidden md:grid grid-cols-4 gap-4 px-6 py-4 mb-2 border-b border-white/10 uppercase tracking-widest text-xs font-mono font-bold">
              <div className="col-span-2 text-gray-500">Fitur & Kemampuan</div>
              <div className="text-center text-[#AAFF00] drop-shadow-[0_0_10px_rgba(170,255,0,0.5)] flex flex-col items-center justify-center">
                <span className="text-base font-extrabold tracking-tight shadow-[#AAFF00]">OMNIBUS</span>
              </div>
              <div className="text-center text-gray-500 flex flex-col items-center justify-center">
                <span>Chatbot Generik</span>
              </div>
            </div>

            {/* Feature Rows */}
            <div className="space-y-3 relative z-10">
              {[
                {
                  feature: 'Hybrid Search (BM25 + Dense)',
                  desc: 'Pencarian keyword dan pemahaman semantik',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'CrossEncoder Reranking',
                  desc: 'Penyaringan presisi tinggi untuk hasil paling relevan',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'Knowledge Graph Visualization',
                  desc: 'Pemetaan relasi pasal secara interaktif',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'Grounding Verification',
                  desc: 'Pemeriksaan silang klaim AI dengan sumber hukum (LLM-as-Judge)',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'Confidence Threshold',
                  desc: 'Sistem menolak menjawab jika tidak memiliki dasar kuat',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'Kutipan Pasal & Ayat',
                  desc: 'Referensi spesifik pada setiap kalimat jawaban',
                  omnibus: true, competitor: false
                },
                {
                  feature: 'Session Memory',
                  desc: 'Mengingat konteks percakapan bertahap',
                  omnibus: true, competitor: true
                },
                {
                  feature: 'Open Source',
                  desc: 'Kode sumber terbuka dan dapat diaudit mandiri',
                  omnibus: true, competitor: false
                },
              ].map((row, i) => (
                <motion.div
                  key={row.feature}
                  className="group relative grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-4 items-center p-5 md:px-6 rounded-2xl bg-[#0A0A0F]/60 border border-white/5 hover:border-white/10 transition-all duration-300 backdrop-blur-sm cursor-default overflow-hidden hover:bg-[#0A0A0F]/80"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ delay: 0.1 + i * 0.05, duration: 0.5 }}
                >
                  {/* Hover Left Highlight */}
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#AAFF00] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                  {/* Omnibus Column Highlight inside the row */}
                  <div className="hidden md:block absolute inset-y-0 left-[50%] right-[25%] bg-[#AAFF00]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                  {/* Feature Info */}
                  <div className="col-span-1 md:col-span-2 relative z-10 text-center md:text-left">
                    <h3 className="text-[16px] font-bold text-white group-hover:text-[#AAFF00] transition-colors">{row.feature}</h3>
                    <p className="text-[13px] text-gray-500 mt-1 group-hover:text-gray-400 transition-colors leading-relaxed">{row.desc}</p>
                  </div>

                  {/* Comparison Grid for Mobile (shows side-by-side on small screens) */}
                  <div className="grid grid-cols-2 md:contents gap-4 mt-2 md:mt-0 pt-3 md:pt-0 border-t border-white/5 md:border-0 relative z-10 w-full">

                    {/* Omnibus Status */}
                    <div className="flex flex-col md:items-center justify-center gap-2 items-center">
                      <span className="md:hidden text-[10px] font-mono tracking-widest uppercase text-[#AAFF00] font-bold mb-1">Omnibus</span>
                      {row.omnibus ? (
                        <div className="w-10 h-10 rounded-full bg-[#AAFF00]/10 border border-[#AAFF00]/20 flex items-center justify-center text-[#AAFF00] shadow-[0_0_15px_rgba(170,255,0,0.15)] group-hover:shadow-[0_0_25px_rgba(170,255,0,0.3)] transition-all group-hover:scale-110">
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-gray-600/50 relative">
                          <div className="w-4 h-px bg-gray-600/50 rotate-45 absolute" />
                          <div className="w-4 h-px bg-gray-600/50 -rotate-45 absolute" />
                        </div>
                      )}
                    </div>

                    {/* Competitor Status */}
                    <div className="flex flex-col md:items-center justify-center gap-2 items-center">
                      <span className="md:hidden text-[10px] font-mono tracking-widest uppercase text-gray-500 font-bold mb-1">Generik</span>
                      {row.competitor ? (
                        <div className="w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 opacity-60 transition-all group-hover:bg-white/10">
                          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-gray-600/50 relative">
                          {/* A very subtle minimal cross */}
                          <div className="w-3 h-px bg-gray-600/40 rotate-45 absolute" />
                          <div className="w-3 h-px bg-gray-600/40 -rotate-45 absolute" />
                        </div>
                      )}
                    </div>
                  </div>

                </motion.div>
              ))}
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
          className="max-w-5xl mx-auto px-4 mt-32 mb-20 relative"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.8 }}
        >
          {/* Outer glow aura */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[120%] bg-[#AAFF00]/5 blur-[120px] rounded-full pointer-events-none" />

          {/* Premium Glassmorphic Container */}
          <div className="relative p-[1px] rounded-[2.5rem] overflow-hidden bg-gradient-to-b from-[#AAFF00]/30 via-[#AAFF00]/5 to-transparent group">
            {/* Hover ambient blur */}
            <div className="absolute inset-0 bg-[#AAFF00]/10 opacity-0 group-hover:opacity-100 transition-opacity duration-1000 blur-3xl pointer-events-none" />

            <div className="relative bg-[#0A0A0F]/90 backdrop-blur-xl rounded-[2.5rem] p-12 md:p-16 text-center border border-white/5 overflow-hidden">

              {/* Internal subtle glow pulse */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-[#AAFF00]/20 blur-[60px] rounded-full pointer-events-none" />

              <motion.div
                className="relative z-10"
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2, duration: 0.6 }}
              >
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
                  <span className="text-white">Mulai Eksplorasi </span>
                  <br className="hidden md:block" />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#AAFF00] to-white">
                    Hukum Indonesia
                  </span>
                </h2>

                <p className="text-lg md:text-xl text-gray-400 mb-10 max-w-2xl mx-auto font-light leading-relaxed">
                  Platform AI legal intelligence open-source dan gratis. <br className="hidden md:block" />
                  <span className="text-white/80 font-medium">Tanpa akun. Tanpa kartu kredit. Langsung dapatkan jawaban terverifikasi.</span>
                </p>

                {/* Animated Shine Button */}
                <motion.button
                  onClick={() => router.push('/chat')}
                  className="group relative inline-flex items-center justify-center gap-3 px-10 py-5 bg-[#AAFF00] text-[#0A0A0F] rounded-2xl font-bold text-lg overflow-hidden shadow-[0_0_40px_rgba(170,255,0,0.3)] hover:shadow-[0_0_60px_rgba(170,255,0,0.5)] transition-shadow duration-300"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <span className="relative z-10 flex items-center gap-2">
                    Mulai Sekarang
                    <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </span>
                  {/* Sweeping Shine overlay */}
                  <div className="absolute inset-0 -translate-x-full group-hover:animate-sweep bg-gradient-to-r from-transparent via-white/40 to-transparent skew-x-12 z-0" />
                </motion.button>

                {/* Trust Badges */}
                <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
                  <div className="flex items-center gap-1.5 text-xs font-mono text-gray-500 uppercase tracking-wider">
                    <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    <span>Powered by NIM</span>
                  </div>
                  <div className="w-1 h-1 rounded-full bg-white/10" />
                  <div className="flex items-center gap-1.5 text-xs font-mono text-gray-500 uppercase tracking-wider">
                    <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    <span>Terverifikasi</span>
                  </div>
                  <div className="w-1 h-1 rounded-full bg-white/10" />
                  <div className="flex items-center gap-1.5 text-xs font-mono text-gray-500 uppercase tracking-wider">
                    <svg className="w-3.5 h-3.5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21V3h18v18H3zm3-3h12M6 6h12" /></svg>
                    <span>100% Hukum ID</span>
                  </div>
                </div>

              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
