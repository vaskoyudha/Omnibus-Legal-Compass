'use client';

export interface RegulationFiltersProps {
  search: string;
  nodeType: string;
  status: string;
  year: string;
  onSearchChange: (v: string) => void;
  onNodeTypeChange: (v: string) => void;
  onStatusChange: (v: string) => void;
  onYearChange: (v: string) => void;
}

const NODE_TYPE_OPTIONS = [
  { value: '', label: 'Semua Jenis' },
  { value: 'law', label: 'UU – Undang-Undang' },
  { value: 'government_regulation', label: 'PP – Peraturan Pemerintah' },
  { value: 'presidential_regulation', label: 'Perpres – Peraturan Presiden' },
  { value: 'ministerial_regulation', label: 'Permen – Peraturan Menteri' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Semua Status' },
  { value: 'active', label: 'Aktif' },
  { value: 'amended', label: 'Diamandemen' },
  { value: 'repealed', label: 'Dicabut' },
];

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = [
  { value: '', label: 'Semua Tahun' },
  ...Array.from({ length: currentYear - 2014 }, (_, i) => {
    const y = String(currentYear - i);
    return { value: y, label: y };
  }),
];

const selectClass =
  'w-full px-3.5 py-3 rounded-xl bg-[#0A0A0F]/60 border border-white/[0.08] text-white/80 text-sm font-medium appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/40 focus:border-[#AAFF00]/40 hover:border-white/[0.15] transition-all';

export default function RegulationFilters({
  search, nodeType, status, year,
  onSearchChange, onNodeTypeChange, onStatusChange, onYearChange,
}: Readonly<RegulationFiltersProps>) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {/* Search */}
      <div className="relative flex-1 min-w-0 group">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-white/25 group-focus-within:text-[#AAFF00] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
        </span>
        <input
          type="text" value={search} onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Cari regulasi…" aria-label="Cari regulasi"
          className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#0A0A0F]/60 border border-white/[0.08] text-white/90 text-sm font-medium placeholder:text-white/25 focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/40 focus:border-[#AAFF00]/40 hover:border-white/[0.15] transition-all"
        />
      </div>

      {/* Type */}
      <div className="relative sm:w-52">
        <select value={nodeType} onChange={(e) => onNodeTypeChange(e.target.value)} aria-label="Filter jenis regulasi" className={selectClass}>
          {NODE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F] text-white">{opt.label}</option>
          ))}
        </select>
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-3.5 h-3.5 text-white/25" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" /></svg>
        </span>
      </div>

      {/* Status */}
      <div className="relative sm:w-44">
        <select value={status} onChange={(e) => onStatusChange(e.target.value)} aria-label="Filter status regulasi" className={selectClass}>
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F] text-white">{opt.label}</option>
          ))}
        </select>
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-3.5 h-3.5 text-white/25" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" /></svg>
        </span>
      </div>

      {/* Year */}
      <div className="relative sm:w-36">
        <select value={year} onChange={(e) => onYearChange(e.target.value)} aria-label="Filter tahun regulasi" className={selectClass}>
          {YEAR_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F] text-white">{opt.label}</option>
          ))}
        </select>
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-3.5 h-3.5 text-white/25" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" /></svg>
        </span>
      </div>
    </div>
  );
}
