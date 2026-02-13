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
  grounding_score?: number | null;
  ungrounded_claims?: string[];
}

export interface AskResponse {
  answer: string;
  citations: CitationInfo[];
  confidence: string;
  confidence_score?: ConfidenceScore;
  validation?: ValidationResult;
  processing_time_ms: number;
  session_id?: string;
}

export interface AskRequest {
  question: string;
  top_k?: number;
  document_type?: string;
  session_id?: string;
}

export async function askQuestion(
  question: string,
  topK: number = 5,
  sessionId?: string
): Promise<AskResponse> {
  const body: Record<string, unknown> = { question, top_k: topK };
  if (sessionId) body.session_id = sessionId;

  const response = await fetch(`${API_URL}/api/v1/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal mendapatkan jawaban' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }
  
  return response.json();
}

// Chat Session Types & API
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
}

export async function fetchChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const response = await fetch(`${API_URL}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Sesi tidak ditemukan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal menghapus sesi' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }
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
  citations: CitationInfo[];
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

  const response = await fetch(`${API_URL}/api/v1/compliance/check`, {
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
  const response = await fetch(`${API_URL}/api/v1/guidance`, {
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

// Streaming types and function
export interface StreamMetadata {
  citations: CitationInfo[];
  sources: string[];
  confidence_score: ConfidenceScore;
}

export interface StreamDone {
  validation: ValidationResult;
  processing_time_ms: number;
}

export interface StreamCallbacks {
  onMetadata?: (metadata: StreamMetadata) => void;
  onChunk?: (text: string) => void;
  onDone?: (data: StreamDone) => void;
  onError?: (error: Error) => void;
}

/**
 * Stream a question answer from the backend using Server-Sent Events.
 * Provides real-time text chunks as the LLM generates the response.
 */
export async function askQuestionStream(
  question: string,
  callbacks: StreamCallbacks,
  topK: number = 5
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal mendapatkan jawaban' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ') && currentEvent) {
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            
            if (currentEvent === 'metadata' && callbacks.onMetadata) {
              callbacks.onMetadata(parsed as StreamMetadata);
            } else if (currentEvent === 'chunk' && callbacks.onChunk) {
              callbacks.onChunk(parsed.text);
            } else if (currentEvent === 'done' && callbacks.onDone) {
              callbacks.onDone(parsed as StreamDone);
            } else if (currentEvent === 'error' && callbacks.onError) {
              callbacks.onError(new Error(parsed.error));
            }
          } catch {
            // Ignore JSON parse errors
          }
          currentEvent = '';
        }
      }
    }
  } catch (err) {
    if (callbacks.onError) {
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
    throw err;
  }
}

// Knowledge Graph Types
export type GraphNodeType = 'law' | 'government_regulation' | 'presidential_regulation' | 'ministerial_regulation' | 'chapter' | 'article';
export type GraphNodeStatus = 'active' | 'amended' | 'repealed';

export interface GraphNode {
  id: string;
  node_type: GraphNodeType;
  number: number | string;
  year?: number;
  title?: string;
  about?: string;
  status?: GraphNodeStatus;
  full_text?: string;
  children?: GraphNode[];
}

export interface GraphHierarchy {
  law: GraphNode;
  implementing_regulations: GraphNode[];
  amendments: GraphNode[];
}

export interface GraphReference {
  source_id: string;
  target_id: string;
  edge_type: string;
  source_node: GraphNode;
  target_node: GraphNode;
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

export async function fetchGraphLaws(filters?: {
  status?: string;
  year?: number;
  node_type?: string;
}): Promise<GraphNode[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set('status', filters.status);
  if (filters?.year) params.set('year', String(filters.year));
  if (filters?.node_type) params.set('node_type', filters.node_type);

  const query = params.toString();
  const url = `${API_URL}/api/v1/graph/laws${query ? `?${query}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal memuat data graf' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchGraphLaw(lawId: string): Promise<GraphNode> {
  const response = await fetch(`${API_URL}/api/v1/graph/law/${encodeURIComponent(lawId)}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Regulasi tidak ditemukan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchGraphHierarchy(lawId: string): Promise<GraphHierarchy> {
  const response = await fetch(`${API_URL}/api/v1/graph/law/${encodeURIComponent(lawId)}/hierarchy`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Hierarki tidak ditemukan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchGraphArticleReferences(articleId: string): Promise<GraphReference[]> {
  const response = await fetch(`${API_URL}/api/v1/graph/article/${encodeURIComponent(articleId)}/references`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Referensi tidak ditemukan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchGraphSearch(query: string, nodeType?: string): Promise<GraphNode[]> {
  const params = new URLSearchParams({ q: query });
  if (nodeType) params.set('node_type', nodeType);

  const response = await fetch(`${API_URL}/api/v1/graph/search?${params.toString()}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Pencarian gagal' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchGraphStats(): Promise<GraphStats> {
  const response = await fetch(`${API_URL}/api/v1/graph/stats`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal memuat statistik' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

// Dashboard Types & API
export interface LawCoverage {
  regulation_id: string;
  regulation_type: string;
  title: string;
  about: string;
  domain: string;
  total_articles: number;
  indexed_articles: number;
  missing_articles: string[];
  coverage_percent: number;
  total_chapters: number;
}

export interface DomainCoverage {
  domain: string;
  total_articles: number;
  indexed_articles: number;
  coverage_percent: number;
  regulation_count: number;
  laws: LawCoverage[];
}

export interface DashboardStats {
  overall_coverage_percent: number;
  total_regulations: number;
  total_articles: number;
  total_chapters: number;
  indexed_articles: number;
  total_edges: number;
  domain_count: number;
  most_covered_domain: string | null;
  least_covered_domain: string | null;
  last_updated: string;
}

export async function fetchDashboardCoverage(): Promise<LawCoverage[]> {
  const response = await fetch(`${API_URL}/api/v1/dashboard/coverage`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal memuat data coverage' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_URL}/api/v1/dashboard/stats`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Gagal memuat statistik dashboard' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}

export async function fetchDomainCoverage(domain: string): Promise<DomainCoverage> {
  const response = await fetch(`${API_URL}/api/v1/dashboard/coverage/${encodeURIComponent(domain)}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Domain tidak ditemukan' }));
    throw new Error(error.detail || 'Terjadi kesalahan pada server');
  }

  return response.json();
}
