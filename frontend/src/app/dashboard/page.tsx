'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Play, Globe, GitBranch, Clock, BarChart3,
  Activity, Shield, RefreshCw, Search, ArrowRight, Loader2,
  CheckCircle2, XCircle, Layers, Cpu, HardDrive, Database,
  Brain, FileText, Server
} from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useDashboardMetrics, useBackendHealth } from '@/lib/hooks';
import { useAuth } from '@/lib/auth';
import { SkeletonStat } from '@/components/ui/Skeleton';

const quickActions = [
  { icon: Play, label: 'New Workflow', desc: 'Execute a new task', href: '/chat', color: 'text-primary' },
  { icon: Globe, label: 'Open Browser', desc: 'Launch browser session', href: '/chat', color: 'text-blue-400' },
  { icon: Search, label: 'Search Files', desc: 'Find local files', href: '/files', color: 'text-amber-400' },
  { icon: BarChart3, label: 'Analytics', desc: 'View metrics', href: '/analytics', color: 'text-emerald-400' },
];

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const connected = useBackendHealth();
  const { metrics, loading, error } = useDashboardMetrics();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  if (!mounted || loading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <XCircle size={32} className="text-danger mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-400">Failed to load dashboard metrics</p>
          <p className="text-xs text-gray-600 mt-1">{error}</p>
          <button onClick={() => window.location.reload()} className="mt-4 text-xs text-primary hover:underline cursor-pointer">Retry</button>
        </div>
      </div>
    );
  }

  const workflows = metrics?.workflows || {};
  const today = metrics?.today || {};
  const timing = metrics?.timing || {};
  const verification = metrics?.verification || {};
  const recovery = metrics?.recovery || {};
  const workers = metrics?.workers || {};
  const queue = metrics?.queue || {};
  const ai = metrics?.ai || {};
  const files = metrics?.files || {};
  const memory = metrics?.memory || {};
  const systemHealth = metrics?.system_health || {};
  const systemInfo = metrics?.system_info || {};
  const recentActivity = metrics?.recent_activity || [];

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <h1 className="text-2xl font-bold text-foreground">
          Welcome back, {user?.name?.split(' ')[0] || 'Operator'}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Autonomous Computer Operator — Enterprise Orchestrator v1.0
          {systemInfo.uptime && <span className="ml-2 text-gray-600">• Uptime: {systemInfo.uptime}</span>}
        </p>
      </motion.div>

      {/* Primary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={<GitBranch size={16} />} label="Running" value={workflows.running || 0} color="text-primary" />
        <StatCard icon={<CheckCircle2 size={16} />} label="Completed Today" value={today.completed || 0} color="text-accent" />
        <StatCard icon={<Shield size={16} />} label="Success Rate" value={metrics?.success_rate ? `${metrics.success_rate}%` : '—'} color="text-accent" />
        <StatCard icon={<RefreshCw size={16} />} label="Recovery Rate" value={recovery.rate ? `${recovery.rate}%` : '—'} color="text-blue-400" />
        <StatCard icon={<CheckCircle2 size={16} />} label="Verification" value={verification.rate ? `${verification.rate}%` : '—'} color="text-cyan-400" />
        <StatCard icon={<Clock size={16} />} label="Avg Runtime" value={timing.avg_execution_time ? `${Math.round(timing.avg_execution_time)}s` : '—'} color="text-amber-400" />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={<Activity size={16} />} label="Total Executions" value={metrics?.total_executions || 0} color="text-purple-400" />
        <StatCard icon={<XCircle size={16} />} label="Failed" value={today.failed || 0} color="text-danger" />
        <StatCard icon={<Layers size={16} />} label="Workers" value={`${workers.busy || 0}/${workers.total || 0}`} color="text-blue-400" />
        <StatCard icon={<Brain size={16} />} label="AI Provider" value={ai.current_provider || '—'} color="text-purple-400" />
        <StatCard icon={<FileText size={16} />} label="Files Indexed" value={files.indexed_files || 0} color="text-amber-400" />
        <StatCard
          icon={<span className={cn('h-2 w-2 rounded-full', connected ? 'bg-accent' : 'bg-danger')} />}
          label="Backend"
          value={connected ? 'Online' : 'Offline'}
          color={connected ? 'text-accent' : 'text-danger'}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recent Activity */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-border">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Recent Activity</span>
            <button onClick={() => router.push('/history')} className="text-[10px] text-primary hover:underline cursor-pointer">View All</button>
          </div>
          <div className="divide-y divide-border">
            {recentActivity.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-gray-500">
                <Activity size={28} className="text-gray-600 mb-2" />
                <p className="text-xs font-medium">No executions yet</p>
                <button onClick={() => router.push('/chat')} className="mt-2 text-[10px] text-primary hover:underline cursor-pointer">Create your first workflow</button>
              </div>
            ) : recentActivity.slice(0, 6).map((ex) => (
              <div key={ex.id} onClick={() => router.push('/history')} className="flex items-center justify-between px-5 py-3 hover:bg-surface-2 cursor-pointer transition group">
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate group-hover:text-foreground">{ex.title}</p>
                  <p className="text-[10px] text-gray-500">{formatRelativeTime(ex.started_at)}</p>
                </div>
                <StatusPill status={ex.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-5">
          {/* System Health */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">System Health</span>
              <span className={cn('text-[10px] font-medium', connected ? 'text-accent' : 'text-danger')}>
                {connected ? 'All Systems Operational' : 'Degraded'}
              </span>
            </div>
            <div className="space-y-3">
              <HealthRow label="Backend API" active={systemHealth.backend?.status === 'healthy'} />
              <HealthRow label="MongoDB" active={systemHealth.mongodb?.status === 'healthy'} />
              <HealthRow label="Redis" active={systemHealth.redis?.status === 'healthy'} />
              <HealthRow label="AI Provider" active={systemHealth.ai_provider?.status === 'healthy'} />
              <HealthRow label="Worker Pool" active={systemHealth.worker_pool?.status === 'healthy'} />
              <HealthRow label="Event Bus" active={systemHealth.event_bus?.status === 'healthy'} />
              <HealthRow label="File Indexer" active={systemHealth.file_indexer?.status === 'running'} />
            </div>
          </div>

          {/* AI Performance */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">AI Performance</span>
            <div className="space-y-3">
              <MetricRow label="Total Requests" value={ai.total_requests || 0} />
              <MetricRow label="Total Tokens" value={ai.total_tokens ? `${(ai.total_tokens / 1000).toFixed(1)}k` : '0'} />
              <MetricRow label="Avg Response" value={ai.avg_response_ms ? `${ai.avg_response_ms}ms` : '—'} />
              <MetricRow label="Providers" value={ai.provider_count || 0} />
            </div>
          </div>

          {/* Queue & Workers */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Workers & Queue</span>
            <div className="space-y-3">
              <MetricRow label="Queue Length" value={queue.tasks_waiting || 0} />
              <MetricRow label="Completed Jobs" value={workers.completed_jobs || 0} />
              <MetricRow label="Failed Jobs" value={workers.failed_jobs || 0} />
            </div>
          </div>
        </div>
      </div>

      {/* System Resources */}
      {systemInfo.cpu_percent > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ResourceCard icon={<Cpu size={16} />} label="CPU" value={`${systemInfo.cpu_percent}%`} percent={systemInfo.cpu_percent} />
          <ResourceCard icon={<HardDrive size={16} />} label="RAM" value={`${systemInfo.ram_used_gb}GB / ${systemInfo.ram_total_gb}GB`} percent={systemInfo.ram_percent} />
          <ResourceCard icon={<Database size={16} />} label="Disk" value={`${systemInfo.disk_used_gb}GB / ${systemInfo.disk_total_gb}GB`} percent={systemInfo.disk_percent} />
        </div>
      )}

      {/* Quick Actions */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {quickActions.map((action, i) => (
            <motion.button
              key={i}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => router.push(action.href)}
              className="flex flex-col items-center gap-2 p-4 rounded-xl border border-border bg-card hover:bg-card-hover hover:border-border-light transition cursor-pointer text-center"
            >
              <action.icon size={20} className={action.color} />
              <span className="text-xs font-medium text-foreground">{action.label}</span>
              <span className="text-[10px] text-gray-500">{action.desc}</span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto">
      <div className="space-y-2">
        <div className="h-8 w-64 bg-surface-2 rounded animate-pulse" />
        <div className="h-4 w-96 bg-surface-2 rounded animate-pulse" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 12 }).map((_, i) => <SkeletonStat key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 h-64 bg-surface-2 rounded-xl animate-pulse" />
        <div className="space-y-5">
          <div className="h-48 bg-surface-2 rounded-xl animate-pulse" />
          <div className="h-32 bg-surface-2 rounded-xl animate-pulse" />
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: any; color: string }) {
  return (
    <motion.div whileHover={{ y: -1 }} className="rounded-xl border border-border bg-card p-4 transition-all">
      <div className={cn('mb-2', color)}>{icon}</div>
      <p className="text-lg font-bold text-foreground">{value}</p>
      <p className="text-[10px] text-gray-500">{label}</p>
    </motion.div>
  );
}

function HealthRow({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-xs text-gray-400">
        {label}
      </span>
      <span className="flex items-center gap-1.5">
        <span className={cn('h-1.5 w-1.5 rounded-full', active ? 'bg-accent' : 'bg-danger')} />
        <span className={cn('text-[10px] font-medium', active ? 'text-accent' : 'text-danger')}>
          {active ? 'Healthy' : 'Down'}
        </span>
      </span>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-xs font-medium text-foreground">{value}</span>
    </div>
  );
}

function ResourceCard({ icon, label, value, percent }: { icon: React.ReactNode; label: string; value: string; percent: number }) {
  const color = percent > 80 ? 'text-danger' : percent > 60 ? 'text-amber-400' : 'text-accent';
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-gray-400">
          <span className={color}>{icon}</span>
          {label}
        </span>
        <span className={cn('text-xs font-semibold', color)}>{percent.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', percent > 80 ? 'bg-danger' : percent > 60 ? 'bg-amber-400' : 'bg-accent')} style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <p className="text-[10px] text-gray-500">{value}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const colors = s === 'completed' ? 'bg-accent/10 text-accent' : s === 'failed' ? 'bg-danger/10 text-danger' : s === 'executing' || s === 'running' ? 'bg-primary/10 text-primary' : 'bg-gray-500/10 text-gray-400';
  return <span className={cn('text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase', colors)}>{status}</span>;
}
