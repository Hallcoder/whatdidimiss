import { cn } from "@/lib/utils";

interface ScoreCardProps {
  label: string;
  score: number;
  maxScore?: number;
  feedback: string;
}

const scoreColor = (score: number) => {
  if (score >= 8) return "text-emerald-500";
  if (score >= 6) return "text-blue-500";
  if (score >= 4) return "text-amber-500";
  return "text-red-500";
};

const scoreBg = (score: number) => {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 6) return "bg-blue-500";
  if (score >= 4) return "bg-amber-500";
  return "bg-red-500";
};

export function ScoreCard({ label, score, maxScore = 10, feedback }: ScoreCardProps) {
  return (
    <div className="space-y-2 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className={cn("text-lg font-bold", scoreColor(score))}>
          {score}/{maxScore}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div
          className={cn("h-1.5 rounded-full transition-all", scoreBg(score))}
          style={{ width: `${(score / maxScore) * 100}%` }}
        />
      </div>
      <p className="text-sm leading-relaxed text-muted-foreground">{feedback}</p>
    </div>
  );
}
