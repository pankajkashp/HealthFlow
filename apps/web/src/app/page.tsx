/**
 * HealthFlow — Application shell (Phase 1).
 *
 * This page is a foundation placeholder only.
 * It contains no HealthFlow business logic and no healthcare data.
 * Workflow UI, patient screens, and agent controls are implemented in later phases.
 *
 * Ref: Phase 1 specification §3 (Frontend foundation) and §14 (Application functionality limit).
 */
export default function HomePage(): React.JSX.Element {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-white px-6 dark:bg-zinc-950">
      <div className="flex flex-col items-center gap-6 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          HealthFlow
        </h1>
        <p className="max-w-sm text-base text-zinc-500 dark:text-zinc-400">
          Prior-authorization workflow system — Phase 1 engineering foundation.
        </p>
        <span className="inline-flex items-center rounded-full bg-zinc-100 px-3 py-1 text-sm font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
          Foundation
        </span>
      </div>
    </main>
  );
}
