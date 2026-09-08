import { cn } from "@/lib/utils";

const STATE_STYLES: Record<string, string> = {
  COMPLETED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  DENIED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  ESCALATED: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
};

const DEFAULT_STYLE = "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300";

export function StateBadge({ state }: { state: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        STATE_STYLES[state] ?? DEFAULT_STYLE,
      )}
    >
      {state.replaceAll("_", " ")}
    </span>
  );
}
