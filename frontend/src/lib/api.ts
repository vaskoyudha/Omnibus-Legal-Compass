const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Citation {
  document_title: string;
  document_type: string;
  pasal: string;
  relevance_score: number;
  content_snippet: string;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
  processing_time: number;
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
