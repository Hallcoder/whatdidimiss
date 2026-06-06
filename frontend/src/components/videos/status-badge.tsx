import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const statusConfig: Record<string, { label: string; className: string }> = {
  completed: { label: "Completed", className: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" },
  failed: { label: "Failed", className: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20" },
  pending: { label: "Pending", className: "bg-zinc-500/15 text-zinc-600 dark:text-zinc-400 border-zinc-500/20" },
};

const processingStatuses = new Set([
  "downloading", "uploading_gcs", "analyzing_video",
  "fetching_analytics", "correlating", "synthesizing",
]);

export function StatusBadge({ status }: { status: string }) {
  const isProcessing = processingStatuses.has(status);
  const config = statusConfig[status] ?? (isProcessing
    ? { label: "Processing", className: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20" }
    : { label: status, className: "bg-zinc-500/15 text-zinc-500 border-zinc-500/20" });

  return (
    <Badge variant="outline" className={cn("text-xs font-medium", config.className)}>
      {isProcessing && (
        <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500" />
      )}
      {config.label}
    </Badge>
  );
}
