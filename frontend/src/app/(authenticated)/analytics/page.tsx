'use client';

import React, { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import {
  BarChart3, TrendingUp, Clock, CheckCircle2, XCircle, Activity,
  Download, Calendar, ArrowUpRight, ArrowDownRight, Loader2
} from 'lucide-react';
import { cn, statusColor } from '@/lib/utils';
import { useExecutions } from '@/lib/hooks';

const Charts = dynamic(() => import('./charts'), { ssr: false, loading: () => (
  <div className="space-y-5">
    <div className="h-64 rounded-xl bg-surface-2 border border-theme animate-pulse" />
    <div className="h-48 rounded-xl bg-surface-2 border border-theme animate-pulse" />
  </div>
)});

type TimeRange = '7d' | '30d' | '90d';

export default function AnalyticsPage() {
  const { data: executions, loading } = useExecutions();
  const [range, setRange] = useState<TimeRange>('7d');

  const stats = useMemo(() => {
    const now = new Date();
    const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
    const cutoff = new Date(now.getTime() - days * 86400000);
    const recent = executions.filter(e => new Date(e.started_at) >= cutoff);

    const completed = recent.filter(e => e.status === 'completed').length;
    const failed = recent.filter(e => e.status === 'failed').length;
    const running = recent.filter(e => e.status === 'executing' || e.status === 'running').length;
    const total = recent.length;
    const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const durations = recent
      .filter(e => e.completed_at)
      .map(e => new Date(e.completed_at).getTime() - new Date(e.started_at).getTime());
    const avgDuration = durations.length > 0
      ? durations.reduce((a, b) => a + b, 0) / durations.length
      : 0;

    return { total, completed, failed, running, successRate, avgDuration };
  }, [executions, range]);

  const statusData = useMemo(() => {
    const counts: Record<string, number> = {};
    executions.forEach(e => { counts[e.status] = (counts[e.status] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [executions]);

  const dailyData = useMemo(() => {
    const now = new Date();
    const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
    const result: { date: string; completed: number; failed: number; total: number }[] = [];

    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 86400000);
      const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const dayExecs = executions.filter(e => {
        const ed = new Date(e.started_at);
        return ed.toDateString() === d.toDateString();
      });
      result.push({
        date: dateStr,
        completed: dayExecs.filter(e => e.status === 'completed').length,
        failed: dayExecs.filter(e => e.status === 'failed').length,
        total: dayExecs.length,
      });
    }
    return result;
  }, [executions, range]);

  const hourlyData = useMemo(() => {
    const hourCounts: Record<number, number> = {};
    for (let h = 0; h < 24; h++) hourCounts[h] = 0;
    executions.forEach(e => {
      const h = new Date(e.started_at).getHours();
      hourCounts[h]++;
    });
    return Object.entries(hourCounts).map(([hour, count]) => ({
      hour: `${hour}:00`,
      executions: count,
    }));
  }, [executions]);

  const formatMs = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto bg-app min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-theme">Analytics</h1>
          <p className="text-xs text-theme-tertiary mt-0.5">Execution performance and usage metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-surface-2 rounded-lg p-0.5">
            {(['7d', '30d', '90d'] as TimeRange[]).map(r => (
              <button key={r} onClick={() => setRange(r)}
                className={cn('px-3 py-1 rounded-md text-[11px] font-medium transition cursor-pointer',
                  range === r ? 'bg-surface-2 text-theme' : 'text-theme-tertiary hover:text-theme')}>
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 size={24} className="animate-spin text-theme-tertiary" /></div>
      ) : (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Total Executions" value={stats.total} icon={<Activity size={16} />} color="text-theme" />
            <StatCard label="Completed" value={stats.completed} icon={<CheckCircle2 size={16} />} color="text-status-active" />
            <StatCard label="Failed" value={stats.failed} icon={<XCircle size={16} />} color="text-status-error" />
            <StatCard label="Success Rate" value={`${stats.successRate}%`} icon={<TrendingUp size={16} />} color={stats.successRate > 80 ? 'text-status-active' : 'text-status-warning'} />
            <StatCard label="Avg Duration" value={formatMs(stats.avgDuration)} icon={<Clock size={16} />} color="text-theme" />
          </div>

          {/* Charts Grid */}
          <Charts dailyData={dailyData} statusData={statusData} hourlyData={hourlyData} />
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: any; icon: React.ReactNode; color: string }) {
  return (
    <div className="rounded-[14px] border border-theme bg-surface p-4">
      <div className={cn('mb-2', color)}>{icon}</div>
      <p className="text-lg font-bold text-theme">{value}</p>
      <p className="text-[10px] text-theme-tertiary">{label}</p>
    </div>
  );
}
