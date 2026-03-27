'use client';

import { useState, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useLanguage } from '@/contexts/LanguageContext';

export interface GlassAreaChartDataPoint {
  label: string;
  value: number;
}

interface GlassAreaChartProps {
  title?: string;
  valueLabel?: string;
  value?: number;
  deltaLabel?: string;
  delta?: number;
  data: GlassAreaChartDataPoint[];
  initialIndex?: number;
  valueFormatter?: (v: number) => string;
  className?: string;
}

const defaultFormatter = (v: number): string =>
  v >= 1000 ? `${(v / 1000).toFixed(1)}K` : v.toLocaleString();

export default function GlassAreaChart({
  title,
  valueLabel,
  value,
  deltaLabel,
  delta,
  data,
  initialIndex,
  valueFormatter = defaultFormatter,
  className,
}: GlassAreaChartProps) {
  const { t } = useLanguage();
  const resolvedTitle = title ?? t('chart.statistics');
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const resolvedInitialIndex = initialIndex ?? Math.max(0, data.length - 1);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const displayIndex = activeIndex ?? resolvedInitialIndex;

  const { max, min, points, areaPath, linePath } = useMemo(() => {
    if (data.length === 0) return { max: 0, min: 0, points: [], areaPath: '', linePath: '' };

    const values = data.map((d) => d.value);
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    const range = maxVal - minVal || 1;

    const padding = { top: 40, bottom: 50, left: 16, right: 16 };
    const w = 600;
    const h = 260;
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const pts = data.map((d, i) => ({
      x: padding.left + (i / Math.max(data.length - 1, 1)) * chartW,
      y: padding.top + (1 - (d.value - minVal) / range) * chartH,
      value: d.value,
      label: d.label,
    }));

    // Build smooth curve
    const lineSegments = pts.map((p, i) => {
      if (i === 0) return `M ${p.x} ${p.y}`;
      const prev = pts[i - 1];
      const cpx = (prev.x + p.x) / 2;
      return `C ${cpx} ${prev.y}, ${cpx} ${p.y}, ${p.x} ${p.y}`;
    });

    const lp = lineSegments.join(' ');
    const ap = `${lp} L ${pts[pts.length - 1].x} ${h - padding.bottom} L ${pts[0].x} ${h - padding.bottom} Z`;

    return { max: maxVal, min: minVal, points: pts, areaPath: ap, linePath: lp };
  }, [data]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!svgRef.current || points.length === 0) return;
      const rect = svgRef.current.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 600;

      let closest = 0;
      let closestDist = Infinity;
      points.forEach((p, i) => {
        const dist = Math.abs(p.x - mouseX);
        if (dist < closestDist) {
          closestDist = dist;
          closest = i;
        }
      });
      setActiveIndex(closest);
    },
    [points]
  );

  const handleMouseLeave = useCallback(() => setActiveIndex(null), []);

  const activePoint = points[displayIndex];
  const displayValue = activePoint ? valueFormatter(activePoint.value) : valueLabel ?? '';
  const displayLabel = activePoint?.label ?? '';

  // Compute delta from previous point
  const computedDelta = useMemo(() => {
    if (delta !== undefined) return deltaLabel ?? (delta >= 0 ? `+${valueFormatter(delta)}` : valueFormatter(delta));
    if (!activePoint || displayIndex === 0) return null;
    const prev = data[displayIndex - 1]?.value ?? 0;
    const diff = activePoint.value - prev;
    return diff >= 0 ? `+${valueFormatter(diff)}` : valueFormatter(diff);
  }, [delta, deltaLabel, activePoint, displayIndex, data, valueFormatter]);

  if (data.length === 0) {
    return (
      <div className={cn('relative rounded-2xl p-6 text-center text-muted-foreground', className)}>
        <p className="text-sm">{t('chart.noData')}</p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative rounded-2xl overflow-hidden',
        // Glass morphism
        'bg-background/40 backdrop-blur-2xl',
        'border border-border/30',
        'shadow-soft-lg',
        className
      )}
    >
      {/* Inner highlight overlay */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-b from-white/10 to-transparent dark:from-white/5" />

      {/* Header */}
      <div className="relative z-10 px-6 pt-5 pb-2 space-y-1">
        <p className="text-xs font-medium text-muted-foreground tracking-wide">{resolvedTitle}</p>
        <div className="flex items-baseline gap-2">
          <motion.span
            key={displayValue}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold text-foreground tabular-nums"
          >
            {displayValue}
          </motion.span>
          {computedDelta && (
            <motion.span
              key={computedDelta}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={cn(
                'text-xs font-medium tabular-nums',
                computedDelta.startsWith('+') ? 'text-success' : 'text-destructive'
              )}
            >
              {computedDelta}
            </motion.span>
          )}
        </div>
        {displayLabel && (
          <p className="text-[11px] text-muted-foreground/70">{displayLabel}</p>
        )}
      </div>

      {/* Chart SVG */}
      <svg
        ref={svgRef}
        viewBox="0 0 600 260"
        className="relative z-10 w-full h-auto cursor-crosshair"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="glassAreaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.25} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="glassLineGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.6} />
            <stop offset="50%" stopColor="hsl(var(--primary))" stopOpacity={1} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.6} />
          </linearGradient>
        </defs>

        {/* Area fill */}
        <path d={areaPath} fill="url(#glassAreaFill)" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="url(#glassLineGrad)" strokeWidth="2.5" strokeLinecap="round" />

        {/* Bottom labels */}
        {points.map((p, i) => {
          // Show every nth label to avoid crowding
          const showEvery = Math.max(1, Math.floor(points.length / 7));
          if (i % showEvery !== 0 && i !== points.length - 1) return null;
          return (
            <text
              key={i}
              x={p.x}
              y={245}
              textAnchor="middle"
              className="fill-muted-foreground"
              fontSize="11"
            >
              {p.label}
            </text>
          );
        })}

        {/* Active point indicator */}
        {activePoint && (
          <>
            {/* Vertical line */}
            <line
              x1={activePoint.x}
              y1={40}
              x2={activePoint.x}
              y2={210}
              stroke="hsl(var(--primary))"
              strokeOpacity={0.2}
              strokeWidth={1}
              strokeDasharray="4 3"
            />
            {/* Outer glow */}
            <circle
              cx={activePoint.x}
              cy={activePoint.y}
              r={10}
              fill="hsl(var(--primary))"
              fillOpacity={0.1}
            />
            {/* Dot */}
            <circle
              cx={activePoint.x}
              cy={activePoint.y}
              r={5}
              fill="hsl(var(--primary))"
              stroke="hsl(var(--background))"
              strokeWidth={2}
            />
          </>
        )}
      </svg>
    </div>
  );
}
