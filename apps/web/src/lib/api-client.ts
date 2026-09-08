/**
 * Typed client for the HealthFlow API (apps/api).
 *
 * The frontend never touches the domain, the database, or the agent directly — it only calls this
 * REST boundary (docs/architecture/ARCHITECTURE.md §4.2, §17.9).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface PatientOption {
  patient_id: string;
  name: string;
  scenario: string;
  procedure_type: string;
}

export interface CaseSummary {
  case_id: string;
  patient_id: string;
  patient_name: string;
  procedure_type: string;
  current_state: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTransition {
  from_state: string;
  to_state: string;
  reason: string;
  actor: string;
  transitioned_at: string;
}

export interface CaseDetail extends CaseSummary {
  clinical_indication: string;
  priority: string;
  transitions: WorkflowTransition[];
}

export interface ToolCallStep {
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  success: boolean;
}

export interface RunCaseResponse {
  case_id: string;
  status: string;
  is_verified: boolean;
  final_response: string;
  current_state: string;
  steps: ToolCallStep[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `Request to ${path} failed`, response.status);
  }
  return response.json() as Promise<T>;
}

export const apiClient = {
  listPatientOptions: () => request<PatientOption[]>("/cases/patients"),
  listCases: () => request<CaseSummary[]>("/cases"),
  createCase: (patientId: string) =>
    request<CaseDetail>("/cases", {
      method: "POST",
      body: JSON.stringify({ patient_id: patientId }),
    }),
  getCase: (caseId: string) => request<CaseDetail>(`/cases/${caseId}`),
  runCase: (caseId: string) => request<RunCaseResponse>(`/cases/${caseId}/run`, { method: "POST" }),
};

/** Non-terminal workflow states — the dashboard keeps polling a case while it's one of these. */
export const NON_TERMINAL_STATES = new Set([
  "INITIATED",
  "GATHERING_INFORMATION",
  "VALIDATING",
  "PREPARING_SUBMISSION",
  "SUBMITTED",
  "MONITORING",
  "FOLLOW_UP_REQUIRED",
  "VERIFYING",
]);
