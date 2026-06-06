"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSelfAssessment, useSubmitSelfAssessment } from "@/lib/hooks/use-videos";

const RATING_FIELDS = [
  { key: "hook_score", label: "Hook", hint: "How well does your opening grab attention?" },
  { key: "structure_score", label: "Structure", hint: "Is the video well-organized?" },
  { key: "clarity_score", label: "Clarity", hint: "Are your explanations easy to follow?" },
  { key: "cta_score", label: "Call to Action", hint: "How compelling is your CTA?" },
  { key: "energy_score", label: "Energy", hint: "How's your vocal energy and enthusiasm?" },
  { key: "pacing_score", label: "Pacing", hint: "Is the video too fast, too slow, or just right?" },
  { key: "visual_score", label: "Visuals", hint: "Quality of visuals, B-roll, overlays?" },
] as const;

type RatingKey = (typeof RATING_FIELDS)[number]["key"];

interface Props {
  videoId: string;
}

export function SelfAssessmentForm({ videoId }: Props) {
  const { data: existing, isError } = useSelfAssessment(videoId);
  const submitMutation = useSubmitSelfAssessment();
  const [ratings, setRatings] = useState<Record<RatingKey, number | null>>({
    hook_score: null,
    structure_score: null,
    clarity_score: null,
    cta_score: null,
    energy_score: null,
    pacing_score: null,
    visual_score: null,
  });
  const [bestPart, setBestPart] = useState("");
  const [wouldChange, setWouldChange] = useState("");

  // Already submitted
  if (existing && !isError) {
    return (
      <Card className="border-emerald-500/30 bg-emerald-500/5">
        <CardContent className="flex items-center gap-3 py-4">
          <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          <div>
            <p className="text-sm font-medium">Self-assessment saved</p>
            <p className="text-xs text-muted-foreground">
              Your ratings will be compared with the AI analysis once it completes.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submitMutation.mutate(
      {
        videoId,
        data: {
          ...ratings,
          best_part: bestPart || null,
          would_change: wouldChange || null,
        },
      },
      {
        onSuccess: () => toast.success("Self-assessment saved!"),
        onError: () => toast.error("Failed to save assessment"),
      },
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Rate Yourself First</CardTitle>
        <CardDescription>
          Before seeing the AI analysis, rate your own video. We'll show you where your
          self-awareness matches — and where you have blind spots.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            {RATING_FIELDS.map((field) => (
              <div key={field.key}>
                <div className="mb-1.5 flex items-baseline justify-between">
                  <label className="text-sm font-medium">{field.label}</label>
                  <span className="text-xs text-muted-foreground">
                    {ratings[field.key] ?? "—"}/10
                  </span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={ratings[field.key] ?? 5}
                  onChange={(e) =>
                    setRatings((prev) => ({
                      ...prev,
                      [field.key]: parseInt(e.target.value),
                    }))
                  }
                  className="w-full accent-primary"
                />
                <p className="mt-0.5 text-[10px] text-muted-foreground">{field.hint}</p>
              </div>
            ))}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              What do you think worked best?
            </label>
            <textarea
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              rows={2}
              placeholder="e.g. The intro hook, the way I explained the concept..."
              value={bestPart}
              onChange={(e) => setBestPart(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">
              What would you change if you could re-record?
            </label>
            <textarea
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              rows={2}
              placeholder="e.g. Better pacing in the middle, stronger CTA..."
              value={wouldChange}
              onChange={(e) => setWouldChange(e.target.value)}
            />
          </div>

          <Button type="submit" className="w-full" disabled={submitMutation.isPending}>
            {submitMutation.isPending ? "Saving..." : "Save Self-Assessment"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
