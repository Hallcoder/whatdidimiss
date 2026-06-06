"use client";

import { ErrorState } from "@/components/ui/error-state";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex items-center justify-center py-20">
      <ErrorState
        title="Dashboard Error"
        message={error.message || "Failed to load dashboard data."}
        onRetry={reset}
      />
    </div>
  );
}
