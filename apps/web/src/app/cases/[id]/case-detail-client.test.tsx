import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import { CaseDetailClient } from "./case-detail-client";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
  return {
    ...actual,
    apiClient: {
      listPatientOptions: vi.fn(),
      listCases: vi.fn(),
      createCase: vi.fn(),
      getCase: vi.fn(),
      runCase: vi.fn(),
    },
  };
});

const BASE_CASE = {
  case_id: "case_abc123",
  patient_id: "pat_jenkins_001",
  patient_name: "Sarah Jenkins",
  procedure_type: "MRI_LUMBAR_SPINE",
  current_state: "INITIATED",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  clinical_indication: "Chronic lumbar radiculopathy.",
  priority: "ROUTINE",
  transitions: [],
};

describe("CaseDetailClient", () => {
  beforeEach(() => {
    vi.mocked(apiClient.getCase).mockResolvedValue(BASE_CASE);
  });

  it("shows the run button for a not-yet-started case", async () => {
    render(<CaseDetailClient caseId="case_abc123" />);
    await waitFor(() => expect(screen.getByText("Sarah Jenkins")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /run agent/i })).toBeInTheDocument();
  });

  it("running the agent shows the completed banner and tool trace", async () => {
    vi.mocked(apiClient.runCase).mockResolvedValue({
      case_id: "case_abc123",
      status: "COMPLETED",
      is_verified: true,
      final_response: "Verified and completed.",
      current_state: "COMPLETED",
      steps: [
        {
          tool_name: "get_patient_record",
          arguments: { patient_identifier: "pat_jenkins_001" },
          result: { success: true },
          success: true,
        },
      ],
    });
    vi.mocked(apiClient.getCase)
      .mockResolvedValueOnce(BASE_CASE)
      .mockResolvedValue({ ...BASE_CASE, current_state: "COMPLETED" });

    const user = userEvent.setup();
    render(<CaseDetailClient caseId="case_abc123" />);
    await waitFor(() => expect(screen.getByRole("button", { name: /run agent/i })).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /run agent/i }));

    await waitFor(() => expect(screen.getByText(/independently verified/i)).toBeInTheDocument());
    expect(screen.getByText("get_patient_record")).toBeInTheDocument();
  });

  it("shows the escalation banner for an escalated case", async () => {
    vi.mocked(apiClient.getCase).mockResolvedValue({
      ...BASE_CASE,
      current_state: "ESCALATED",
      transitions: [
        {
          from_state: "VERIFYING",
          to_state: "ESCALATED",
          reason: "Independent verification did not confirm expected outcome.",
          actor: "agent",
          transitioned_at: "2026-01-01T00:00:05Z",
        },
      ],
    });
    render(<CaseDetailClient caseId="case_abc123" />);
    await waitFor(() => expect(screen.getByText(/escalated to human staff/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /run agent/i })).not.toBeInTheDocument();
  });
});
