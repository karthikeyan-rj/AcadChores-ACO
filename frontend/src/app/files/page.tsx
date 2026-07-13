'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Folder, FileText, Search, RefreshCw, Eye,
  Download, Copy, FileCode, FileImage, FileAudio,
  FileVideo, FileArchive, Grid, List, Loader2, Plus,
  X, Settings, Play, Clock, CheckCircle2, XCircle,
  HardDrive, Database, AlertTriangle, Trash2
} from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useFileSearch, useIndexConfig, useIndexJobs, useIndexStats } from '@/lib/hooks';
import { useAuth } from '@/lib/auth';

function getFileIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  if (['py', 'js', 'ts', 'tsx', 'jsx', 'json', 'yaml', 'yml', 'toml'].includes(ext)) return FileCode;
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) return FileImage;
  if (['mp3', 'wav', 'ogg', 'flac'].includes(ext)) return FileAudio;
  if (['mp4', 'avi', 'mkv', 'mov'].includes(ext)) return FileVideo;
  if (['zip', 'tar', 'gz', 'rar', '7z'].includes(ext)) return FileArchive;
  return FileText;
}

function formatSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export default function FilesPage() {
  const { token } = useAuth();
  const { results, loading: searchLoading, search } = useFileSearch();
  const { config, exists, loading: configLoading, refresh: refreshConfig, updateConfig } = useIndexConfig();
  const { jobs, loading: jobsLoading, refresh: refreshJobs, triggerIndex } = useIndexJobs();
  const { stats, loading: statsLoading, refresh: refreshStats } = useIndexStats();

  const [tab, setTab] = useState<'search' | 'index'>('search');
  const [searchInput, setSearchInput] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<'grid' | 'list'>('list');
  const [preview, setPreview] = useState<any | null>(null);
  const [configForm, setConfigForm] = useState({
    roots: [''],
    enabled: false,
    interval_seconds: 3600,
    max_file_size_mb: 100,
    exclude_extensions: '.exe,.dll,.so,.dylib,.bin,.obj,.o',
    exclude_dirs: 'node_modules,.git,__pycache__,.venv,venv,AppData,Windows,Program Files'
  });
  const [saving, setSaving] = useState(false);
  const [trigerring, setTriggering] = useState(false);

  useEffect(() => {
    if (config) {
      setConfigForm({
        roots: config.roots?.length ? config.roots : [''],
        enabled: config.enabled,
        interval_seconds: config.interval_seconds || 3600,
        max_file_size_mb: config.max_file_size_mb || 100,
        exclude_extensions: (config.exclude_extensions || []).join(','),
        exclude_dirs: (config.exclude_dirs || []).join(',')
      });
    }
  }, [config]);

  const handleSearch = useCallback((q: string) => {
    setSearchInput(q);
    search(q);
  }, [search]);

  const handleSaveConfig = useCallback(async () => {
    setSaving(true);
    try {
      const roots = configForm.roots.filter(r => r.trim());
      if (roots.length === 0) return;
      await updateConfig({
        roots,
        enabled: configForm.enabled,
        interval_seconds: configForm.interval_seconds,
        max_file_size_mb: configForm.max_file_size_mb,
        exclude_extensions: configForm.exclude_extensions.split(',').map(s => s.trim()).filter(Boolean),
        exclude_dirs: configForm.exclude_dirs.split(',').map(s => s.trim()).filter(Boolean)
      });
    } finally { setSaving(false); }
  }, [configForm, updateConfig]);

  const handleTrigger = useCallback(async () => {
    setTriggering(true);
    try { await triggerIndex(); } finally { setTriggering(false); }
  }, [triggerIndex]);

  const addRoot = () => setConfigForm(p => ({ ...p, roots: [...p.roots, ''] }));
  const removeRoot = (i: number) => setConfigForm(p => ({ ...p, roots: p.roots.filter((_, j) => j !== i) }));
  const updateRoot = (i: number, v: string) => setConfigForm(p => ({ ...p, roots: p.roots.map((r, j) => j === i ? v : r) }));

  const runningJob = jobs.find(j => j.status === 'running');

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="h-12 border-b border-border flex items-center justify-between px-4 shrink-0 bg-card/50">
        <div className="flex items-center gap-2">
          <div className={cn(
            'flex bg-surface border border-border rounded-lg p-0.5'
          )}>
            <button
              onClick={() => setTab('search')}
              className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition cursor-pointer', tab === 'search' ? 'bg-primary/10 text-primary' : 'text-gray-500 hover:text-foreground')}
            >
              <Search size={13} className="inline mr-1.5" />Search
            </button>
            <button
              onClick={() => setTab('index')}
              className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition cursor-pointer', tab === 'index' ? 'bg-primary/10 text-primary' : 'text-gray-500 hover:text-foreground')}
            >
              <Database size={13} className="inline mr-1.5" />Index
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {tab === 'search' && (
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                placeholder="Search your indexed files..."
                value={searchInput}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition"
              />
              {searchLoading && <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-primary" />}
            </div>
          )}
          {tab === 'index' && (
            <div className="flex items-center gap-2">
              <button onClick={() => { refreshConfig(); refreshJobs(); refreshStats(); }}
                className="p-1.5 rounded-lg hover:bg-surface-2 transition text-gray-400 hover:text-foreground cursor-pointer" title="Refresh">
                <RefreshCw size={14} />
              </button>
              <button
                onClick={handleTrigger}
                disabled={trigerring || !!runningJob || !config?.enabled}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 transition disabled:opacity-40 cursor-pointer"
              >
                {trigerring || runningJob ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                {runningJob ? 'Indexing...' : 'Run Now'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'search' ? (
          /* Search Tab */
          searchInput.length < 2 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Search size={40} className="text-gray-600 mb-3" />
              <p className="text-sm font-medium">Search your files</p>
              <p className="text-xs text-gray-600 mt-1">Enter at least 2 characters to search indexed files</p>
            </div>
          ) : searchLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Loader2 size={24} className="animate-spin text-primary mb-3" />
              <p className="text-xs">Searching files...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Folder size={40} className="text-gray-600 mb-3" />
              <p className="text-sm font-medium">No files found</p>
              <p className="text-xs text-gray-600 mt-1">No indexed files match &quot;{searchInput}&quot;</p>
              {!exists && (
                <button onClick={() => setTab('index')} className="mt-3 text-xs text-primary hover:underline cursor-pointer">
                  Configure file indexing first
                </button>
              )}
            </div>
          ) : view === 'list' ? (
            <div className="divide-y divide-border/50">
              <div className="grid grid-cols-[1fr_100px_140px_80px] gap-2 px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                <span>Name</span>
                <span>Size</span>
                <span>Modified</span>
                <span></span>
              </div>
              {results.map((item: any, i: number) => {
                const Icon = getFileIcon(item.file_name || item.file_path || '');
                const isSelected = selected === item.file_path;
                return (
                  <motion.div
                    key={item.file_path || i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    onClick={() => { setSelected(item.file_path); setPreview(item); }}
                    className={cn(
                      'grid grid-cols-[1fr_100px_140px_80px] gap-2 px-4 py-2.5 text-xs cursor-pointer transition-all',
                      isSelected ? 'bg-primary/5 border-l-2 border-l-primary' : 'hover:bg-surface-2 border-l-2 border-l-transparent'
                    )}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon size={14} className="text-gray-500 shrink-0" />
                      <span className="truncate font-medium">{item.file_name || item.file_path}</span>
                    </div>
                    <span className="text-gray-500">{formatSize(item.size_bytes)}</span>
                    <span className="text-gray-500">{item.modified_at ? new Date(item.modified_at).toLocaleDateString() : '—'}</span>
                    <div className="flex items-center gap-1">
                      <button className="p-1 rounded hover:bg-surface-2 cursor-pointer" title="Preview"><Eye size={12} className="text-gray-400" /></button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 p-4">
              {results.map((item: any, i: number) => {
                const Icon = getFileIcon(item.file_name || item.file_path || '');
                return (
                  <motion.div
                    key={item.file_path || i}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => { setSelected(item.file_path); setPreview(item); }}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border cursor-pointer transition-all',
                      selected === item.file_path ? 'border-primary/40 bg-primary/5' : 'border-border hover:border-border-light hover:bg-card-hover'
                    )}
                  >
                    <Icon size={28} className="text-gray-400" />
                    <span className="text-[11px] font-medium text-center truncate w-full">{item.file_name || item.file_path}</span>
                    {item.size_bytes ? <span className="text-[9px] text-gray-500">{formatSize(item.size_bytes)}</span> : null}
                  </motion.div>
                );
              })}
            </div>
          )
        ) : (
          /* Index Tab */
          <div className="p-6 space-y-6 max-w-[1000px] mx-auto">
            {/* Stats */}
            {!statsLoading && stats && (
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-xl border border-border bg-card/80 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-gray-400">
                    <FileText size={14} />
                    <span className="text-xs font-medium">Total Files</span>
                  </div>
                  <p className="text-2xl font-bold">{stats.total_files || 0}</p>
                </div>
                <div className="rounded-xl border border-border bg-card/80 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-gray-400">
                    <HardDrive size={14} />
                    <span className="text-xs font-medium">Total Size</span>
                  </div>
                  <p className="text-2xl font-bold">{formatSize(stats.total_size_bytes || 0)}</p>
                </div>
                <div className="rounded-xl border border-border bg-card/80 p-4 space-y-2">
                  <div className="flex items-center gap-2 text-gray-400">
                    <Database size={14} />
                    <span className="text-xs font-medium">Extensions</span>
                  </div>
                  <p className="text-2xl font-bold">{stats.top_extensions?.length || 0}</p>
                </div>
              </div>
            )}

            {/* Top Extensions */}
            {!statsLoading && stats?.top_extensions?.length > 0 && (
              <div className="rounded-xl border border-border bg-card/80 p-5 space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Top File Types</span>
                <div className="space-y-2">
                  {stats.top_extensions.slice(0, 5).map((ext: any, i: number) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-primary">{ext.extension}</span>
                        <span className="text-[10px] text-gray-500">{ext.count} files</span>
                      </div>
                      <span className="text-[10px] text-gray-500">{formatSize(ext.total_size)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Configuration */}
            <div className="rounded-xl border border-border bg-card/80 p-5 space-y-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Index Configuration</span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-[10px] text-gray-500">Enabled</span>
                  <div
                    onClick={() => setConfigForm(p => ({ ...p, enabled: !p.enabled }))}
                    className={cn('w-9 h-5 rounded-full transition cursor-pointer relative', configForm.enabled ? 'bg-primary' : 'bg-surface-2')}
                  >
                    <div className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all', configForm.enabled ? 'left-[18px]' : 'left-0.5')} />
                  </div>
                </label>
              </div>

              {/* Index Roots */}
              <div className="space-y-2">
                <label className="text-xs text-gray-400 font-medium">Index Roots</label>
                {configForm.roots.map((root, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      value={root}
                      onChange={(e) => updateRoot(i, e.target.value)}
                      placeholder="C:\Users\you\Documents"
                      className="flex-1 px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition font-mono"
                    />
                    <button onClick={() => removeRoot(i)} className="p-1.5 rounded-lg hover:bg-surface-2 text-gray-500 hover:text-danger transition cursor-pointer">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
                <button onClick={addRoot} className="flex items-center gap-1.5 text-xs text-primary hover:underline cursor-pointer">
                  <Plus size={12} />Add Root
                </button>
              </div>

              {/* Settings Row */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-gray-400 font-medium">Max File Size (MB)</label>
                  <input
                    type="number"
                    min={1}
                    value={configForm.max_file_size_mb}
                    onChange={(e) => setConfigForm(p => ({ ...p, max_file_size_mb: parseInt(e.target.value) || 100 }))}
                    className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-gray-400 font-medium">Re-index Interval (seconds)</label>
                  <input
                    type="number"
                    min={60}
                    value={configForm.interval_seconds}
                    onChange={(e) => setConfigForm(p => ({ ...p, interval_seconds: parseInt(e.target.value) || 3600 }))}
                    className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition"
                  />
                </div>
              </div>

              {/* Excludes */}
              <div className="space-y-1">
                <label className="text-xs text-gray-400 font-medium">Exclude Extensions (comma-separated)</label>
                <input
                  value={configForm.exclude_extensions}
                  onChange={(e) => setConfigForm(p => ({ ...p, exclude_extensions: e.target.value }))}
                  className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400 font-medium">Exclude Directories (comma-separated)</label>
                <input
                  value={configForm.exclude_dirs}
                  onChange={(e) => setConfigForm(p => ({ ...p, exclude_dirs: e.target.value }))}
                  className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition font-mono"
                />
              </div>

              <button
                onClick={handleSaveConfig}
                disabled={saving || configForm.roots.filter(r => r.trim()).length === 0}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-xs font-medium hover:bg-primary/90 transition disabled:opacity-40 cursor-pointer"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Settings size={12} />}
                Save Configuration
              </button>
            </div>

            {/* Recent Jobs */}
            <div className="rounded-xl border border-border bg-card/80 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-border">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Indexing Jobs</span>
                <button onClick={refreshJobs} className="text-[10px] text-primary hover:underline cursor-pointer">Refresh</button>
              </div>
              <div className="divide-y divide-border/50">
                {jobsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 size={16} className="animate-spin text-primary" />
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                    <Clock size={24} className="text-gray-600 mb-2" />
                    <p className="text-xs">No indexing jobs yet</p>
                  </div>
                ) : (
                  jobs.map((job) => (
                    <div key={job.id} className="flex items-center justify-between px-5 py-3 hover:bg-surface-2 transition">
                      <div className="flex items-center gap-3 min-w-0">
                        {job.status === 'completed' ? (
                          <CheckCircle2 size={14} className="text-accent shrink-0" />
                        ) : job.status === 'failed' ? (
                          <XCircle size={14} className="text-danger shrink-0" />
                        ) : job.status === 'running' ? (
                          <Loader2 size={14} className="text-primary animate-spin shrink-0" />
                        ) : (
                          <Clock size={14} className="text-gray-500 shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p className="text-xs font-medium truncate">
                            {job.roots?.[0] || 'Index run'}
                            {job.roots?.length > 1 && <span className="text-gray-500"> +{job.roots.length - 1} more</span>}
                          </p>
                          <p className="text-[10px] text-gray-500">
                            {job.files_indexed} indexed, {job.files_updated} updated, {job.files_removed} removed
                            {job.errors?.length > 0 && <span className="text-danger ml-2">{job.errors.length} errors</span>}
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className={cn(
                          'text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase',
                          job.status === 'completed' ? 'bg-accent/10 text-accent' :
                          job.status === 'failed' ? 'bg-danger/10 text-danger' :
                          job.status === 'running' ? 'bg-primary/10 text-primary' :
                          'bg-gray-500/10 text-gray-400'
                        )}>
                          {job.status}
                        </span>
                        <p className="text-[10px] text-gray-600 mt-0.5">
                          {job.completed_at ? formatRelativeTime(job.completed_at) : job.started_at ? 'Started' : 'Pending'}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Preview panel */}
      <AnimatePresence>
        {preview && tab === 'search' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-border bg-card/80 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2">
              <div className="flex items-center gap-2 min-w-0">
                {React.createElement(getFileIcon(preview.file_name || preview.file_path || ''), { size: 14, className: 'text-primary shrink-0' })}
                <span className="text-xs font-medium truncate">{preview.file_name || preview.file_path}</span>
                {preview.size_bytes ? <span className="text-[10px] text-gray-500">{formatSize(preview.size_bytes)}</span> : null}
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1 rounded hover:bg-surface-2 cursor-pointer" title="Copy path"><Copy size={12} className="text-gray-400" /></button>
                <button onClick={() => setPreview(null)} className="p-1 rounded hover:bg-surface-2 cursor-pointer text-gray-500 hover:text-foreground">×</button>
              </div>
            </div>
            <div className="px-4 pb-3 text-[10px] text-gray-500 space-y-1">
              <p>Path: <span className="font-mono text-foreground">{preview.file_path}</span></p>
              {preview.modified_at && <p>Modified: <span className="text-foreground">{new Date(preview.modified_at).toLocaleString()}</span></p>}
              {preview.extension && <p>Type: <span className="text-foreground">{preview.extension}</span></p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
