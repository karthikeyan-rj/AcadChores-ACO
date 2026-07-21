'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database, Search, Plus, Trash2, Edit3, Tag, Pin,
  ChevronDown, ChevronRight, Loader2, MessageSquare,
  GitBranch, Brain, StickyNote, Filter
} from 'lucide-react';
import { cn } from '@/lib/utils';

type MemoryCategory = 'All' | 'Conversations' | 'Workflows' | 'Agent' | 'Pinned' | 'Cached';

interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  category: Exclude<MemoryCategory, 'All'>;
  created: string;
  updated: string;
  tags: string[];
  pinned: boolean;
}

const categoryIcons: Record<string, React.ComponentType<any>> = {
  Conversations: MessageSquare, Workflows: GitBranch, Agent: Brain, Pinned: Pin, Cached: StickyNote,
};

const allCategories: MemoryCategory[] = ['All', 'Conversations', 'Workflows', 'Agent', 'Pinned', 'Cached'];

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [category, setCategory] = useState<MemoryCategory>('All');
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const filtered = memories.filter(m => {
    if (category !== 'All' && m.category !== category) return false;
    if (search && !m.key.toLowerCase().includes(search.toLowerCase()) && !m.value.toLowerCase().includes(search.toLowerCase()) && !m.tags.some(t => t.includes(search.toLowerCase()))) return false;
    return true;
  });

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const togglePin = (id: string) => {
    setMemories(prev => prev.map(m => m.id === id ? { ...m, pinned: !m.pinned } : m));
  };

  const deleteMemory = (id: string) => {
    setMemories(prev => prev.filter(m => m.id !== id));
  };

  const clearAll = () => {
    setMemories([]);
    setConfirmClear(false);
  };

  const stats = {
    total: memories.length,
    conversations: memories.filter(m => m.category === 'Conversations').length,
    workflows: memories.filter(m => m.category === 'Workflows').length,
    agent: memories.filter(m => m.category === 'Agent').length,
    pinned: memories.filter(m => m.pinned).length,
  };

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-theme">Memory Manager</h1>
          <p className="text-xs text-theme-tertiary mt-0.5">
            {memories.length === 0
              ? 'No memory entries available'
              : `${stats.total} entries · ${stats.pinned} pinned · ${stats.conversations} conversations · ${stats.workflows} workflows`
            }
          </p>
        </div>
        <div className="flex items-center gap-2">
          {memories.length > 0 && (
            <button onClick={() => setConfirmClear(true)}
              className="flex items-center gap-2 px-3 py-2 text-xs text-status-error hover:bg-status-error-soft border border-status-error rounded-xl transition cursor-pointer">
              <Trash2 size={13} />Clear All
            </button>
          )}
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 bg-theme hover:opacity-90 text-white text-xs font-semibold rounded-xl transition cursor-pointer">
            <Plus size={14} />Add Memory
          </button>
        </div>
      </div>

      {/* Category tabs + Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-tertiary" />
          <input type="text" placeholder="Search memories by key, value, or tag..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition text-theme" />
        </div>
        <div className="flex gap-1">
          {allCategories.map(c => {
            const Icon = categoryIcons[c];
            return (
              <button key={c} onClick={() => setCategory(c)}
                className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                  category === c ? 'bg-surface-2 text-theme border-theme-strong' : 'bg-surface border-theme text-theme-tertiary hover:text-theme')}>
                {Icon && <Icon size={12} />}
                {c}
              </button>
            );
          })}
        </div>
      </div>

      {/* Memory entries */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-theme-tertiary">
          <Database size={32} className="text-theme-tertiary mb-3" />
          <p className="text-sm font-medium">
            {search ? 'No matching memories' : memories.length === 0 ? 'No memory entries' : 'No entries in this category'}
          </p>
          <p className="text-xs text-theme-tertiary mt-1 mb-4">
            {search ? 'Try a different search term' : memories.length === 0 ? 'Memory entries are created as workflows execute and the agent learns' : 'No entries match the selected filter'}
          </p>
          {!search && memories.length === 0 && (
            <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 bg-theme hover:opacity-90 text-white text-xs font-semibold rounded-xl transition cursor-pointer">
              <Plus size={14} />Add Memory
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((m, i) => {
            const isExpanded = expanded.has(m.id);
            const Icon = categoryIcons[m.category] || Database;
            return (
              <motion.div key={m.id} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.02 }}
                className={cn('rounded-xl border bg-surface overflow-hidden transition-all', isExpanded ? 'border-theme' : 'border-theme')}>
                <div onClick={() => toggleExpand(m.id)} className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-surface-hover transition">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-surface-2 flex items-center justify-center shrink-0">
                      <Icon size={14} className="text-theme-tertiary" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-medium font-mono truncate text-theme">{m.key}</p>
                        {m.pinned && <Pin size={10} className="text-theme shrink-0" />}
                      </div>
                      {!isExpanded && <p className="text-[10px] text-theme-tertiary truncate max-w-[400px]">{m.value}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex gap-1">
                      {m.tags.slice(0, 3).map(t => (
                        <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-surface-2 text-theme-tertiary border border-theme">{t}</span>
                      ))}
                    </div>
                    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => togglePin(m.id)} className="p-1 rounded hover:bg-surface-2 transition cursor-pointer" title={m.pinned ? 'Unpin' : 'Pin'}>
                        <Pin size={12} className={cn(m.pinned ? 'text-theme' : 'text-theme-tertiary')} />
                      </button>
                      <button onClick={() => deleteMemory(m.id)} className="p-1 rounded hover:bg-surface-2 transition cursor-pointer" title="Delete">
                        <Trash2 size={12} className="text-theme-tertiary hover:text-status-error" />
                      </button>
                    </div>
                  </div>
                </div>
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <div className="px-4 pb-4 pt-1 ml-11">
                        <div className="bg-surface-2 rounded-lg p-3 border border-theme">
                          <p className="text-xs text-theme whitespace-pre-wrap font-mono leading-relaxed">{m.value}</p>
                        </div>
                        <div className="flex items-center gap-4 mt-2 text-[10px] text-theme-tertiary">
                          <span>Created: {new Date(m.created).toLocaleString()}</span>
                          <span>Updated: {new Date(m.updated).toLocaleString()}</span>
                          <span>Size: {m.value.length} chars</span>
                          <span>Category: {m.category}</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Clear all confirmation */}
      <AnimatePresence>
        {confirmClear && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-theme/32" onClick={() => setConfirmClear(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()} className="w-full max-w-sm rounded-xl border border-theme bg-surface p-5 space-y-4">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-status-error-soft flex items-center justify-center mx-auto mb-3">
                  <Trash2 size={20} className="text-status-error" />
                </div>
                <h2 className="text-sm font-bold text-theme">Clear All Memory?</h2>
                <p className="text-xs text-theme-tertiary mt-1">This will permanently delete all {memories.length} memory entries. This action cannot be undone.</p>
              </div>
              <div className="flex justify-center gap-2">
                <button onClick={() => setConfirmClear(false)} className="px-4 py-2 text-xs text-theme-tertiary hover:text-theme border border-theme rounded-lg transition cursor-pointer">Cancel</button>
                <button onClick={clearAll} className="px-4 py-2 bg-status-error hover:opacity-90 text-white text-xs font-semibold rounded-lg transition cursor-pointer">Clear All</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add memory modal */}
      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-theme/32" onClick={() => setShowAdd(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()} className="w-full max-w-md rounded-xl border border-theme bg-surface p-5 space-y-4">
              <h2 className="text-sm font-bold text-theme">Add Memory Entry</h2>
              <div className="space-y-3">
                <Field label="Key">
                  <input type="text" placeholder="e.g. my_setting" className="w-full px-3 py-2 text-xs font-mono bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition text-theme" />
                </Field>
                <Field label="Value">
                  <textarea rows={3} placeholder="Enter value..." className="w-full px-3 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition resize-none text-theme" />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Category">
                    <select className="w-full px-3 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition text-theme">
                      {allCategories.filter(c => c !== 'All').map(c => <option key={c}>{c}</option>)}
                    </select>
                  </Field>
                  <Field label="Tags">
                    <input type="text" placeholder="comma-separated" className="w-full px-3 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition text-theme" />
                  </Field>
                </div>
                <Toggle label="Pin this entry" />
              </div>
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 text-xs text-theme-tertiary hover:text-theme transition cursor-pointer">Cancel</button>
                <button onClick={() => setShowAdd(false)} className="px-4 py-1.5 bg-theme hover:opacity-90 text-white text-xs font-semibold rounded-lg transition cursor-pointer">Add</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] text-theme-tertiary mb-1 block">{label}</label>
      {children}
    </div>
  );
}

function Toggle({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-theme-tertiary">{label}</span>
      <button onClick={() => setOn(p => !p)} className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative', on ? 'bg-theme' : 'bg-surface-2')}>
        <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform', on ? 'left-[18px]' : 'left-0.5')} />
      </button>
    </div>
  );
}
