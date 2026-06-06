"use client";

import { useTheme } from "next-themes";

export function useChartTheme() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return {
    gridColor: isDark ? "hsl(0 0% 20%)" : "hsl(0 0% 92%)",
    textColor: isDark ? "hsl(0 0% 65%)" : "hsl(0 0% 40%)",
    areaFill: isDark ? "rgba(59, 130, 246, 0.15)" : "rgba(59, 130, 246, 0.1)",
    lineStroke: "hsl(217, 91%, 60%)",
    referenceLine: isDark ? "hsl(0 0% 40%)" : "hsl(0 0% 75%)",
    tooltipBg: isDark ? "hsl(0 0% 12%)" : "hsl(0 0% 100%)",
    tooltipBorder: isDark ? "hsl(0 0% 20%)" : "hsl(0 0% 90%)",
  };
}
