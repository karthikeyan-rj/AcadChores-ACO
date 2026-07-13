'use client';

import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { History, Search, LayoutGrid, List, Table as TableIcon, Clock, CheckCircle2, XCircle, Download, Loader2, ChevronLeft, ChevronRight, RotateCcw, Copy, Eye } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration, statusColor } from '@/lib/utils';
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

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Execution History</h1>
          <p className="text-xs text-gray-500 mt-0.5">{filtered.length} executions{filter !== 'All' ? ` (${filter})` : ''}</p>
        </div>
        <button onClick={handleExport} disabled={filtered.length === 0}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-gray-400 hover:text-foreground transition cursor-pointer disabled:opacity-50">
          <Download size={13} />Export CSV
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input type="text" placeholder="Search history..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-card border border-border rounded-lg outline-none focus:border-primary transition" />
        </div>
        <div className="flex gap-1">
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                filter === f ? 'bg-primary/10 text-primary border-primary/30' : 'bg-card border-border text-gray-400 hover:text-foreground')}>
              {f}
            </button>
          ))}
        </div>
        <div className="flex gap-0.5 bg-card border border-border rounded-lg p-0.5">
          {([['cards', LayoutGrid], ['timeline', List], ['table', TableIcon]] as [ViewMode, any][]).map(([v, Icon]) => (
            <button key={v} onClick={() => setView(v)}
              className={cn('p-1.5 rounded-md transition cursor-pointer', view === v ? 'bg-primary/10 text-primary' : 'text-gray-500 hover:text-foreground')}>
              <Icon size={14} />
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        view === 'table' ? <SkeletonTable /> : <SkeletonList rows={4} />
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <History size={32} className="text-gray-600 mb-3" />
          <p className="text-sm font-medium">No execution history</p>
          <p className="text-xs text-gray-600 mt-1 mb-4">
            {search ? 'No results match your search' : 'Run a workflow to see results here'}
          </p>
          <button onClick={() => router.push('/chat')}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl transition cursor-pointer">
            <RotateCcw size={13} />Create Workflow
          </button>
        </div>
      ) : view === 'table' ? (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-border text-gray-500">
              <th className="text-left px-4 py-2.5 font-medium">Status</th>
              <th className="text-left px-4 py-2.5 font-medium">Description</th>
              <th className="text-left px-4 py-2.5 font-medium">Steps</th>
              <th className="text-left px-4 py-2.5 font-medium">Duration</th>
              <th className="text-left px-4 py-2.5 font-medium">Time</th>
              <th className="text-left px-4 py-2.5 font-medium">Actions</th>
            </tr></thead>
            <tbody>
              {paginated.map((ex) => (
                <tr key={ex._id} className="border-b border-border/50 hover:bg-surface-2 transition group">
                  <td className="px-4 py-2.5"><span className={cn('font-semibold uppercase', statusColor(ex.status))}>{ex.status}</span></td>
                  <td className="px-4 py-2.5 truncate max-w-[300px]">{ex.description || ex.title}</td>
                  <td className="px-4 py-2.5 text-gray-400">{ex.current_step_index}/{ex.total_steps}</td>
                  <td className="px-4 py-2.5 text-accent font-mono">{ex.completed_at ? formatDuration(ex.started_at, ex.completed_at) : '—'}</td>
                  <td className="px-4 py-2.5 text-gray-500">{formatRelativeTime(ex.started_at)}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                      <button className="p-1 rounded hover:bg-surface-2 cursor-pointer" title="View"><Eye size={12} className="text-gray-400" /></button>
                      <button className="p-1 rounded hover:bg-surface-2 cursor-pointer" title="Replay"><RotateCcw size={12} className="text-gray-400" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : view === 'timeline' ? (
        <div className="space-y-0 pl-4 border-l border-border">
          {paginated.map((ex, i) => (
            <motion.div key={ex._id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.03 }}
              className="relative pl-6 pb-6 cursor-pointer group" onClick={() => router.push('/chat')}>
              <span className={cn('absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-background flex items-center justify-center',
                ex.status === 'completed' ? 'bg-accent' : ex.status === 'Failed' ? 'bg-danger' : 'bg-primary')}>
                {ex.status === 'completed' ? <CheckCircle2 size={10} className="text-white" /> : <Clock size={10} className="text-white" />}
              </span>
              <div className="rounded-lg border border-border bg-card p-3 hover:bg-card-hover transition">
                <div className="flex items-center justify-between mb-1">
                  <span className={cn('text-[10px] font-semibold uppercase', statusColor(ex.status))}>{ex.status}</span>
                  <span className="text-[10px] text-gray-500">{formatRelativeTime(ex.started_at)}</span>
                </div>
                <p className="text-xs font-medium truncate">{ex.description || ex.title}</p>
                {ex.completed_at && <p className="text-[10px] text-accent mt-1 font-mono">{formatDuration(ex.started_at, ex.completed_at)}</p>}
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {paginated.map((ex, i) => (
            <motion.div key={ex._id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
              onClick={() => router.push('/chat')}
              className="rounded-xl border border-border bg-card hover:bg-card-hover transition p-4 cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <span className={cn('text-[10px] font-semibold uppercase', statusColor(ex.status))}>{ex.status}</span>
                <span className="text-[10px] text-gray-500">{formatRelativeTime(ex.started_at)}</span>
              </div>
              <p className="text-xs font-medium truncate mb-2">{ex.description || ex.title}</p>
              <div className="flex items-center gap-3 text-[10px] text-gray-500">
                <span>{ex.current_step_index}/{ex.total_steps} steps</span>
                {ex.completed_at && <span className="text-accent font-mono">{formatDuration(ex.started_at, ex.completed_at)}</span>}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <p className="text-[10px] text-gray-500">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="p-1.5 rounded-lg hover:bg-surface-2 disabled:opacity-30 transition cursor-pointer text-gray-400">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
              const pageNum = i + 1;
              return (
                <button key={pageNum} onClick={() => setPage(pageNum)}
                  className={cn('w-7 h-7 rounded-lg text-[11px] font-medium transition cursor-pointer',
                    page === pageNum ? 'bg-primary/10 text-primary' : 'text-gray-400 hover:bg-surface-2')}>
                  {pageNum}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="p-1.5 rounded-lg hover:bg-surface-2 disabled:opacity-30 transition cursor-pointer text-gray-400">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
