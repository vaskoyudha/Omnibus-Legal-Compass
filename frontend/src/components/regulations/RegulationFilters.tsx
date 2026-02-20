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

const selectBaseClass =
  'w-full px-3 py-3 rounded-xl bg-white/[0.02] border border-white/10 text-white/80 text-sm appearance-none cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/50 focus:border-[#AAFF00]/60 hover:border-white/20 transition-all shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)] focus:shadow-[0_0_15px_rgba(170,255,0,0.15)]';

export default function RegulationFilters({
  search,
  nodeType,
  status,
  year,
  onSearchChange,
  onNodeTypeChange,
  onStatusChange,
  onYearChange,
}: Readonly<RegulationFiltersProps>) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {/* Search input */}
      <div className="relative flex-1 min-w-0">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg
            className="w-4 h-4 text-white/30"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
            />
          </svg>
        </span>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Cari regulasi…"
          aria-label="Cari regulasi"
          className="w-full pl-9 pr-4 py-3 rounded-xl bg-white/[0.02] border border-white/10 text-white/90 text-sm placeholder:text-white/40 focus:outline-none focus:ring-1 focus:ring-[#AAFF00]/50 focus:border-[#AAFF00]/60 hover:border-white/20 transition-all shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)] focus:shadow-[0_0_15px_rgba(170,255,0,0.15)]"
        />
      </div>

      {/* Jenis (node type) */}
      <div className="relative sm:w-52">
        <select
          value={nodeType}
          onChange={(e) => onNodeTypeChange(e.target.value)}
          aria-label="Filter jenis regulasi"
          className={selectBaseClass}
        >
          {NODE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F]">
              {opt.label}
            </option>
          ))}
        </select>
        <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>

      {/* Status */}
      <div className="relative sm:w-44">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filter status regulasi"
          className={selectBaseClass}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F]">
              {opt.label}
            </option>
          ))}
        </select>
        <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>

      {/* Tahun */}
      <div className="relative sm:w-36">
        <select
          value={year}
          onChange={(e) => onYearChange(e.target.value)}
          aria-label="Filter tahun regulasi"
          className={selectBaseClass}
        >
          {YEAR_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#0A0A0F]">
              {opt.label}
            </option>
          ))}
        </select>
        <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <svg className="w-4 h-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </div>
    </div>
  );
}
