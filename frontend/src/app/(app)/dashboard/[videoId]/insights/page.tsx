"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InsightCard } from "@/components/dashboard/insight-card";
import { useInsights } from "@/lib/hooks/use-insights";

const TABS = [
  { value: "all", label: "All" },
  { value: "win", label: "Wins" },
  { value: "improvement", label: "Improvements" },
  { value: "next_post", label: "Next Post" },
  { value: "creative_tweak", label: "Tweaks" },
];

export default function InsightsPage({
  params,
}: {
  params: Promise<{ videoId: string }>;
}) {
  const { videoId } = use(params);
  const [tab, setTab] = useState("all");
  const typeFilter = tab === "all" ? undefined : tab;
  const { data, isLoading } = useInsights(videoId, typeFilter);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/dashboard/${videoId}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold">All Insights</h1>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={tab} className="mt-4">
          {data?.items.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {data.items.map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-muted-foreground">No insights found.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
