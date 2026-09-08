"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import {
  apiClient,
  ApiError,
  NON_TERMINAL_STATES,
  type CaseDetail,
  type RunCaseResponse,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { StateBadge } from "@/components/state-badge";

const POLL_INTERVAL_MS = 2000;

export function CaseDetailClient({ caseId }: { caseId: string }) {
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [runResult, setRunResult] = useState<RunCaseResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const detail = await apiClient.getCase(caseId);
      setCaseDetail(detail);
      return detail;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
      return null;
    }
  }, [caseId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount
    refresh();
  }, [refresh]);

  // Poll while the case is in a non-terminal state, so a second tab (or this one, during a
  // real-LLM run) sees live progress from the transitions the deterministic sync layer commits
  // as the agent works — see services/agent/src/healthflow_agent/state_sync.py.
  useEffect(() => {
    const isActive = caseDetail ? NON_TERMINAL_STATES.has(caseDetail.current_state) : false;
    if (isActive && !pollRef.current) {
      pollRef.current = setInterval(refresh, POLL_INTERVAL_MS);
    }
    if (!isActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [caseDetail, refresh]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const result = await apiClient.runCase(caseId);
      setRunResult(result);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  if (!caseDetail) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {error ?? "Loading case…"}
        </p>
      </main>
    );
  }

  const canRun = caseDetail.current_state === "INITIATED";

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-8 px-6 py-12 text-zinc-900 dark:text-zinc-50">
      <Link href="/" className="text-sm text-zinc-500 hover:underline dark:text-zinc-400">
        ← All cases
      </Link>

      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{caseDetail.patient_name}</h1>
          <StateBadge state={caseDetail.current_state} />
        </div>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          {caseDetail.procedure_type.replaceAll("_", " ")} · {caseDetail.case_id}
        </p>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          {caseDetail.clinical_indication}
        </p>
      </header>

      {caseDetail.current_state === "COMPLETED" && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
          Independently verified and completed. The agent never declared this DONE itself — an
          authoritative external check confirmed the outcome (PRS §7).
        </div>
      )}
      {caseDetail.current_state === "ESCALATED" && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          Escalated to human staff. If the payer portal reported apparent success but independent
          verification didn&apos;t confirm it, the agent is blocked from declaring completion.
        </div>
      )}

      {canRun && (
        <Button onClick={handleRun} disabled={running}>
          {running ? "Agent running…" : "Run agent"}
        </Button>
      )}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Workflow timeline
        </h2>
        {caseDetail.transitions.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Not started yet — run the agent to begin.
          </p>
        ) : (
          <ol className="flex flex-col gap-2 border-l border-zinc-200 pl-4 dark:border-zinc-800">
            {caseDetail.transitions.map((t, i) => (
              <li key={i} className="text-sm">
                <div className="flex items-center gap-2 font-medium">
                  <span>{t.from_state.replaceAll("_", " ")}</span>
                  <span className="text-zinc-400">→</span>
                  <span>{t.to_state.replaceAll("_", " ")}</span>
                </div>
                <div className="text-zinc-500 dark:text-zinc-400">{t.reason}</div>
              </li>
            ))}
          </ol>
        )}
      </section>

      {runResult && (
        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Agent tool-call trace (last run)
          </h2>
          <ol className="flex flex-col gap-2">
            {runResult.steps.map((step, i) => (
              <li
                key={i}
                className="rounded-lg border border-zinc-200 px-3 py-2 text-xs dark:border-zinc-800"
              >
                <div className="flex items-center justify-between font-mono font-medium">
                  <span>{step.tool_name}</span>
                  <span className={step.success ? "text-emerald-600" : "text-red-600"}>
                    {step.success ? "ok" : "failed"}
                  </span>
                </div>
                <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-zinc-500 dark:text-zinc-400">
                  {JSON.stringify(step.result, null, 2)}
                </pre>
              </li>
            ))}
          </ol>
        </section>
      )}
    </main>
  );
}
