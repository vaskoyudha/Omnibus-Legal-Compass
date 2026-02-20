'use client';

import { useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { checkCompliance, ComplianceResponse } from '@/lib/api';
import CitationList from '@/components/CitationList';
import SkeletonLoader from '@/components/SkeletonLoader';
import SpotlightCard from '@/components/reactbits/SpotlightCard';
import { toast } from 'sonner';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
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

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
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
      border: 'border-emerald-500/20',
      text: 'text-emerald-400',
      label: 'Sesuai Regulasi',
      icon: <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    };
    return {
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      text: 'text-red-400',
      label: 'Tidak Sesuai',
      icon: <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    };
  };

  const getRiskConfig = (risk: string) => {
    if (risk === 'low' || risk === 'rendah') return { text: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Rendah' };
    if (risk === 'medium' || risk === 'sedang') return { text: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Sedang' };
    return { text: 'text-red-400', bg: 'bg-red-500/10', label: 'Tinggi' };
  };

  return (
    <div className="min-h-screen">
      {/* Breadcrumb */}
      <div className="max-w-4xl mx-auto px-4 pt-6">
        <nav className="flex items-center gap-2 text-xs text-text-muted">
          <Link href="/" className="hover:text-[#AAFF00] transition-colors">Beranda</Link>
          <span>/</span>
          <span className="text-text-primary">Kepatuhan</span>
        </nav>
      </div>

      {/* Hero Section */}
      <motion.div
        className="relative py-12 px-4 overflow-hidden"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Glow aura */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-[-1]"
          style={{
            width: '60%',
            height: '200px',
            background: 'radial-gradient(ellipse at center, rgba(170,255,0,0.15) 0%, transparent 70%)',
            filter: 'blur(40px)',
          }}
        />
        <div className="relative max-w-4xl mx-auto text-center z-10">
          <motion.div className="mb-4" variants={itemVariants}>
            <span className="ai-badge inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.04] border border-[#AAFF00]/30 text-sm font-medium text-[#AAFF00] shadow-[0_0_15px_rgba(170,255,0,0.2)]">
              <span>🛡️</span> Compliance Check
            </span>
          </motion.div>
          <motion.h1 className="text-4xl md:text-5xl font-extrabold mb-3 tracking-tight" variants={itemVariants}>
            <span className="text-transparent bg-clip-text bg-gradient-to-b from-white to-white/70">
              Cek Kepatuhan Bisnis
            </span>
          </motion.h1>
          <motion.p className="text-white/60 text-base max-w-2xl mx-auto" variants={itemVariants}>
            Periksa kepatuhan bisnis Anda terhadap peraturan perundang-undangan Indonesia
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
          {/* Input Type Selector */}
          <div className="flex gap-1 p-1 bg-white/[0.03] border border-white/[0.06] rounded-xl mb-6 max-w-xs">
            {(['text', 'pdf'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setInputType(type)}
                className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${inputType === type
                    ? 'bg-[#AAFF00] text-[#0A0A0F] shadow-[0_0_15px_rgba(170,255,0,0.3)]'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                  }`}
              >
                {type === 'text' ? '📝 Teks' : '📄 PDF'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            {inputType === 'text' ? (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Deskripsi Bisnis
                </label>
                <textarea
                  value={businessDescription}
                  onChange={(e) => setBusinessDescription(e.target.value)}
                  placeholder="Jelaskan kegiatan bisnis Anda secara detail (jenis usaha, lokasi, skala, dll.)..."
                  className="w-full h-40 p-4 rounded-xl dark-input resize-none text-sm"
                  disabled={isLoading}
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Upload Dokumen Bisnis (PDF)
                </label>
                <div
                  className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${selectedFile
                      ? 'border-[#AAFF00]/40 bg-[#AAFF00]/5 shadow-[0_0_20px_rgba(170,255,0,0.1)]'
                      : 'border-white/[0.1] hover:border-[#AAFF00]/30 hover:bg-white/[0.02]'
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
                  {selectedFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <div className="p-3 bg-[#AAFF00]/10 rounded-xl">
                        <svg className="w-8 h-8 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-text-primary">{selectedFile.name}</p>
                        <p className="text-sm text-text-muted">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <svg className="w-12 h-12 text-text-muted mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <p className="text-text-secondary font-medium">Klik untuk upload PDF</p>
                      <p className="text-sm text-text-muted mt-1">Maksimal 10MB</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            <motion.button
              type="submit"
              disabled={isLoading}
              className="mt-6 w-full py-3.5 bg-gradient-to-r from-[#AAFF00] to-[#88CC00] text-[#0A0A0F] font-semibold rounded-xl hover:shadow-[0_0_20px_rgba(170,255,0,0.3)] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Memeriksa...
                </span>
              ) : (
                '🔍 Periksa Kepatuhan'
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
            {/* Status Card */}
            <motion.div variants={itemVariants}>
              <SpotlightCard className="p-6 h-full" spotlightColor="rgba(170, 255, 0, 0.1)">
                <div className="flex items-center gap-4 mb-6">
                  {(() => {
                    const config = getStatusConfig(result.compliant);
                    return (
                      <>
                        <div className={`p-3 rounded-xl ${config.bg} ${config.text} border ${config.border}`}>
                          {config.icon}
                        </div>
                        <div>
                          <h2 className="text-xl font-bold text-text-primary">
                            {config.label}
                          </h2>
                          {result.risk_level && (
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-sm text-text-muted">Tingkat Risiko:</span>
                              {(() => {
                                const riskConfig = getRiskConfig(result.risk_level);
                                return (
                                  <span className={`px-2 py-0.5 text-xs font-medium rounded-md ${riskConfig.bg} ${riskConfig.text}`}>
                                    {riskConfig.label}
                                  </span>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      </>
                    );
                  })()}
                </div>

                {result.summary && (
                  <div className="p-4 glass rounded-xl">
                    <h3 className="text-sm font-semibold text-text-primary mb-2">Ringkasan</h3>
                    <p className="text-sm text-text-secondary leading-relaxed">{result.summary}</p>
                  </div>
                )}
              </SpotlightCard>
            </motion.div>

            {/* Issues */}
            {result.issues && result.issues.length > 0 && (
              <motion.div variants={itemVariants}>
                <SpotlightCard className="p-6 h-full" spotlightColor="rgba(239, 68, 68, 0.08)">
                  <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Temuan Masalah
                    <span className="px-2 py-0.5 text-sm bg-red-500/10 text-red-400 rounded-full">{result.issues.length}</span>
                  </h3>
                  <div className="space-y-3">
                    {result.issues.map((issue, i) => (
                      <div key={i} className="flex items-start gap-3 p-4 dark-error-bg border rounded-xl">
                        <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-red-500/15 flex items-center justify-center text-red-400 text-xs font-bold">{i + 1}</span>
                        <p className="text-sm text-red-200/80 leading-relaxed">{issue.issue}</p>
                      </div>
                    ))}
                  </div>
                </SpotlightCard>
              </motion.div>
            )}

            {/* Recommendations */}
            {result.recommendations && result.recommendations.length > 0 && (
              <motion.div variants={itemVariants}>
                <SpotlightCard className="p-6 h-full" spotlightColor="rgba(170, 255, 0, 0.08)">
                  <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5 text-[#AAFF00]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Rekomendasi
                    <span className="px-2 py-0.5 text-sm bg-[#AAFF00]/10 text-[#AAFF00] rounded-full">{result.recommendations.length}</span>
                  </h3>
                  <div className="space-y-3">
                    {result.recommendations.map((rec, i) => (
                      <div key={i} className="flex items-start gap-3 p-4 dark-success-bg border rounded-xl">
                        <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400 text-xs font-bold">{i + 1}</span>
                        <p className="text-sm text-emerald-200/80 leading-relaxed">{rec}</p>
                      </div>
                    ))}
                  </div>
                </SpotlightCard>
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

    </div>
  );
}
