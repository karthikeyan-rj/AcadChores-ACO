'use client';

import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { History, Search, LayoutGrid, List, Table as TableIcon, Clock, CheckCircle2, Download, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration, statusColor, statusBg } from '@/lib/utils';
import { useExecutions } from '@/lib/hooks';
import { SkeletonTable, SkeletonList } from '@/components/ui/Skeleton';

type ViewMode = 'timeline' | 'cards' | 'table';
const filters = ['All', 'Completed', 'Failed', 'Running', 'Cancelled'];
const PAGE_SIZE = 10;

export default function HistoryPage() {
  const router = useRouter();
  const { data: executions, loading } = useExecutions();
  const [view, setView] = useState<ViewMode>('cards');
  const [filter, setFilter] = useState('All');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return executions.filter(ex => {
      if (filter !== 'All' && ex.status.toLowerCase() !== filter.toLowerCase()) return false;
      if (search && !ex.description?.toLowerCase().includes(search.toLowerCase()) && !ex.title?.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [executions, filter, search]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset page on filter/search change
  React.useEffect(() => { setPage(1); }, [filter, search]);

  const handleExport = () => {
    const csv = [
      'Status,Description,Steps,Duration,Started',
      ...filtered.map(ex => [
        ex.status,
        `"${(ex.description || ex.title || '').replace(/"/g, '""')}"`,
        `${ex.current_step_index}/${ex.total_steps}`,
        ex.completed_at ? formatDuration(ex.started_at, ex.completed_at) : '',
        new Date(ex.started_at).toISOString(),
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aco-history-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isRunning = (status: string) => status === 'executing' || status === 'running';

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#F4F4F5]">Execution History</h1>
          <p className="text-xs text-[#71717A] mt-0.5">{filtered.length} executions{filter !== 'All' ? ` (${filter})` : ''}</p>
        </div>
        <button onClick={handleExport} disabled={filtered.length === 0}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181B21] border border-white/[0.07] text-xs text-[#71717A] hover:text-[#A1A1AA] transition cursor-pointer disabled:opacity-50">
          <Download size={13} />Export CSV
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <input type="text" placeholder="Search history..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-lg text-[#F4F4F5] placeholder:text-[#71717A] outline-none focus:border-[#7C3AED]/40 transition" />
        </div>
        <div className="flex gap-1">
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                filter === f
                  ? 'bg-[#7C3AED]/12 text-[#7C3AED] border-[#7C3AED]/30'
                  : 'bg-[#181B21] border-white/[0.07] text-[#71717A] hover:text-[#A1A1AA]')}>
              {f}
            </button>
          ))}
        </div>
        <div className="flex gap-0.5 bg-[#181B21] border border-white/[0.07] rounded-lg p-0.5">
          {([['cards', LayoutGrid], ['timeline', List], ['table', TableIcon]] as [ViewMode, any][]).map(([v, Icon]) => (
            <button key={v} onClick={() => setView(v)}
              className={cn('p-1.5 rounded-md transition cursor-pointer', view === v ? 'bg-[#7C3AED]/12 text-[#7C3AED]' : 'text-[#71717A] hover:text-[#A1A1AA]')}>
              <Icon size={14} />
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        view === 'table' ? (
          <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] overflow-hidden animate-pulse">
            <div className="bg-[#0D0F12] px-4 py-2.5 flex gap-4">
              {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-3 flex-1 bg-[#181B21] rounded" />)}
            </div>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="px-4 py-3 flex gap-4 border-t border-white/[0.05]">
                {[1, 2, 3, 4, 5].map(j => <div key={j} className="h-3 flex-1 bg-[#181B21] rounded" />)}
              </div>
            ))}
          </div>
        ) : (
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
        )
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <History size={32} className="text-[#71717A] mb-3" />
          <p className="text-sm font-medium text-[#A1A1AA]">No execution history</p>
          <p className="text-xs text-[#71717A] mt-1 mb-4">
            {search ? 'No results match your search' : 'Run a workflow to see results here'}
          </p>
          <button onClick={() => router.push('/chat')}
            className="flex items-center gap-2 px-4 py-2 bg-[#7C3AED] hover:bg-[#6D28D9] text-white text-xs font-semibold rounded-lg transition cursor-pointer">
            <RotateCcw size={13} />Create Workflow
          </button>
        </div>
      ) : view === 'table' ? (
        <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] overflow-hidden">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-white/[0.07] bg-[#0D0F12]">
              <th className="text-left px-4 py-2.5 font-medium text-[#71717A]">Status</th>
              <th className="text-left px-4 py-2.5 font-medium text-[#71717A]">Description</th>
              <th className="text-left px-4 py-2.5 font-medium text-[#71717A]">Steps</th>
              <th className="text-left px-4 py-2.5 font-medium text-[#71717A]">Duration</th>
              <th className="text-left px-4 py-2.5 font-medium text-[#71717A]">Time</th>
            </tr></thead>
            <tbody>
              {paginated.map((ex) => (
                <tr key={ex._id} onClick={() => router.push('/chat')}
                  className="border-t border-white/[0.05] hover:bg-white/[0.02] transition cursor-pointer group">
                  <td className="px-4 py-2.5">
                    <span className={cn(
                      'font-semibold uppercase px-2 py-0.5 rounded',
                      isRunning(ex.status) ? 'bg-[#ADFF2F]/10 text-[#ADFF2F]' : cn(statusBg(ex.status), statusColor(ex.status))
                    )}>{ex.status}</span>
                  </td>
                  <td className="px-4 py-2.5 truncate max-w-[300px] text-[#F4F4F5]">{ex.description || ex.title}</td>
                  <td className="px-4 py-2.5 text-[#71717A]">{ex.current_step_index}/{ex.total_steps}</td>
                  <td className="px-4 py-2.5 text-[#4ADE80] font-mono">{ex.completed_at ? formatDuration(ex.started_at, ex.completed_at) : '—'}</td>
                  <td className="px-4 py-2.5 text-[#71717A]">{formatRelativeTime(ex.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : view === 'timeline' ? (
        <div className="space-y-0 pl-4 border-l border-white/[0.07]">
          {paginated.map((ex, i) => (
            <motion.div key={ex._id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }}
              className="relative pl-6 pb-6 cursor-pointer group" onClick={() => router.push('/chat')}>
              <span className={cn(
                'absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-[#08090B] flex items-center justify-center',
                isRunning(ex.status) ? 'bg-[#ADFF2F]' : ex.status === 'completed' ? 'bg-[#4ADE80]' : ex.status === 'failed' ? 'bg-[#F87171]' : 'bg-[#7C3AED]'
              )}>
                {ex.status === 'completed' ? <CheckCircle2 size={10} className="text-[#08090B]" /> : <Clock size={10} className="text-[#08090B]" />}
              </span>
              <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-3 hover:bg-[#181B21] transition">
                <div className="flex items-center justify-between mb-1">
                  <span className={cn(
                    'text-[10px] font-semibold uppercase px-2 py-0.5 rounded',
                    isRunning(ex.status) ? 'bg-[#ADFF2F]/10 text-[#ADFF2F]' : cn(statusBg(ex.status), statusColor(ex.status))
                  )}>{ex.status}</span>
                  <span className="text-[10px] text-[#71717A]">{formatRelativeTime(ex.started_at)}</span>
                </div>
                <p className="text-xs font-medium truncate text-[#F4F4F5]">{ex.description || ex.title}</p>
                {ex.completed_at && <p className="text-[10px] text-[#4ADE80] mt-1 font-mono">{formatDuration(ex.started_at, ex.completed_at)}</p>}
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {paginated.map((ex, i) => (
            <motion.div key={ex._id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
              onClick={() => router.push('/chat')}
              className="rounded-[14px] border border-white/[0.07] bg-[#121419] hover:bg-[#181B21] transition p-4 cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <span className={cn(
                  'text-[10px] font-semibold uppercase px-2 py-0.5 rounded',
                  isRunning(ex.status) ? 'bg-[#ADFF2F]/10 text-[#ADFF2F]' : cn(statusBg(ex.status), statusColor(ex.status))
                )}>{ex.status}</span>
                <span className="text-[10px] text-[#71717A]">{formatRelativeTime(ex.started_at)}</span>
              </div>
              <p className="text-xs font-medium truncate mb-2 text-[#F4F4F5]">{ex.description || ex.title}</p>
              <div className="flex items-center gap-3 text-[10px] text-[#71717A]">
                <span>{ex.current_step_index}/{ex.total_steps} steps</span>
                {ex.completed_at && <span className="text-[#4ADE80] font-mono">{formatDuration(ex.started_at, ex.completed_at)}</span>}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-white/[0.07]">
          <p className="text-[10px] text-[#71717A]">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="p-1.5 rounded-lg bg-[#181B21] hover:bg-[#181B21]/80 disabled:opacity-30 transition cursor-pointer text-[#71717A] border border-white/[0.07]">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
              const pageNum = i + 1;
              return (
                <button key={pageNum} onClick={() => setPage(pageNum)}
                  className={cn('w-7 h-7 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                    page === pageNum
                      ? 'bg-[#7C3AED] text-white border-[#7C3AED]'
                      : 'bg-[#181B21] border-white/[0.07] text-[#71717A] hover:text-[#A1A1AA]')}>
                  {pageNum}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-[#181B21] hover:bg-[#181B21]/80 disabled:opacity-30 transition cursor-pointer text-[#71717A] border border-white/[0.07]">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
