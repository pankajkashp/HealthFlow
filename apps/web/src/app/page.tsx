"use client";

/**
 * HealthFlow dashboard — Phase 6.
 *
 * Lets a demo user start a new MRI prior-authorization case from one of the 6 synthetic
 * benchmark patients and see every case's live workflow state. Business rules live entirely in
 * the API/application layer; this page only renders what it fetches (§17.9).
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { apiClient, ApiError, type CaseSummary, type PatientOption } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { StateBadge } from "@/components/state-badge";

const SCENARIO_LABELS: Record<string, string> = {
  SUCCESS: "Standard approval",
  MISSING_DOCUMENT: "Missing document",
  CONFLICTING_INFO: "Conflicting information",
  PAYER_DENIAL: "Payer denial",
  SERVICE_UNAVAILABLE: "Transient service error",
  FALSE_SUCCESS: "False-success (DONE-principle test)",
};

export default function DashboardPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<PatientOption[]>([]);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([apiClient.listPatientOptions(), apiClient.listCases()])
      .then(([patientOptions, caseList]) => {
        setPatients(patientOptions);
        setCases(caseList);
        setSelectedPatientId((current) => current || patientOptions[0]?.patient_id || "");
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateCase() {
    if (!selectedPatientId) return;
    setCreating(true);
    setError(null);
    try {
      const created = await apiClient.createCase(selectedPatientId);
      router.push(`/cases/${created.case_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      setCreating(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-8 px-6 py-12 text-zinc-900 dark:text-zinc-50">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">HealthFlow</h1>
        <p className="max-w-xl text-sm text-zinc-500 dark:text-zinc-400">
          Autonomous MRI prior-authorization agent. The agent reasons; deterministic safety code
          controls every action; independent verification proves completion.
        </p>
      </header>

      <section className="flex flex-col gap-3 rounded-xl border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Start a new case from a synthetic benchmark patient
        </h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <select
            className="flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            disabled={loading || patients.length === 0}
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.name} — {p.procedure_type.replaceAll("_", " ")} (
                {SCENARIO_LABELS[p.scenario] ?? p.scenario})
              </option>
            ))}
          </select>
          <Button onClick={handleCreateCase} disabled={creating || !selectedPatientId}>
            {creating ? "Creating…" : "Start case"}
          </Button>
        </div>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Cases</h2>
        {loading ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</p>
        ) : cases.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            No cases yet. Start one above.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {cases.map((c) => (
              <li key={c.case_id}>
                <Link
                  href={`/cases/${c.case_id}`}
                  className="flex items-center justify-between rounded-lg border border-zinc-200 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
                >
                  <span className="flex flex-col">
                    <span className="font-medium">{c.patient_name}</span>
                    <span className="text-zinc-500 dark:text-zinc-400">
                      {c.procedure_type.replaceAll("_", " ")} · {c.case_id}
                    </span>
                  </span>
                  <StateBadge state={c.current_state} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
