'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import type { RegulationDetailResponse } from '@/lib/api';

export interface MetadataPanelProps {
  regulation: Readonly<RegulationDetailResponse>;
}

const DIRECTION_LABEL: Record<string, string> = {
  amends: 'Mengamandemen',
  amended_by: 'Diamandemen oleh',
  implements: 'Melaksanakan',
  implemented_by: 'Dilaksanakan oleh',
  repeals: 'Mencabut',
  repealed_by: 'Dicabut oleh',
};

export default function MetadataPanel({ regulation }: Readonly<MetadataPanelProps>) {
  const router = useRouter();

  const handleAskQuestion = () => {
    const question = encodeURIComponent(`Jelaskan ${regulation.title}`);
    router.push(`/chat?question=${question}`);
  };

  return (
    <aside className="flex flex-col gap-4">
      {/* Quick stats */}
      <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Info Dokumen</h3>
        <dl className="space-y-2">
          {regulation.enactment_date && (
            <div className="flex justify-between items-center">
              <dt className="text-xs text-white/40">Tanggal Berlaku</dt>
              <dd className="text-xs text-white/70 font-medium">{regulation.enactment_date}</dd>
            </div>
          )}
          <div className="flex justify-between items-center">
            <dt className="text-xs text-white/40">Referensi Silang</dt>
            <dd className="text-xs text-white/70 font-medium">{regulation.cross_reference_count}</dd>
          </div>
          <div className="flex justify-between items-center">
            <dt className="text-xs text-white/40">Chunk Terindeks</dt>
            <dd className="text-xs text-white/70 font-medium">{regulation.indexed_chunk_count}</dd>
          </div>
          <div className="flex justify-between items-center">
            <dt className="text-xs text-white/40">Bab</dt>
            <dd className="text-xs text-white/70 font-medium">{regulation.chapters.length}</dd>
          </div>
        </dl>
      </div>

      {/* Ask about this regulation */}
      <button
        onClick={handleAskQuestion}
        className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[#AAFF00] to-[#88CC00] text-[#0A0A0F] text-sm font-bold hover:shadow-lg hover:shadow-[#AAFF00]/20 transition-all"
      >
        💬 Tanya tentang regulasi ini
      </button>

      {/* Amendments */}
      {regulation.amendments.length > 0 && (
        <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
          <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">Amandemen</h3>
          <ul className="space-y-2">
            {regulation.amendments.map((amend) => (
              <li key={`${amend.regulation_id}-${amend.direction}`}>
                <Link
                  href={`/regulations/${encodeURIComponent(amend.regulation_id)}`}
                  className="flex flex-col gap-0.5 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] hover:border-white/[0.1] transition-colors group"
                >
                  <span className="text-[10px] text-white/30 uppercase tracking-wide">
                    {DIRECTION_LABEL[amend.direction] ?? amend.direction} · {amend.year}
                  </span>
                  <span className="text-xs text-white/65 group-hover:text-[#AAFF00]/80 transition-colors line-clamp-2 leading-snug">
                    {amend.regulation_title}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Implementing regulations */}
      {regulation.implementing_regulations.length > 0 && (
        <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
          <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">
            Regulasi Pelaksana
          </h3>
          <ul className="space-y-2">
            {regulation.implementing_regulations.map((reg) => (
              <li key={reg.id}>
                <Link
                  href={`/regulations/${encodeURIComponent(reg.id)}`}
                  className="block p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] hover:border-white/[0.1] transition-colors group"
                >
                  <span className="text-xs text-white/65 group-hover:text-[#AAFF00]/80 transition-colors line-clamp-2 leading-snug">
                    {reg.title}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Parent law */}
      {regulation.parent_law && (
        <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-2xl">
          <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">
            Hukum Induk
          </h3>
          <Link
            href={`/regulations/${encodeURIComponent(regulation.parent_law.id)}`}
            className="block p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.06] hover:border-white/[0.1] transition-colors group"
          >
            <span className="text-xs text-white/65 group-hover:text-[#AAFF00]/80 transition-colors line-clamp-2 leading-snug">
              {regulation.parent_law.title}
            </span>
          </Link>
        </div>
      )}
    </aside>
  );
}
