'use client';

import React, { useState, useMemo, useDeferredValue } from 'react';
import { useRouter } from 'next/navigation';
import { History, Search, LayoutGrid, List, Table as TableIcon, Download, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react';
import { cn, formatRelativeTime, formatLocalDateTime, formatDuration, statusColor, statusBg } from '@/lib/utils';
import { useExecutions } from '@/lib/hooks';

type ViewMode = 'timeline' | 'cards' | 'table';
const filters = ['All', 'Completed', 'Stopped', 'Draft'] as const;
const PAGE_SIZE = 10;

export default function HistoryPage() {
  const router = useRouter();
  const { data: executions, loading } = useExecutions();
  const [view, setView] = useState<ViewMode>('cards');
  const [filter, setFilter] = useState<string>('All');
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return executions.filter(ex => {
      const ds = (ex.display_status || '').toLowerCase();
      if (filter !== 'All' && ds !== filter.toLowerCase()) return false;
      if (deferredSearch && !ex.description?.toLowerCase().includes(deferredSearch.toLowerCase()) && !ex.title?.toLowerCase().includes(deferredSearch.toLowerCase())) return false;
      return true;
    });
  }, [executions, filter, deferredSearch]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const ta = a.completed_at || a.stopped_at || a.started_at || '';
      const tb = b.completed_at || b.stopped_at || b.started_at || '';
      return new Date(tb).getTime() - new Date(ta).getTime();
    });
  }, [filtered]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const paginated = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  React.useEffect(() => { setPage(1); }, [filter, deferredSearch]);

  const handleExport = () => {
    const csv = [
      'Status,Description,Steps,Duration,Started',
      ...sorted.map(ex => [
        ex.display_status || ex.status,
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

  const timeLabel = (ex: any) => {
    const end = ex.completed_at || ex.stopped_at;
    if (end) return formatLocalDateTime(end);
    if (ex.started_at) return formatLocalDateTime(ex.started_at);
    return 'Unknown time';
  };

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto bg-app min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-theme">Execution History</h1>
          <p className="text-xs text-theme-tertiary mt-0.5">{sorted.length} executions{filter !== 'All' ? ` (${filter})` : ''}</p>
        </div>
        <button onClick={handleExport} disabled={sorted.length === 0}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-2 border border-theme text-xs text-theme-tertiary hover:text-theme-secondary transition cursor-pointer disabled:opacity-50">
          <Download size={13} />Export CSV
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-tertiary" />
          <input type="text" placeholder="Search history..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-input border border-theme rounded-lg text-theme placeholder:text-theme-tertiary outline-none focus:border-theme-strong transition" />
        </div>
        <div className="flex gap-1">
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                filter === f
                  ? 'bg-surface-2 text-theme border-theme-strong'
                  : 'bg-surface-2 border-theme text-theme-tertiary hover:text-theme-secondary')}>
              {f}
            </button>
          ))}
        </div>
        <div className="flex gap-0.5 bg-surface-2 border border-theme rounded-lg p-0.5">
          {([['cards', LayoutGrid], ['timeline', List], ['table', TableIcon]] as [ViewMode, any][]).map(([v, Icon]) => (
            <button key={v} onClick={() => setView(v)}
              className={cn('p-1.5 rounded-md transition cursor-pointer', view === v ? 'bg-surface-2 text-theme' : 'text-theme-tertiary hover:text-theme-secondary')}>
              <Icon size={14} />
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        view === 'table' ? (
          <div className="rounded-[14px] border border-theme bg-surface overflow-hidden animate-pulse">
            <div className="bg-surface-2 px-4 py-2.5 flex gap-4">
              {[1, 2, 3, 4, 5].map(i => <div key={i} className="h-3 flex-1 bg-surface-hover rounded" />)}
            </div>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="px-4 py-3 flex gap-4 border-t border-theme">
                {[1, 2, 3, 4, 5].map(j => <div key={j} className="h-3 flex-1 bg-surface-hover rounded" />)}
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="rounded-[14px] border border-theme bg-surface p-4 space-y-3 animate-pulse">
                <div className="h-3 w-16 bg-surface-hover rounded" />
                <div className="h-4 w-3/4 bg-surface-hover rounded" />
                <div className="flex gap-3">
                  <div className="h-3 w-20 bg-surface-hover rounded" />
                  <div className="h-3 w-14 bg-surface-hover rounded" />
                </div>
              </div>
            ))}
          </div>
        )
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <History size={32} className="text-theme-tertiary mb-3" />
          <p className="text-sm font-medium text-theme-secondary">No execution history</p>
          <p className="text-xs text-theme-tertiary mt-1 mb-4">
            {search ? 'No results match your search' : 'Run a workflow to see results here'}
          </p>
          <button onClick={() => router.push('/chat')}
            className="flex items-center gap-2 px-4 py-2 bg-theme text-white text-xs font-semibold rounded-lg transition hover:opacity-90 cursor-pointer">
            <RotateCcw size={13} />Create Workflow
          </button>
        </div>
      ) : view === 'table' ? (
        <div className="rounded-[14px] border border-theme bg-surface overflow-hidden">
          <table className="w-full text-xs">
            <thead><tr className="border-b border-theme bg-surface-2">
              <th className="text-left px-4 py-2.5 font-medium text-theme-tertiary">Status</th>
              <th className="text-left px-4 py-2.5 font-medium text-theme-tertiary">Description</th>
              <th className="text-left px-4 py-2.5 font-medium text-theme-tertiary">Steps</th>
              <th className="text-left px-4 py-2.5 font-medium text-theme-tertiary">Duration</th>
              <th className="text-left px-4 py-2.5 font-medium text-theme-tertiary">Time</th>
            </tr></thead>
            <tbody>
              {paginated.map((ex) => {
                const ds = ex.display_status || ex.status;
                return (
                  <tr key={ex._id} onClick={() => router.push('/chat')}
                    className="border-t border-theme hover:bg-surface-hover transition cursor-pointer group">
                    <td className="px-4 py-2.5">
                      <span className={cn('font-semibold uppercase px-2 py-0.5 rounded', statusBg(ds), statusColor(ds))}>{ds}</span>
                    </td>
                    <td className="px-4 py-2.5 truncate max-w-[300px] text-theme">{ex.description || ex.title}</td>
                    <td className="px-4 py-2.5 text-theme-tertiary">{ex.current_step_index}/{ex.total_steps}</td>
                    <td className="px-4 py-2.5 text-status-active font-mono">{ex.duration_ms != null ? formatDuration(ex.started_at, ex.completed_at || ex.stopped_at) : '—'}</td>
                    <td className="px-4 py-2.5 text-theme-tertiary" title={timeLabel(ex)}>{timeLabel(ex)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : view === 'timeline' ? (
        <div className="space-y-0 pl-4 border-l border-theme">
          {paginated.map((ex, i) => {
            const ds = ex.display_status || ex.status;
            const dotClass = ds === 'completed' ? 'bg-status-active' : ds === 'stopped' ? 'bg-status-error' : 'bg-theme-tertiary';
            return (
              <div key={ex._id} style={{ animationDelay: `${i * 30}ms` }}
                className="relative pl-6 pb-6 cursor-pointer group animate-[fadeIn_0.2s_ease-out_both]" onClick={() => router.push('/chat')}>
                <span className={cn(
                  'absolute -left-[9px] top-1 h-4 w-4 rounded-full border-2 border-app flex items-center justify-center',
                  dotClass
                )} />
                <div className="rounded-[14px] border border-theme bg-surface p-3 hover:bg-surface-hover transition">
                  <div className="flex items-center justify-between mb-1">
                    <span className={cn('text-[10px] font-semibold uppercase px-2 py-0.5 rounded', statusBg(ds), statusColor(ds))}>{ds}</span>
                    <span className="text-[10px] text-theme-tertiary">{timeLabel(ex)}</span>
                  </div>
                  <p className="text-xs font-medium truncate text-theme">{ex.description || ex.title}</p>
                  {ex.duration_ms != null && <p className="text-[10px] text-status-active mt-1 font-mono">{formatDuration(ex.started_at, ex.completed_at || ex.stopped_at)}</p>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {paginated.map((ex, i) => {
            const ds = ex.display_status || ex.status;
            return (
              <div key={ex._id} style={{ animationDelay: `${i * 30}ms` }}
                onClick={() => router.push('/chat')}
                className="rounded-[14px] border border-theme bg-surface hover:bg-surface-hover transition p-4 cursor-pointer animate-[fadeIn_0.2s_ease-out_both]">
                <div className="flex items-center justify-between mb-2">
                  <span className={cn('text-[10px] font-semibold uppercase px-2 py-0.5 rounded', statusBg(ds), statusColor(ds))}>{ds}</span>
                  <span className="text-[10px] text-theme-tertiary">{timeLabel(ex)}</span>
                </div>
                <p className="text-xs font-medium truncate mb-2 text-theme">{ex.description || ex.title}</p>
                <div className="flex items-center gap-3 text-[10px] text-theme-tertiary">
                  <span>{ex.current_step_index}/{ex.total_steps} steps</span>
                  {ex.duration_ms != null && <span className="text-status-active font-mono">{formatDuration(ex.started_at, ex.completed_at || ex.stopped_at)}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-theme">
          <p className="text-[10px] text-theme-tertiary">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, sorted.length)} of {sorted.length}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="p-1.5 rounded-lg bg-surface-2 hover:bg-surface-hover disabled:opacity-30 transition cursor-pointer text-theme-tertiary border border-theme">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
              const pageNum = i + 1;
              return (
                <button key={pageNum} onClick={() => setPage(pageNum)}
                  className={cn('w-7 h-7 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                    page === pageNum
                      ? 'bg-theme text-white border-theme'
                      : 'bg-surface-2 border-theme text-theme-tertiary hover:text-theme-secondary')}>
                  {pageNum}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-surface-2 hover:bg-surface-hover disabled:opacity-30 transition cursor-pointer text-theme-tertiary border border-theme">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
