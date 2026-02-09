const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Backend returns this structure
export interface CitationInfo {
  number: number;
  citation_id: string;
  citation: string;
  score: number;
  metadata: Record<string, unknown>;
}

// Mapped citation for display
export interface Citation {
  document_title: string;
  document_type: string;
  pasal: string;
  relevance_score: number;
  content_snippet: string;
}

// Helper to map backend citation to frontend format
export function mapCitation(c: CitationInfo): Citation {
  const meta = c.metadata || {};
  return {
    document_title: c.citation || `${meta.jenis_dokumen || ''} No. ${meta.nomor || ''} Tahun ${meta.tahun || ''}`,
    document_type: (meta.jenis_dokumen as string) || 'Peraturan',
    pasal: meta.pasal ? `Pasal ${meta.pasal}${meta.ayat ? ` Ayat (${meta.ayat})` : ''}` : '',
    relevance_score: c.score || 0,
    content_snippet: (meta.text as string) || (meta.isi as string) || '',
  };
}

export interface ConfidenceScore {
  numeric: number;
  label: string;
  top_score: number;
  avg_score: number;
}

export interface ValidationResult {
  is_valid: boolean;
  citation_coverage: number;
  warnings: string[];
  hallucination_risk: 'low' | 'medium' | 'high';
}

export interface AskResponse {
  answer: string;
  citations: CitationInfo[];
  confidence: string;
  confidence_score?: ConfidenceScore;
  validation?: ValidationResult;
  processing_time_ms: number;
}

export interface AskRequest {
  question: string;
  top_k?: number;
  document_type?: string;
}

export async function askQuestion(question: string, topK: number = 5): Promise<AskResponse> {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK })
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal mendapatkan jawaban' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }
  
  return response.json();
}

export async function checkHealth(): Promise<{ status: string; qdrant_connected: boolean }> {
  const response = await fetch(`${API_URL}/health`);
  if (!response.ok) {
    throw new Error('Server tidak tersedia');
  }
  return response.json();
}

// Compliance Checker Types
export interface ComplianceIssue {
  issue: string;
  severity: string;
  regulation: string;
}

export interface ComplianceResponse {
  compliant: boolean;
  risk_level: 'tinggi' | 'sedang' | 'rendah';
  summary: string;
  issues: ComplianceIssue[];
  recommendations: string[];
  citations: Citation[];
  processing_time_ms: number;
}

export async function checkCompliance(
  businessDescription: string,
  pdfFile?: File
): Promise<ComplianceResponse> {
  const formData = new FormData();
  
  if (pdfFile) {
    formData.append('pdf_file', pdfFile);
  } else {
    formData.append('business_description', businessDescription);
  }

  const response = await fetch(`${API_URL}/api/compliance/check`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal memeriksa kepatuhan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

// Guidance Types
export interface GuidanceRequest {
  business_type: string;
  location?: string;
  industry?: string;
}

export interface GuidanceStep {
  step_number: number;
  title: string;
  description: string;
  required_documents: string[];
  estimated_time: string;
  responsible_agency: string;
  notes: string;
}

export interface GuidanceCitation {
  number: number;
  citation_id: string;
  citation: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface GuidanceResponse {
  business_type: string;
  business_type_name: string;
  summary: string;
  steps: GuidanceStep[];
  total_estimated_time: string;
  required_permits: string[];
  citations: GuidanceCitation[];
  processing_time_ms: number;
}

export async function getGuidance(request: GuidanceRequest): Promise<GuidanceResponse> {
  const response = await fetch(`${API_URL}/api/guidance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal mendapatkan panduan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}
