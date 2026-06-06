"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RetentionPoint } from "@/lib/api/types";
import { useChartTheme } from "@/lib/hooks/use-chart-theme";
import { formatMs } from "@/lib/utils/format";

interface RetentionCurveChartProps {
  data: RetentionPoint[];
  title?: string;
  height?: number;
}

export function RetentionCurveChart({
  data,
  title = "Audience Retention",
  height = 280,
}: RetentionCurveChartProps) {
  const theme = useChartTheme();

  const chartData = data.map((point) => ({
    timestamp: point.timestamp_ms,
    watchRatio: point.watch_ratio != null ? Math.round(point.watch_ratio * 100) : 0,
    relativePerf: point.relative_performance != null ? point.relative_performance * 100 : 100,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
            <defs>
              <linearGradient id="retentionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={theme.lineStroke} stopOpacity={0.3} />
                <stop offset="100%" stopColor={theme.lineStroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={theme.gridColor} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(ms) => formatMs(ms)}
              stroke={theme.textColor}
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              stroke={theme.textColor}
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={45}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: theme.tooltipBg,
                border: `1px solid ${theme.tooltipBorder}`,
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelFormatter={(ms) => formatMs(ms as number)}
              formatter={(value, name) => [
                `${Number(value).toFixed(1)}%`,
                name === "watchRatio" ? "Retention" : "vs. Similar",
              ]}
            />
            <ReferenceLine
              y={100}
              stroke={theme.referenceLine}
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{ value: "Average", position: "right", fontSize: 10, fill: theme.textColor }}
            />
            <Area
              type="monotone"
              dataKey="watchRatio"
              stroke={theme.lineStroke}
              strokeWidth={2}
              fill="url(#retentionGradient)"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
