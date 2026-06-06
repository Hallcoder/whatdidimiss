"use client";

import { ErrorState } from "@/components/ui/error-state";

export default function VideosError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex items-center justify-center py-20">
      <ErrorState
        title="Failed to load videos"
        message={error.message || "Could not fetch your video list."}
        onRetry={reset}
      />
    </div>
  );
}
