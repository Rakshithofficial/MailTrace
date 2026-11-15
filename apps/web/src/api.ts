export type ApiState = "available" | "unavailable" | "loading" | "empty";

export interface ParsedEmail {
  id: string;
  message_id: string | null;
  subject: string | null;
  from: string | null;
  to: string[];
  cc: string[];
  reply_to: string | null;
  date: string | null;
  received: string[];
  authentication_results: string[];
  body_text: string | null;
  body_html: string | null;
  urls: Array<{ value: string; scheme: string; host: string; location: string }>;
  attachments: Array<{ filename: string; content_type: string; size: number; sha256: string }>;
}

export interface InvestigationCase {
  id: string;
  title: string;
  status: string;
  risk_score: number;
  severity: string;
  verdict: string;
  summary?: string | null;
  email?: ParsedEmail;
  analysis?: AnalysisResult;
}

export interface Finding {
  rule_id: string;
  category: string;
  title: string;
  description: string;
  severity: string;
  score_contribution: number;
  evidence: Array<{ type: string; value: string; location: string; source: string }>;
}

export interface AnalysisResult {
  findings: Finding[];
  indicators: Array<{ id: string; type: string; normalized_value: string; source: string }>;
  relationships: Relationship[];
  campaign: Campaign | null;
  infrastructure: { status: string; limitations?: string; [key: string]: unknown };
  enrichment: { status: string; providers: Array<Record<string, unknown>> };
  risk: { score: number; severity: string; contributors: Array<Record<string, unknown>> };
  explanation: { source: string; status: string; summary: string; explanation: string; recommendations: string[]; risk_score: number; severity: string };
  recommendations: Array<{ action: string; reason: string; priority: string; evidence_reference: unknown }>;
  report?: { id: string; format: string; content_reference: string };
}

export interface Relationship {
  id: string;
  source_case_id: string;
  target_case_id: string;
  source_indicator_id: string;
  target_indicator_id: string;
  relationship_type: string;
  strength: string;
  confidence: number;
  evidence: Record<string, string | number>;
}

export interface RelatedCasesResponse {
  case_id: string;
  related_cases: Array<{ id: string; relationship_count: number }>;
  relationships: Relationship[];
}

export interface Campaign {
  id: string;
  name: string;
  confidence: number;
  wording: string;
  case_ids: string[];
  first_seen: string | null;
  last_seen: string | null;
}

export interface CampaignResponse {
  case_id: string;
  campaigns: Campaign[];
}

const API_ROOT = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function readError(response: Response): Promise<never> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = await response.json();
    message = body.error?.message ?? body.detail?.message ?? message;
  } catch {
    // Keep the status message when the server did not return JSON.
  }
  throw new Error(message);
}

export async function createInvestigation(input: {
  file?: File;
  pastedEmail?: string;
  title?: string;
}): Promise<InvestigationCase> {
  const form = new FormData();
  if (input.file) form.append("file", input.file);
  if (input.pastedEmail) {
    form.append("file", new File([input.pastedEmail], "pasted-message.eml", { type: "message/rfc822" }));
  }
  if (input.title) form.append("title", input.title);
  const response = await fetch(`${API_ROOT}/cases`, { method: "POST", body: form });
  if (!response.ok) return readError(response);
  return response.json() as Promise<InvestigationCase>;
}

export async function fetchRelationships(caseId: string): Promise<RelatedCasesResponse> {
  const response = await fetch(`${API_ROOT}/cases/${encodeURIComponent(caseId)}/relationships`);
  if (!response.ok) return readError(response);
  return response.json() as Promise<RelatedCasesResponse>;
}

export async function fetchCampaigns(caseId: string): Promise<CampaignResponse> {
  const response = await fetch(`${API_ROOT}/cases/${encodeURIComponent(caseId)}/campaigns`);
  if (!response.ok) return readError(response);
  return response.json() as Promise<CampaignResponse>;
}

export async function checkApi(): Promise<boolean> {
  const response = await fetch(`${API_ROOT}/health`, { signal: AbortSignal.timeout(2500) });
  return response.ok;
}

export async function createReport(caseId: string, format: "json" | "pdf" = "pdf"): Promise<{ id: string; format: string; content_reference: string }> {
  const response = await fetch(`${API_ROOT}/cases/${encodeURIComponent(caseId)}/report?format=${format}`, { method: "POST" });
  if (!response.ok) return readError(response);
  return response.json();
}
