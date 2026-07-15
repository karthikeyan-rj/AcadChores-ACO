'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, Search, Plus, Clock, CheckCircle2, XCircle, ArrowUpDown, Loader2 } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration, statusColor, statusBg } from '@/lib/utils';
import { useExecutions } from '@/lib/hooks';
import { SkeletonList } from '@/components/ui/Skeleton';

const filterOptions = ['All', 'Completed', 'Failed', 'Running', 'Cancelled'];
type SortBy = 'newest' | 'oldest' | 'status';

export default function WorkflowsPage() {
  const router = useRouter();
  const { data: executions, loading, refresh } = useExecutions();
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortBy>('newest');

  let filtered = executions.filter(ex => {
    if (filter !== 'All' && ex.status.toLowerCase() !== filter.toLowerCase()) return false;
    if (search && !ex.description?.toLowerCase().includes(search.toLowerCase()) && !ex.title?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // Sort
  filtered = [...filtered].sort((a, b) => {
    if (sortBy === 'newest') return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
    if (sortBy === 'oldest') return new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
    const order: Record<string, number> = { executing: 0, running: 0, failed: 1, cancelled: 2, completed: 3 };
    return (order[a.status.toLowerCase()] ?? 4) - (order[b.status.toLowerCase()] ?? 4);
  });

  const runningCount = executions.filter(e => e.status === 'executing' || e.status === 'running').length;

  const isRunning = (status: string) => status === 'executing' || status === 'running';

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#F4F4F5]">Workflows</h1>
          <p className="text-xs text-[#71717A] mt-0.5">
            {filtered.length} workflows{runningCount > 0 ? <span className="text-[#ADFF2F]"> · {runningCount} running</span> : ''}
          </p>
        </div>
        <button onClick={() => router.push('/chat')}
          className="flex items-center gap-2 px-4 py-2 bg-[#7C3AED] hover:bg-[#6D28D9] text-white text-xs font-semibold rounded-lg transition cursor-pointer">
          <Plus size={14} />New Workflow
        </button>
      </div>

      {/* Filters + Search + Sort */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <input type="text" placeholder="Search workflows..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-lg text-[#F4F4F5] placeholder:text-[#71717A] outline-none focus:border-[#7C3AED]/40 transition" />
        </div>
        <div className="flex gap-1">
          {filterOptions.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                filter === f
                  ? 'bg-[#7C3AED]/12 text-[#7C3AED] border-[#7C3AED]/30'
                  : 'bg-[#181B21] border-white/[0.07] text-[#71717A] hover:text-[#A1A1AA]')}>
              {f}
            </button>
          ))}
        </div>
        <div className="relative">
          <button onClick={() => setSortBy(p => p === 'newest' ? 'oldest' : p === 'oldest' ? 'status' : 'newest')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-[#181B21] border border-white/[0.07] text-[#71717A] hover:text-[#A1A1AA] transition cursor-pointer">
            <ArrowUpDown size={12} />
            {sortBy === 'newest' ? 'Newest' : sortBy === 'oldest' ? 'Oldest' : 'By Status'}
          </button>
        </div>
      </div>

      {/* Workflow Cards */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-4 space-y-3 animate-pulse">
              <div className="h-3 w-16 bg-[#181B21] rounded" />
              <div className="h-4 w-3/4 bg-[#181B21] rounded" />
              <div className="flex gap-3">
                <div className="h-3 w-20 bg-[#181B21] rounded" />
                <div className="h-3 w-14 bg-[#181B21] rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <GitBranch size={32} className="text-[#71717A] mb-3" />
          <p className="text-sm font-medium text-[#A1A1AA]">No workflows found</p>
          <p className="text-xs text-[#71717A] mt-1 mb-4">
            {search ? 'Try a different search term' : 'Create your first workflow to get started'}
          </p>
          <button onClick={() => router.push('/chat')}
            className="flex items-center gap-2 px-4 py-2 bg-[#7C3AED] hover:bg-[#6D28D9] text-white text-xs font-semibold rounded-lg transition cursor-pointer">
            <Plus size={14} />Create Workflow
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <AnimatePresence>
            {filtered.map((ex, i) => (
              <motion.div key={ex._id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                onClick={() => router.push('/chat')}
                className="rounded-[14px] border border-white/[0.07] bg-[#121419] hover:bg-[#181B21] transition p-4 cursor-pointer group relative">
                <div className="flex items-start justify-between mb-2">
                  <span className={cn(
                    'text-[10px] font-semibold uppercase px-2 py-0.5 rounded',
                    isRunning(ex.status) ? 'bg-[#ADFF2F]/10 text-[#ADFF2F]' : cn(statusBg(ex.status), statusColor(ex.status))
                  )}>{ex.status}</span>
                </div>
                <p className="text-sm font-medium truncate mb-1 text-[#F4F4F5]">{ex.description || ex.title || `Workflow ${ex._id.slice(-6)}`}</p>
                <div className="flex items-center gap-3 text-[10px] text-[#71717A]">
                  <span className="flex items-center gap-1"><Clock size={10} />{formatRelativeTime(ex.started_at)}</span>
                  {ex.completed_at && <span className="flex items-center gap-1 text-[#4ADE80]">{formatDuration(ex.started_at, ex.completed_at)}</span>}
                  <span>{ex.current_step_index}/{ex.total_steps} steps</span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
