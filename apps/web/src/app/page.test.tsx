import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

import DashboardPage from "./page";
import { apiClient } from "@/lib/api-client";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

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

const PATIENTS = [
  { patient_id: "pat_jenkins_001", name: "Sarah Jenkins", scenario: "SUCCESS", procedure_type: "MRI_LUMBAR_SPINE" },
  { patient_id: "pat_chen_006", name: "Olivia Chen", scenario: "FALSE_SUCCESS", procedure_type: "MRI_CERVICAL_SPINE" },
];

const CASES = [
  {
    case_id: "case_abc123",
    patient_id: "pat_jenkins_001",
    patient_name: "Sarah Jenkins",
    procedure_type: "MRI_LUMBAR_SPINE",
    current_state: "COMPLETED",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:01Z",
  },
];

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.mocked(apiClient.listPatientOptions).mockResolvedValue(PATIENTS);
    vi.mocked(apiClient.listCases).mockResolvedValue(CASES);
    push.mockClear();
  });

  it("renders the HealthFlow heading", async () => {
    render(<DashboardPage />);
    const heading = screen.getByRole("heading", { level: 1, name: /HealthFlow/i });
    expect(heading).toBeInTheDocument();
  });

  it("lists existing cases once loaded", async () => {
    render(<DashboardPage />);
    await waitFor(() => expect(screen.getByText("Sarah Jenkins")).toBeInTheDocument());
    expect(screen.getByText(/COMPLETED/i)).toBeInTheDocument();
  });

  it("creates a case for the selected patient and navigates to it", async () => {
    vi.mocked(apiClient.createCase).mockResolvedValue({
      case_id: "case_new001",
      patient_id: "pat_jenkins_001",
      patient_name: "Sarah Jenkins",
      procedure_type: "MRI_LUMBAR_SPINE",
      current_state: "INITIATED",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      clinical_indication: "test",
      priority: "ROUTINE",
      transitions: [],
    });
    const user = userEvent.setup();
    render(<DashboardPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /start case/i })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: /start case/i }));

    await waitFor(() => expect(apiClient.createCase).toHaveBeenCalledWith("pat_jenkins_001"));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/cases/case_new001"));
  });
});
