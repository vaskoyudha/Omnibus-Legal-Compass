'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import LoadingSpinner from '@/components/LoadingSpinner';
import CitationList from '@/components/CitationList';
import { checkCompliance, ComplianceResponse } from '@/lib/api';

type InputType = 'text' | 'pdf';

export default function CompliancePage() {
  const [inputType, setInputType] = useState<InputType>('text');
  const [businessDescription, setBusinessDescription] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [response, setResponse] = useState<ComplianceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResponse(null);

    try {
      if (inputType === 'pdf' && pdfFile) {
        const result = await checkCompliance('', pdfFile);
        setResponse(result);
      } else if (inputType === 'text' && businessDescription.trim()) {
        const result = await checkCompliance(businessDescription);
        setResponse(result);
      } else {
        throw new Error(inputType === 'pdf' 
          ? 'Silakan pilih file PDF terlebih dahulu' 
          : 'Silakan masukkan deskripsi kegiatan usaha');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Terjadi kesalahan saat memeriksa kepatuhan');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('Hanya file PDF yang diperbolehkan');
        return;
      }
      setPdfFile(file);
      setError(null);
    }
  };

  const getRiskBadge = (riskLevel: string) => {
    const styles = {
      tinggi: 'bg-red-100 text-red-800 border-red-200',
      sedang: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      rendah: 'bg-green-100 text-green-800 border-green-200',
    };
    const labels = {
      tinggi: 'Risiko Tinggi',
      sedang: 'Risiko Sedang',
      rendah: 'Risiko Rendah',
    };
    return (
      <span className={`px-3 py-1 text-sm font-semibold rounded-full border ${styles[riskLevel as keyof typeof styles] || styles.sedang}`}>
        {labels[riskLevel as keyof typeof labels] || riskLevel}
      </span>
    );
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      tinggi: 'text-red-600 bg-red-50 border-red-200',
      sedang: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      rendah: 'text-green-600 bg-green-50 border-green-200',
    };
    return colors[severity.toLowerCase()] || 'text-slate-600 bg-slate-50 border-slate-200';
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-700 to-emerald-800 text-white py-12 px-4">
        <div className="max-w-4xl mx-auto">
          <Link href="/" className="inline-flex items-center gap-2 text-emerald-200 hover:text-white mb-4 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Kembali ke Beranda
          </Link>
          <h1 className="text-4xl font-bold mb-2">Pemeriksa Kepatuhan</h1>
          <p className="text-emerald-200 text-lg">Compliance Checker untuk Kegiatan Usaha</p>
          <p className="text-emerald-300 text-sm mt-2">
            Analisis kepatuhan usaha Anda terhadap peraturan perundang-undangan Indonesia
          </p>
        </div>
      </div>

      {/* Form Section */}
      <div className="max-w-4xl mx-auto px-4 -mt-6">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <form onSubmit={handleSubmit}>
            {/* Input Type Toggle */}
            <div className="flex gap-4 mb-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="inputType"
                  value="text"
                  checked={inputType === 'text'}
                  onChange={() => setInputType('text')}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-sm font-medium text-slate-700">Deskripsi Teks</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="inputType"
                  value="pdf"
                  checked={inputType === 'pdf'}
                  onChange={() => setInputType('pdf')}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-sm font-medium text-slate-700">Upload PDF</span>
              </label>
            </div>

            {/* Text Input */}
            {inputType === 'text' && (
              <div className="mb-4">
                <label htmlFor="businessDescription" className="block text-sm font-medium text-slate-700 mb-2">
                  Deskripsi Kegiatan Usaha
                </label>
                <textarea
                  id="businessDescription"
                  value={businessDescription}
                  onChange={(e) => setBusinessDescription(e.target.value)}
                  placeholder="Jelaskan kegiatan usaha Anda secara detail, termasuk jenis usaha, struktur perusahaan, jumlah karyawan, dan aspek operasional lainnya..."
                  rows={6}
                  className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 resize-none text-slate-800 placeholder-slate-400"
                />
              </div>
            )}

            {/* PDF Input */}
            {inputType === 'pdf' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Upload Dokumen PDF
                </label>
                <div 
                  className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-emerald-400 transition-colors cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <svg className="w-12 h-12 mx-auto text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  {pdfFile ? (
                    <div>
                      <p className="text-emerald-600 font-medium">{pdfFile.name}</p>
                      <p className="text-sm text-slate-500 mt-1">
                        {(pdfFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-slate-600">Klik untuk memilih file PDF</p>
                      <p className="text-sm text-slate-400 mt-1">atau drag and drop di sini</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || (inputType === 'text' && !businessDescription.trim()) || (inputType === 'pdf' && !pdfFile)}
              className="w-full py-3 px-4 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 focus:ring-4 focus:ring-emerald-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Memeriksa Kepatuhan...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Periksa Kepatuhan
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Results Section */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {isLoading && <LoadingSpinner />}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-lg">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="font-medium">Terjadi Kesalahan</h3>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {response && !isLoading && (
          <div className="space-y-6">
            {/* Compliance Status Card */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  {response.compliant ? (
                    <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
                      <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
                      <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </div>
                  )}
                  <div>
                    <h2 className="text-xl font-bold text-slate-800">
                      {response.compliant ? 'Patuh' : 'Tidak Patuh'}
                    </h2>
                    <p className="text-slate-500 text-sm">Status Kepatuhan</p>
                  </div>
                </div>
                {getRiskBadge(response.risk_level)}
              </div>

              {/* Summary */}
              <div className="bg-slate-50 rounded-lg p-4 mt-4">
                <h3 className="font-semibold text-slate-700 mb-2 flex items-center gap-2">
                  <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Ringkasan
                </h3>
                <p className="text-slate-600 whitespace-pre-wrap">{response.summary}</p>
              </div>

              {/* Processing Time */}
              <p className="text-xs text-slate-400 mt-4 text-right">
                Waktu pemrosesan: {(response.processing_time_ms / 1000).toFixed(2)} detik
              </p>
            </div>

            {/* Issues Card */}
            {response.issues && response.issues.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Masalah Ditemukan ({response.issues.length})
                </h3>
                <div className="space-y-3">
                  {response.issues.map((issue, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded uppercase">
                          {issue.severity}
                        </span>
                        <div className="flex-1">
                          <p className="font-medium">{issue.issue}</p>
                          <p className="text-sm opacity-80 mt-1">
                            Regulasi: {issue.regulation}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations Card */}
            {response.recommendations && response.recommendations.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Rekomendasi ({response.recommendations.length})
                </h3>
                <ul className="space-y-2">
                  {response.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start gap-3 text-slate-600">
                      <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-sm font-semibold flex-shrink-0">
                        {index + 1}
                      </span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Citations */}
            {response.citations && response.citations.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <CitationList citations={response.citations} />
              </div>
            )}
          </div>
        )}

        {/* Empty State */}
        {!response && !isLoading && !error && (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 bg-emerald-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Periksa Kepatuhan Usaha Anda
            </h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Masukkan deskripsi kegiatan usaha atau upload dokumen PDF untuk memeriksa 
              kepatuhan terhadap peraturan perundang-undangan Indonesia.
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-gray-500">
            Omnibus Legal Compass - Pemeriksa Kepatuhan Usaha
          </p>
          <p className="text-center text-xs text-gray-400 mt-1">
            Hasil pemeriksaan bersifat informatif dan bukan merupakan nasihat hukum resmi
          </p>
        </div>
      </footer>
    </main>
  );
}
