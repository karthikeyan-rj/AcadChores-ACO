'use client';

import React, { useState, useMemo } from 'react';
import {
  BarChart3, TrendingUp, Clock, CheckCircle2, XCircle, Activity,
  Download, Calendar, ArrowUpRight, ArrowDownRight, Loader2
} from 'lucide-react';
import { cn, statusColor } from '@/lib/utils';
import { useExecutions } from '@/lib/hooks';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Area, AreaChart, Legend
} from 'recharts';

type TimeRange = '7d' | '30d' | '90d';
const COLORS = ['#7C3AED', '#4ADE80', '#F87171', '#FBBF24', '#71717A'];

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
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto bg-[#08090B] min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#F4F4F5]">Analytics</h1>
          <p className="text-xs text-[#71717A] mt-0.5">Execution performance and usage metrics</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-[#181B21] rounded-lg p-0.5">
            {(['7d', '30d', '90d'] as TimeRange[]).map(r => (
              <button key={r} onClick={() => setRange(r)}
                className={cn('px-3 py-1 rounded-md text-[11px] font-medium transition cursor-pointer',
                  range === r ? 'bg-[#7C3AED]/12 text-[#7C3AED]' : 'text-[#71717A] hover:text-[#F4F4F5]')}>
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 size={24} className="animate-spin text-[#71717A]" /></div>
      ) : (
        <>
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Total Executions" value={stats.total} icon={<Activity size={16} />} color="text-[#7C3AED]" />
            <StatCard label="Completed" value={stats.completed} icon={<CheckCircle2 size={16} />} color="text-[#4ADE80]" />
            <StatCard label="Failed" value={stats.failed} icon={<XCircle size={16} />} color="text-[#F87171]" />
            <StatCard label="Success Rate" value={`${stats.successRate}%`} icon={<TrendingUp size={16} />} color={stats.successRate > 80 ? 'text-[#4ADE80]' : 'text-[#FBBF24]'} />
            <StatCard label="Avg Duration" value={formatMs(stats.avgDuration)} icon={<Clock size={16} />} color="text-[#7C3AED]" />
          </div>

          {/* Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Daily executions bar chart */}
            <div className="lg:col-span-2 rounded-[14px] border border-white/[0.07] bg-[#121419] p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#71717A] mb-4">Daily Executions</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#71717A' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#71717A' }} />
                  <Tooltip
                    contentStyle={{ background: '#121419', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '10px', fontSize: '11px', color: '#F4F4F5' }}
                    labelStyle={{ color: '#A1A1AA' }}
                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                  />
                  <Bar dataKey="completed" fill="#4ADE80" radius={[3, 3, 0, 0]} name="Completed" />
                  <Bar dataKey="failed" fill="#F87171" radius={[3, 3, 0, 0]} name="Failed" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Status pie chart */}
            <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[#71717A] mb-4">Status Distribution</h3>
              {statusData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45}>
                      {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#121419', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '10px', fontSize: '11px', color: '#F4F4F5' }}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '10px' }}
                      formatter={(value: string) => <span style={{ color: '#A1A1AA' }}>{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[250px] text-[#71717A] text-xs">No data</div>
              )}
            </div>
          </div>

          {/* Hourly activity */}
          <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[#71717A] mb-4">Hourly Activity</h3>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={hourlyData}>
                <defs>
                  <linearGradient id="colorExec" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#7C3AED" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hour" tick={{ fontSize: 9, fill: '#71717A' }} />
                <YAxis tick={{ fontSize: 10, fill: '#71717A' }} />
                <Tooltip
                  contentStyle={{ background: '#121419', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '10px', fontSize: '11px', color: '#F4F4F5' }}
                  cursor={{ stroke: 'rgba(255,255,255,0.07)' }}
                />
                <Area type="monotone" dataKey="executions" stroke="#7C3AED" fillOpacity={1} fill="url(#colorExec)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: any; icon: React.ReactNode; color: string }) {
  return (
    <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-4">
      <div className={cn('mb-2', color)}>{icon}</div>
      <p className="text-lg font-bold text-[#F4F4F5]">{value}</p>
      <p className="text-[10px] text-[#71717A]">{label}</p>
    </div>
  );
}
