'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Folder, FileText, Search, RefreshCw, Eye,
  Download, Copy, FileCode, FileImage, FileAudio,
  FileVideo, FileArchive, Grid, List, Loader2, Plus,
  X, Settings, Play, Clock, CheckCircle2, XCircle,
  HardDrive, Database, AlertTriangle, Trash2, AlertCircle
} from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { useFileSearch, useIndexConfig, useIndexJobs, useIndexStats } from '@/lib/hooks';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

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
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ path: string; name: string } | null>(null);

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

  const handleDelete = useCallback(async () => {
    if (!deleteConfirm || !token) return;
    const filePath = deleteConfirm.path;
    setDeletingFile(filePath);
    try {
      await api.deleteFile(filePath, token);
      setPreview(null);
      setSelected(null);
      search(searchInput);
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
    setDeletingFile(null);
    setDeleteConfirm(null);
  }, [deleteConfirm, token, search, searchInput]);

  const runningJob = jobs.find(j => j.status === 'running');

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[#08090B]">
      {/* Toolbar */}
      <div className="h-12 border-b border-white/[0.07] flex items-center justify-between px-4 shrink-0 bg-[#0D0F12]">
        <div className="flex items-center gap-2">
          <div className="flex bg-[#181B21] rounded-lg p-0.5">
            <button
              onClick={() => setTab('search')}
              className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition cursor-pointer', tab === 'search' ? 'bg-[#7C3AED]/12 text-[#7C3AED]' : 'text-[#71717A] hover:text-[#F4F4F5]')}
            >
              <Search size={13} className="inline mr-1.5" />Search
            </button>
            <button
              onClick={() => setTab('index')}
              className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition cursor-pointer', tab === 'index' ? 'bg-[#7C3AED]/12 text-[#7C3AED]' : 'text-[#71717A] hover:text-[#F4F4F5]')}
            >
              <Database size={13} className="inline mr-1.5" />Index
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {tab === 'search' && (
            <div className="relative flex-1 max-w-md">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
              <input
                type="text"
                placeholder="Search your indexed files..."
                value={searchInput}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 text-xs bg-[#181B21] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition text-[#F4F4F5] placeholder:text-[#71717A]"
              />
              {searchLoading && <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-[#7C3AED]" />}
            </div>
          )}
          {tab === 'index' && (
            <div className="flex items-center gap-2">
              <button onClick={() => { refreshConfig(); refreshJobs(); refreshStats(); }}
                className="p-1.5 rounded-md hover:bg-[#181B21] transition text-[#A1A1AA] hover:text-[#F4F4F5] cursor-pointer" title="Refresh">
                <RefreshCw size={14} />
              </button>
              <button
                onClick={handleTrigger}
                disabled={trigerring || !!runningJob || !config?.enabled}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#7C3AED] text-white text-xs font-medium hover:opacity-90 transition disabled:opacity-40 cursor-pointer"
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
            <div className="flex flex-col items-center justify-center h-full text-[#71717A]">
              <Search size={40} className="text-[#71717A] mb-3" />
              <p className="text-sm font-medium">Search your files</p>
              <p className="text-xs text-[#71717A] mt-1">Enter at least 2 characters to search indexed files</p>
            </div>
          ) : searchLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-[#71717A]">
              <Loader2 size={24} className="animate-spin text-[#7C3AED] mb-3" />
              <p className="text-xs">Searching files...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[#71717A]">
              <Folder size={40} className="text-[#71717A] mb-3" />
              <p className="text-sm font-medium">No files found</p>
              <p className="text-xs text-[#71717A] mt-1">No indexed files match &quot;{searchInput}&quot;</p>
              {!exists && (
                <button onClick={() => setTab('index')} className="mt-3 text-xs text-[#7C3AED] hover:underline cursor-pointer">
                  Configure file indexing first
                </button>
              )}
            </div>
          ) : view === 'list' ? (
            <div>
              <div className="grid grid-cols-[1fr_100px_140px_80px] gap-2 px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-[#71717A] border-b border-white/[0.05]">
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
                      'grid grid-cols-[1fr_100px_140px_80px] gap-2 px-4 py-2.5 text-xs cursor-pointer transition-all border-b border-white/[0.05]',
                      isSelected ? 'bg-[#7C3AED]/5 border-l-2 border-l-[#7C3AED]' : 'hover:bg-white/[0.02] border-l-2 border-l-transparent'
                    )}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon size={14} className="text-[#71717A] shrink-0" />
                      <span className="truncate font-medium text-[#F4F4F5]">{item.file_name || item.file_path}</span>
                    </div>
                    <span className="text-[#A1A1AA]">{formatSize(item.size_bytes)}</span>
                    <span className="text-[#A1A1AA]">{item.modified_at ? new Date(item.modified_at).toLocaleDateString() : '—'}</span>
                    <div className="flex items-center gap-1">
                      <button className="p-1 rounded hover:bg-[#181B21] cursor-pointer" title="Preview"><Eye size={12} className="text-[#A1A1AA]" /></button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm({ path: item.file_path, name: item.file_name || item.file_path }); }}
                        className="p-1 rounded hover:bg-[#F87171]/10 cursor-pointer"
                        title="Delete file"
                      >
                        <Trash2 size={12} className="text-[#71717A] hover:text-[#F87171]" />
                      </button>
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
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => { setSelected(item.file_path); setPreview(item); }}
                    className={cn(
                      'flex flex-col items-center gap-2 p-4 rounded-xl border cursor-pointer transition-all',
                      selected === item.file_path ? 'border-[#7C3AED]/40 bg-[#7C3AED]/5' : 'border-white/[0.07] bg-[#121419] hover:bg-[#181B21]'
                    )}
                  >
                    <Icon size={28} className="text-[#A1A1AA]" />
                    <span className="text-[11px] font-medium text-center truncate w-full text-[#F4F4F5]">{item.file_name || item.file_path}</span>
                    {item.size_bytes ? <span className="text-[9px] text-[#71717A]">{formatSize(item.size_bytes)}</span> : null}
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
                <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-4 space-y-2">
                  <div className="flex items-center gap-2 text-[#A1A1AA]">
                    <FileText size={14} />
                    <span className="text-xs font-medium">Total Files</span>
                  </div>
                  <p className="text-2xl font-bold text-[#F4F4F5]">{stats.total_files || 0}</p>
                </div>
                <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-4 space-y-2">
                  <div className="flex items-center gap-2 text-[#A1A1AA]">
                    <HardDrive size={14} />
                    <span className="text-xs font-medium">Total Size</span>
                  </div>
                  <p className="text-2xl font-bold text-[#F4F4F5]">{formatSize(stats.total_size_bytes || 0)}</p>
                </div>
                <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-4 space-y-2">
                  <div className="flex items-center gap-2 text-[#A1A1AA]">
                    <Database size={14} />
                    <span className="text-xs font-medium">Extensions</span>
                  </div>
                  <p className="text-2xl font-bold text-[#F4F4F5]">{stats.top_extensions?.length || 0}</p>
                </div>
              </div>
            )}

            {/* Top Extensions */}
            {!statsLoading && stats?.top_extensions?.length > 0 && (
              <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-5 space-y-3">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#71717A]">Top File Types</span>
                <div className="space-y-2">
                  {stats.top_extensions.slice(0, 5).map((ext: any, i: number) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-[#7C3AED]">{ext.extension}</span>
                        <span className="text-[10px] text-[#71717A]">{ext.count} files</span>
                      </div>
                      <span className="text-[10px] text-[#71717A]">{formatSize(ext.total_size)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Configuration */}
            <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] p-5 space-y-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#71717A]">Index Configuration</span>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-[10px] text-[#71717A]">Enabled</span>
                  <div
                    onClick={() => setConfigForm(p => ({ ...p, enabled: !p.enabled }))}
                    className={cn('w-9 h-5 rounded-full transition cursor-pointer relative', configForm.enabled ? 'bg-[#7C3AED]' : 'bg-[#181B21]')}
                  >
                    <div className={cn('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all', configForm.enabled ? 'left-[18px]' : 'left-0.5')} />
                  </div>
                </label>
              </div>

              {/* Index Roots */}
              <div className="space-y-2">
                <label className="text-xs text-[#A1A1AA] font-medium">Index Roots</label>
                {configForm.roots.map((root, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      value={root}
                      onChange={(e) => updateRoot(i, e.target.value)}
                      placeholder="C:\Users\you\Documents"
                      className="flex-1 px-3 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition font-mono text-[#F4F4F5] placeholder:text-[#71717A]"
                    />
                    <button onClick={() => removeRoot(i)} className="p-1.5 rounded-md hover:bg-[#181B21] text-[#71717A] hover:text-[#F87171] transition cursor-pointer">
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
                <button onClick={addRoot} className="flex items-center gap-1.5 text-xs text-[#7C3AED] hover:underline cursor-pointer">
                  <Plus size={12} />Add Root
                </button>
              </div>

              {/* Settings Row */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-[#A1A1AA] font-medium">Max File Size (MB)</label>
                  <input
                    type="number"
                    min={1}
                    value={configForm.max_file_size_mb}
                    onChange={(e) => setConfigForm(p => ({ ...p, max_file_size_mb: parseInt(e.target.value) || 100 }))}
                    className="w-full px-3 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition text-[#F4F4F5]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-[#A1A1AA] font-medium">Re-index Interval (seconds)</label>
                  <input
                    type="number"
                    min={60}
                    value={configForm.interval_seconds}
                    onChange={(e) => setConfigForm(p => ({ ...p, interval_seconds: parseInt(e.target.value) || 3600 }))}
                    className="w-full px-3 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition text-[#F4F4F5]"
                  />
                </div>
              </div>

              {/* Excludes */}
              <div className="space-y-1">
                <label className="text-xs text-[#A1A1AA] font-medium">Exclude Extensions (comma-separated)</label>
                <input
                  value={configForm.exclude_extensions}
                  onChange={(e) => setConfigForm(p => ({ ...p, exclude_extensions: e.target.value }))}
                  className="w-full px-3 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition font-mono text-[#F4F4F5]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[#A1A1AA] font-medium">Exclude Directories (comma-separated)</label>
                <input
                  value={configForm.exclude_dirs}
                  onChange={(e) => setConfigForm(p => ({ ...p, exclude_dirs: e.target.value }))}
                  className="w-full px-3 py-2 text-xs bg-[#0D0F12] border border-white/[0.07] rounded-md outline-none focus:border-[#7C3AED]/40 transition font-mono text-[#F4F4F5]"
                />
              </div>

              <button
                onClick={handleSaveConfig}
                disabled={saving || configForm.roots.filter(r => r.trim()).length === 0}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#7C3AED] text-white text-xs font-medium hover:opacity-90 transition disabled:opacity-40 cursor-pointer"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Settings size={12} />}
                Save Configuration
              </button>
            </div>

            {/* Recent Jobs */}
            <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.07]">
                <span className="text-xs font-semibold uppercase tracking-wider text-[#71717A]">Indexing Jobs</span>
                <button onClick={refreshJobs} className="text-[10px] text-[#7C3AED] hover:underline cursor-pointer">Refresh</button>
              </div>
              <div>
                {jobsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 size={16} className="animate-spin text-[#7C3AED]" />
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-[#71717A]">
                    <Clock size={24} className="text-[#71717A] mb-2" />
                    <p className="text-xs">No indexing jobs yet</p>
                  </div>
                ) : (
                  jobs.map((job) => (
                    <div key={job.id} className="flex items-center justify-between px-5 py-3 hover:bg-white/[0.02] transition border-b border-white/[0.05] last:border-b-0">
                      <div className="flex items-center gap-3 min-w-0">
                        {job.status === 'completed' ? (
                          <CheckCircle2 size={14} className="text-[#4ADE80] shrink-0" />
                        ) : job.status === 'failed' ? (
                          <XCircle size={14} className="text-[#F87171] shrink-0" />
                        ) : job.status === 'running' ? (
                          <Loader2 size={14} className="text-[#7C3AED] animate-spin shrink-0" />
                        ) : (
                          <Clock size={14} className="text-[#71717A] shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p className="text-xs font-medium truncate text-[#F4F4F5]">
                            {job.roots?.[0] || 'Index run'}
                            {job.roots?.length > 1 && <span className="text-[#71717A]"> +{job.roots.length - 1} more</span>}
                          </p>
                          <p className="text-[10px] text-[#71717A]">
                            {job.files_indexed} indexed, {job.files_updated} updated, {job.files_removed} removed
                            {job.errors?.length > 0 && <span className="text-[#F87171] ml-2">{job.errors.length} errors</span>}
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className={cn(
                          'text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase',
                          job.status === 'completed' ? 'bg-[#4ADE80]/10 text-[#4ADE80]' :
                          job.status === 'failed' ? 'bg-[#F87171]/10 text-[#F87171]' :
                          job.status === 'running' ? 'bg-[#7C3AED]/10 text-[#7C3AED]' :
                          'bg-[#71717A]/10 text-[#71717A]'
                        )}>
                          {job.status}
                        </span>
                        <p className="text-[10px] text-[#71717A] mt-0.5">
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
            className="border-t border-white/[0.07] bg-[#121419] overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2">
              <div className="flex items-center gap-2 min-w-0">
                {React.createElement(getFileIcon(preview.file_name || preview.file_path || ''), { size: 14, className: 'text-[#7C3AED] shrink-0' })}
                <span className="text-xs font-medium truncate text-[#F4F4F5]">{preview.file_name || preview.file_path}</span>
                {preview.size_bytes ? <span className="text-[10px] text-[#71717A]">{formatSize(preview.size_bytes)}</span> : null}
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1 rounded hover:bg-[#181B21] cursor-pointer" title="Copy path"><Copy size={12} className="text-[#A1A1AA]" /></button>
                <button onClick={() => setPreview(null)} className="p-1 rounded hover:bg-[#181B21] cursor-pointer text-[#71717A] hover:text-[#F4F4F5]">×</button>
              </div>
            </div>
            <div className="px-4 pb-3 text-[10px] text-[#71717A] space-y-1">
              <p>Path: <span className="font-mono text-[#F4F4F5]">{preview.file_path}</span></p>
              {preview.modified_at && <p>Modified: <span className="text-[#F4F4F5]">{new Date(preview.modified_at).toLocaleString()}</span></p>}
              {preview.extension && <p>Type: <span className="text-[#F4F4F5]">{preview.extension}</span></p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-sm rounded-[14px] border border-[#F87171]/20 bg-[#121419] shadow-matte-lg p-5 space-y-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#F87171]/10 flex items-center justify-center shrink-0">
                  <AlertCircle size={18} className="text-[#F87171]" />
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-[#F4F4F5]">Delete file</p>
                  <p className="text-[11px] text-[#71717A] mt-0.5 truncate max-w-[250px]">{deleteConfirm.name}</p>
                </div>
              </div>
              <p className="text-[11px] text-[#A1A1AA]">
                This action cannot be undone. The file will be permanently removed from your filesystem.
              </p>
              <div className="flex items-center justify-end gap-2">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-medium text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-white/[0.04] transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={!!deletingFile}
                  className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[#F87171]/10 hover:bg-[#F87171]/20 text-[#F87171] border border-[#F87171]/20 transition cursor-pointer disabled:opacity-50"
                >
                  {deletingFile ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
