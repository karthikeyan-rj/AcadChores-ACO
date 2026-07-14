'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, Search, Plus, Clock, CheckCircle2, XCircle, ArrowUpDown, Loader2 } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration, statusColor } from '@/lib/utils';
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

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Workflows</h1>
          <p className="text-xs text-gray-500 mt-0.5">{filtered.length} workflows · {executions.filter(e => e.status === 'executing' || e.status === 'running').length} running</p>
        </div>
        <button onClick={() => router.push('/chat')}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl shadow-lg shadow-primary/20 transition cursor-pointer">
          <Plus size={14} />New Workflow
        </button>
      </div>

      {/* Filters + Search + Sort */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input type="text" placeholder="Search workflows..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-surface-2 border border-border rounded-lg outline-none focus:border-primary transition" />
        </div>
        <div className="flex gap-1">
          {filterOptions.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                filter === f ? 'bg-primary/10 text-primary border-primary/30' : 'bg-surface-2 border-border text-gray-400 hover:text-foreground')}>
              {f}
            </button>
          ))}
        </div>
        <div className="relative">
          <button onClick={() => setSortBy(p => p === 'newest' ? 'oldest' : p === 'oldest' ? 'status' : 'newest')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-surface-2 border border-border text-gray-400 hover:text-foreground transition cursor-pointer">
            <ArrowUpDown size={12} />
            {sortBy === 'newest' ? 'Newest' : sortBy === 'oldest' ? 'Oldest' : 'By Status'}
          </button>
        </div>
      </div>

      {/* Workflow Cards */}
      {loading ? (
        <SkeletonList rows={4} />
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <GitBranch size={32} className="text-gray-600 mb-3" />
          <p className="text-sm font-medium">No workflows found</p>
          <p className="text-xs text-gray-600 mt-1 mb-4">
            {search ? 'Try a different search term' : 'Create your first workflow to get started'}
          </p>
          <button onClick={() => router.push('/chat')}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl transition cursor-pointer">
            <Plus size={14} />Create Workflow
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <AnimatePresence>
            {filtered.map((ex, i) => (
              <motion.div key={ex._id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                className="rounded-xl border border-border bg-card hover:bg-card-hover hover:border-border-light transition p-4 cursor-pointer group relative">
                <div className="flex items-start justify-between mb-2">
                  <span className={cn('text-[10px] font-semibold uppercase', statusColor(ex.status))}>{ex.status}</span>
                </div>
                <p className="text-sm font-medium truncate mb-1">{ex.description || ex.title || `Workflow ${ex._id.slice(-6)}`}</p>
                <div className="flex items-center gap-3 text-[10px] text-gray-500">
                  <span className="flex items-center gap-1"><Clock size={10} />{formatRelativeTime(ex.started_at)}</span>
                  {ex.completed_at && <span className="flex items-center gap-1 text-accent">{formatDuration(ex.started_at, ex.completed_at)}</span>}
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
