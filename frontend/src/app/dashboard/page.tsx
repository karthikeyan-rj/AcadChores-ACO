'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Play, Globe, GitBranch, Clock, BarChart3,
  Activity, Search, ArrowRight, Loader2,
  CheckCircle2, XCircle, Layers, Cpu, HardDrive, Database,
  RefreshCw
} from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useDashboardMetrics } from '@/lib/hooks';
import { useAuth } from '@/lib/auth';

const quickActions = [
  { icon: Play, label: 'New Workflow', desc: 'Execute a new task', href: '/chat', color: 'text-[#7C3AED]' },
  { icon: Globe, label: 'Open Browser', desc: 'Launch browser session', href: '/chat', color: 'text-[#7C3AED]' },
  { icon: Search, label: 'Search Files', desc: 'Find local files', href: '/files', color: 'text-[#7C3AED]' },
  { icon: BarChart3, label: 'Analytics', desc: 'View metrics', href: '/analytics', color: 'text-[#7C3AED]' },
];

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { metrics, loading, error } = useDashboardMetrics();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  if (!mounted || loading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
        <div className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-8 text-center">
          <XCircle size={32} className="text-[#F87171] mx-auto mb-3" />
          <p className="text-sm font-medium text-[#A1A1AA]">Failed to load dashboard metrics</p>
          <p className="text-xs text-[#71717A] mt-1">{error}</p>
          <button onClick={() => window.location.reload()} className="mt-4 text-xs text-[#7C3AED] hover:underline cursor-pointer">Retry</button>
        </div>
      </div>
    );
  }

  const workflows = metrics?.workflows || {};
  const today = metrics?.today || {};
  const timing = metrics?.timing || {};
  const recovery = metrics?.recovery || {};
  const workers = metrics?.workers || {};
  const recentActivity = metrics?.recent_activity || [];
  const systemInfo = metrics?.system_info || {};

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto bg-[#08090B] min-h-screen">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <h1 className="text-2xl font-bold text-[#F4F4F5]">
          Dashboard
        </h1>
        <p className="text-sm text-[#71717A] mt-1">
          System control center
          {systemInfo.uptime && <span className="ml-2 text-[#71717A]">· Uptime {systemInfo.uptime}</span>}
        </p>
      </motion.div>

      {/* Primary Stats — 6 meaningful metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={<GitBranch size={14} />} label="Running" value={workflows.running || 0} accent={workflows.running > 0} />
        <StatCard icon={<CheckCircle2 size={14} />} label="Completed Today" value={today.completed || 0} />
        <StatCard icon={<Activity size={14} />} label="Success Rate" value={metrics?.success_rate ? `${metrics.success_rate}%` : '—'} accent />
        <StatCard icon={<XCircle size={14} />} label="Failed" value={today.failed || 0} danger={today.failed > 0} />
        <StatCard icon={<Clock size={14} />} label="Avg Runtime" value={timing.avg_execution_time ? `${Math.round(timing.avg_execution_time)}s` : '—'} />
        <StatCard icon={<Layers size={14} />} label="Workers" value={`${workers.busy || 0}/${workers.total || 0}`} />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recent Activity */}
        <div className="lg:col-span-2 rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(255,255,255,0.07)]">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[#71717A]">Recent Activity</span>
            <button onClick={() => router.push('/history')} className="text-[10px] text-[#7C3AED] hover:underline cursor-pointer">View All</button>
          </div>
          <div className="divide-y divide-[rgba(255,255,255,0.07)]">
            {recentActivity.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-[#71717A]">
                <Activity size={24} className="text-[#71717A] mb-2" />
                <p className="text-xs font-medium">No executions yet</p>
                <button onClick={() => router.push('/chat')} className="mt-2 text-[10px] text-[#7C3AED] hover:underline cursor-pointer">Create your first workflow</button>
              </div>
            ) : recentActivity.slice(0, 6).map((ex) => (
              <div key={ex.id} onClick={() => router.push('/history')} className="flex items-center justify-between px-5 py-3 hover:bg-[#0D0F12] cursor-pointer transition group">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-[#F4F4F5] truncate group-hover:text-[#F4F4F5]">{ex.title}</p>
                  <p className="text-[10px] text-[#71717A]">{formatRelativeTime(ex.started_at)}</p>
                </div>
                <StatusPill status={ex.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Right Column — Recovery rate + Quick Actions */}
        <div className="space-y-5">
          <div className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-5 space-y-4">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[#71717A]">Recovery</span>
            <div className="space-y-3">
              <MetricRow label="Recovery Rate" value={recovery.rate ? `${recovery.rate}%` : '—'} />
              <MetricRow label="Total Recovered" value={recovery.total_recovered || 0} />
              <MetricRow label="Total Failed" value={recovery.total_failed || 0} />
            </div>
          </div>

          {/* Quick Actions */}
          <div className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-5 space-y-3">
            <span className="text-[11px] font-medium uppercase tracking-wider text-[#71717A]">Quick Actions</span>
            <div className="grid grid-cols-2 gap-2">
              {quickActions.map((action, i) => (
                <motion.button
                  key={i}
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => router.push(action.href)}
                  className="flex flex-col items-center gap-1.5 p-3 rounded-[10px] border border-[rgba(255,255,255,0.07)] bg-[#0D0F12] hover:bg-[#181B21] hover:border-[rgba(255,255,255,0.12)] transition cursor-pointer text-center"
                >
                  <action.icon size={16} className={action.color} />
                  <span className="text-[11px] font-medium text-[#F4F4F5]">{action.label}</span>
                </motion.button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* System Resources */}
      {systemInfo.cpu_percent > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ResourceCard icon={<Cpu size={14} />} label="CPU" value={`${systemInfo.cpu_percent}%`} percent={systemInfo.cpu_percent} />
          <ResourceCard icon={<HardDrive size={14} />} label="RAM" value={`${systemInfo.ram_used_gb}GB / ${systemInfo.ram_total_gb}GB`} percent={systemInfo.ram_percent} />
          <ResourceCard icon={<Database size={14} />} label="Disk" value={`${systemInfo.disk_used_gb}GB / ${systemInfo.disk_total_gb}GB`} percent={systemInfo.disk_percent} />
        </div>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto bg-[#08090B] min-h-screen">
      <div className="space-y-2">
        <div className="h-8 w-64 bg-[#181B21] rounded-[14px] animate-pulse" />
        <div className="h-4 w-96 bg-[#181B21] rounded-[14px] animate-pulse" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-4 space-y-3">
            <div className="h-3 w-16 bg-[#181B21] rounded animate-pulse" />
            <div className="h-6 w-20 bg-[#181B21] rounded animate-pulse" />
            <div className="h-2 w-24 bg-[#181B21] rounded animate-pulse" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 h-64 bg-[#121419] rounded-[14px] border border-[rgba(255,255,255,0.07)] animate-pulse" />
        <div className="space-y-5">
          <div className="h-48 bg-[#121419] rounded-[14px] border border-[rgba(255,255,255,0.07)] animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, accent, danger }: { icon: React.ReactNode; label: string; value: any; accent?: boolean; danger?: boolean }) {
  return (
    <motion.div whileHover={{ y: -1 }} className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-4 transition-all">
      <div className="mb-2 text-[#71717A]">{icon}</div>
      <p className={cn('text-lg font-bold', danger ? 'text-[#F87171]' : accent ? 'text-[#ADFF2F]' : 'text-[#F4F4F5]')}>{value}</p>
      <p className="text-[10px] text-[#71717A] mt-0.5">{label}</p>
    </motion.div>
  );
}

function MetricRow({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[#71717A]">{label}</span>
      <span className="text-xs font-medium text-[#F4F4F5]">{value}</span>
    </div>
  );
}

function ResourceCard({ icon, label, value, percent }: { icon: React.ReactNode; label: string; value: string; percent: number }) {
  const color = percent > 80 ? '#F87171' : percent > 60 ? '#FBBF24' : '#4ADE80';
  return (
    <div className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[#121419] p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-[#A1A1AA]">
          <span style={{ color }}>{icon}</span>
          {label}
        </span>
        <span className="text-xs font-semibold" style={{ color }}>{percent.toFixed(1)}%</span>
      </div>
      <div className="h-1 bg-[#1E2128] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: color }} />
      </div>
      <p className="text-[10px] text-[#71717A]">{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const colors = s === 'completed' ? 'bg-[#4ADE80]/10 text-[#4ADE80]' : s === 'failed' ? 'bg-[#F87171]/10 text-[#F87171]' : s === 'executing' || s === 'running' ? 'bg-[#7C3AED]/10 text-[#7C3AED]' : 'bg-[#71717A]/10 text-[#71717A]';
  return <span className={cn('text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase', colors)}>{status}</span>;
}
