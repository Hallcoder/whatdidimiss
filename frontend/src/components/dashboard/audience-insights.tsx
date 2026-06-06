"use client";

import { MessageCircle, ThumbsDown, ThumbsUp, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface AudienceInsightsProps {
  data: Record<string, unknown>;
}

const sentimentConfig: Record<string, { color: string; label: string }> = {
  positive: { color: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20", label: "Positive" },
  mixed: { color: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20", label: "Mixed" },
  negative: { color: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/20", label: "Negative" },
};

export function AudienceInsights({ data }: AudienceInsightsProps) {
  if (!data) return null;
  const sentiment = String(data.sentiment || "mixed");
  const config = sentimentConfig[sentiment] || sentimentConfig.mixed;

  const sections = [
    { key: "top_praise", label: "What Viewers Love", icon: <ThumbsUp className="h-4 w-4 text-emerald-500" /> },
    { key: "top_complaints", label: "What They Want Improved", icon: <ThumbsDown className="h-4 w-4 text-amber-500" /> },
    { key: "content_requests", label: "What They Want Next", icon: <MessageCircle className="h-4 w-4 text-blue-500" /> },
    { key: "community_health", label: "Community Health", icon: <Users className="h-4 w-4 text-purple-500" /> },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageCircle className="h-4 w-4" />
          Audience Insights
          <Badge variant="outline" className={config.color}>{config.label}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {sections.map(({ key, label, icon }) => {
          const value = data[key];
          if (!value) return null;
          return (
            <div key={key} className="space-y-1.5">
              <div className="flex items-center gap-2">
                {icon}
                <span className="text-sm font-medium">{label}</span>
              </div>
              <p className="whitespace-pre-wrap pl-6 text-sm leading-relaxed text-muted-foreground">
                {String(value)}
              </p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
