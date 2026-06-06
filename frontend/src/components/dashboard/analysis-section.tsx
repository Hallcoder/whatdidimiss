"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreCard } from "./score-card";

interface AnalysisSectionProps {
  title: string;
  icon: React.ReactNode;
  data: Record<string, unknown>;
  scoreFields: { key: string; label: string }[];
  textFields?: { key: string; label: string }[];
}

export function AnalysisSection({ title, icon, data, scoreFields, textFields }: AnalysisSectionProps) {
  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {scoreFields.map(({ key, label }) => {
            const score = data[`${key}_score`];
            const feedback = data[`${key}_feedback`];
            if (score == null || !feedback) return null;
            return (
              <ScoreCard
                key={key}
                label={label}
                score={Number(score)}
                feedback={String(feedback)}
              />
            );
          })}
        </div>

        {textFields?.map(({ key, label }) => {
          const value = data[key];
          if (!value) return null;
          return (
            <div key={key} className="space-y-1.5 rounded-lg border border-dashed p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {label}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {String(value)}
              </p>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
