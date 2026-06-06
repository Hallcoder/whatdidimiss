import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils/format";

interface VideoHeaderProps {
  title: string | null;
  youtubeVideoId: string | null;
  thumbnailUrl: string | null;
  durationSeconds: number | null;
  videoScore: number | null;
}

export function VideoHeader({ title, youtubeVideoId, thumbnailUrl, durationSeconds, videoScore }: VideoHeaderProps) {
  return (
    <div className="flex items-start gap-4">
      <div className="relative shrink-0 overflow-hidden rounded-lg">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="" className="h-20 w-36 object-cover" />
        ) : (
          <div className="h-20 w-36 bg-muted" />
        )}
        {durationSeconds && (
          <Badge className="absolute bottom-1 right-1 bg-black/75 text-[10px] text-white">
            {formatDuration(durationSeconds)}
          </Badge>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-xl font-bold">{title ?? "Untitled Video"}</h1>
        {youtubeVideoId ? (
          <a
            href={`https://www.youtube.com/watch?v=${youtubeVideoId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            View on YouTube
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">Uploaded video</p>
        )}
      </div>
      {videoScore != null && <ScoreRing score={videoScore} />}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 70
      ? "text-emerald-500"
      : score >= 50
        ? "text-amber-500"
        : "text-red-500";

  const strokeColor =
    score >= 70
      ? "stroke-emerald-500"
      : score >= 50
        ? "stroke-amber-500"
        : "stroke-red-500";

  return (
    <div className="relative flex shrink-0 items-center justify-center">
      <svg width="72" height="72" className="-rotate-90">
        <circle
          cx="36"
          cy="36"
          r={radius}
          fill="none"
          className="stroke-muted"
          strokeWidth="5"
        />
        <circle
          cx="36"
          cy="36"
          r={radius}
          fill="none"
          className={strokeColor}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-lg font-bold ${color}`}>{score}</span>
        <span className="text-[9px] text-muted-foreground">SCORE</span>
      </div>
    </div>
  );
}
