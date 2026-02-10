'use client';

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { getGuidance, GuidanceResponse } from '@/lib/api';
import CitationList from '@/components/CitationList';
import SkeletonLoader from '@/components/SkeletonLoader';
import { toast } from 'sonner';

const BUSINESS_TYPES = [
  { value: 'pt', label: 'Perseroan Terbatas (PT)', description: 'Badan usaha berbadan hukum dengan modal terbagi atas saham', icon: '🏢' },
  { value: 'cv', label: 'Commanditaire Vennootschap (CV)', description: 'Persekutuan dengan sekutu aktif dan pasif', icon: '🤝' },
  { value: 'firma', label: 'Firma', description: 'Persekutuan perdata untuk menjalankan usaha bersama', icon: '👥' },
  { value: 'ud', label: 'Usaha Dagang (UD)', description: 'Usaha perorangan tanpa badan hukum', icon: '🛍️' },
  { value: 'koperasi', label: 'Koperasi', description: 'Badan usaha yang beranggotakan orang-orangan atau badan hukum', icon: '🏛️' },
  { value: 'yayasan', label: 'Yayasan', description: 'Badan hukum untuk tujuan sosial, keagamaan, dan kemanusiaan', icon: '💝' },
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } },
};

export default function GuidancePage() {
  const [businessType, setBusinessType] = useState('');
  const [location, setLocation] = useState('');
  const [industry, setIndustry] = useState('');
  const [result, setResult] = useState<GuidanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessType) {
      toast.error('Pilih jenis badan usaha');
      return;
    }

    setError(null);
    setResult(null);
    setIsLoading(true);

    try {
      const response = await getGuidance({ business_type: businessType, location: location || undefined, industry: industry || undefined });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan');
      toast.error('Gagal mendapatkan panduan');
    } finally {
      setIsLoading(false);
    }
  }, [businessType, location, industry]);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <motion.div
        className="py-12 px-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="max-w-4xl mx-auto text-center">
          <motion.div className="mb-4" variants={itemVariants}>
            <span className="ai-badge">
              <span>📋</span> Business Guide
            </span>
          </motion.div>
          <motion.h1 className="text-4xl font-extrabold text-gradient mb-2" variants={itemVariants}>
            Panduan Pendirian Usaha
          </motion.h1>
          <motion.p className="text-text-secondary" variants={itemVariants}>
            Panduan lengkap mendirikan badan usaha sesuai peraturan perundang-undangan
          </motion.p>
        </div>
      </motion.div>

      {/* Form Section */}
      <div className="max-w-4xl mx-auto px-4 -mt-2">
        <motion.div
          className="glass-strong rounded-2xl p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <form onSubmit={handleSubmit}>
            {/* Business Type Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-text-secondary mb-3">
                Pilih Jenis Badan Usaha
              </label>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {BUSINESS_TYPES.map((type) => (
                  <motion.label
                    key={type.value}
                    className={`relative flex flex-col p-4 cursor-pointer glass rounded-xl border-2 transition-all ${businessType === type.value
                      ? 'border-[#AAFF00]/50 bg-[#AAFF00]/5 shadow-lg shadow-[#AAFF00]/5'
                      : 'border-transparent hover:border-[#AAFF00]/15 hover:shadow-md'
                      }`}
                    whileHover={{ scale: 1.02, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <input
                      type="radio"
                      name="businessType"
                      value={type.value}
                      checked={businessType === type.value}
                      onChange={(e) => setBusinessType(e.target.value)}
                      className="sr-only"
                    />
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">{type.icon}</span>
                      <span className={`font-semibold text-sm ${businessType === type.value ? 'text-[#AAFF00]' : 'text-text-primary'
                        }`}>
                        {type.label}
                      </span>
                    </div>
                    <span className="text-xs text-text-muted leading-relaxed">
                      {type.description}
                    </span>
                    {businessType === type.value && (
                      <motion.div
                        layoutId="business-type-indicator"
                        className="absolute top-2 right-2 w-6 h-6 bg-[#AAFF00] rounded-full flex items-center justify-center"
                        transition={{ type: 'spring', bounce: 0.3 }}
                      >
                        <svg className="w-4 h-4 text-[#0A0A0F]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </motion.div>
                    )}
                  </motion.label>
                ))}
              </div>
            </div>

            {/* Optional Fields */}
            <div className="grid gap-4 sm:grid-cols-2 mb-6">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Lokasi (Opsional)
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Contoh: Jakarta, Surabaya..."
                  className="w-full px-4 py-3 rounded-xl dark-input text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Industri (Opsional)
                </label>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="Contoh: Teknologi, F&B..."
                  className="w-full px-4 py-3 rounded-xl dark-input text-sm"
                />
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={isLoading || !businessType}
              className="w-full py-3.5 bg-gradient-to-r from-[#AAFF00] to-[#88CC00] text-[#0A0A0F] font-semibold rounded-xl hover:shadow-lg hover:shadow-[#AAFF00]/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Memproses...
                </span>
              ) : (
                '📋 Dapatkan Panduan'
              )}
            </motion.button>
          </form>
        </motion.div>
      </div>

      {/* Results Section */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {isLoading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <SkeletonLoader variant="card" lines={6} />
          </motion.div>
        )}

        {error && (
          <motion.div
            className="glass-strong rounded-2xl border border-red-500/20 px-6 py-5"
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-text-primary">Terjadi Kesalahan</h3>
                <p className="text-sm text-text-secondary mt-1">{error}</p>
              </div>
            </div>
          </motion.div>
        )}

        {result && !isLoading && (
          <motion.div
            className="space-y-6"
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Summary Card */}
            <motion.div className="glass-strong rounded-2xl p-6" variants={itemVariants}>
              <div className="flex items-center gap-4 mb-5">
                <div className="p-3 bg-[#AAFF00]/10 rounded-xl">
                  <svg className="w-8 h-8 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-text-primary">Panduan Pendirian</h2>
                  <p className="text-sm text-text-muted">
                    {BUSINESS_TYPES.find(t => t.value === businessType)?.label || businessType}
                  </p>
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3 mb-5">
                {result.total_estimated_time && (
                  <div className="stat-card text-center">
                    <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Estimasi Waktu</div>
                    <div className="text-lg font-bold text-[#AAFF00]">{result.total_estimated_time}</div>
                  </div>
                )}
                {result.steps && (
                  <div className="stat-card text-center">
                    <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Jumlah Langkah</div>
                    <div className="text-lg font-bold text-text-primary">{result.steps.length}</div>
                  </div>
                )}
                {result.required_permits && (
                  <div className="stat-card text-center">
                    <div className="text-xs text-text-muted uppercase tracking-wide mb-1">Izin Diperlukan</div>
                    <div className="text-lg font-bold text-text-primary">{result.required_permits.length}</div>
                  </div>
                )}
              </div>

              {result.summary && (
                <div className="p-4 glass rounded-xl">
                  <h3 className="text-sm font-semibold text-text-primary mb-2">Ringkasan</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">{result.summary}</p>
                </div>
              )}
            </motion.div>

            {/* Steps Timeline */}
            {result.steps && result.steps.length > 0 && (
              <motion.div className="glass-strong rounded-2xl p-6" variants={itemVariants}>
                <h3 className="text-lg font-semibold text-text-primary mb-6 flex items-center gap-2">
                  <svg className="w-5 h-5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  Langkah-Langkah
                </h3>
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#AAFF00] via-[#88CC00] to-transparent" />

                  <div className="space-y-4">
                    {result.steps.map((step, i) => (
                      <motion.div
                        key={i}
                        className="relative flex gap-4 pl-2"
                        initial={{ opacity: 0, x: -16 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 + i * 0.1 }}
                      >
                        {/* Step Number */}
                        <div className="relative z-10 flex-shrink-0 w-8 h-8 rounded-full bg-[#AAFF00] flex items-center justify-center text-sm font-bold text-[#0A0A0F] shadow-md shadow-[#AAFF00]/20">
                          {i + 1}
                        </div>

                        {/* Step Content */}
                        <div className="flex-1 glass rounded-xl p-4 hover:bg-white/[0.06] transition-colors">
                          <h4 className="font-semibold text-text-primary text-sm mb-1">
                            {typeof step === 'string' ? step : step.title || `Langkah ${i + 1}`}
                          </h4>
                          {typeof step !== 'string' && step.description && (
                            <p className="text-sm text-text-secondary leading-relaxed">{step.description}</p>
                          )}
                          {typeof step !== 'string' && step.estimated_time && (
                            <div className="mt-2 flex items-center gap-1 text-xs text-text-muted">
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              {step.estimated_time}
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Required Permits */}
            {result.required_permits && result.required_permits.length > 0 && (
              <motion.div className="glass-strong rounded-2xl p-6" variants={itemVariants}>
                <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Izin yang Diperlukan
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {result.required_permits.map((permit, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 glass rounded-xl">
                      <span className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4" />
                        </svg>
                      </span>
                      <span className="text-sm text-text-primary font-medium">{permit}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}



            {/* Citations */}
            {result.citations && result.citations.length > 0 && (
              <motion.div className="glass-strong rounded-2xl overflow-hidden" variants={itemVariants}>
                <CitationList citations={result.citations} />
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-border mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-text-muted">
            Omnibus Legal Compass - Panduan Pendirian Badan Usaha
          </p>
        </div>
      </footer>
    </div>
  );
}
