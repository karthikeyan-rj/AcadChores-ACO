'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, FileText, GitBranch, Clock, Settings, Terminal, LayoutDashboard,
  MessageSquare, BarChart3, Puzzle, HelpCircle, Database, Globe, Play,
  ArrowRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (section: string) => void;
  triggerRef?: React.RefObject<HTMLButtonElement>;
}

interface PaletteItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  description?: string;
  category: string;
  action: string;
  keywords: string[];
}

const allItems: PaletteItem[] = [
  { id: 'nav-dashboard', icon: <LayoutDashboard size={14} />, label: 'Dashboard', description: 'View overview and stats', category: 'Pages', action: '/dashboard', keywords: ['home', 'overview', 'main'] },
  { id: 'nav-chat', icon: <MessageSquare size={14} />, label: 'AI Assistant', description: 'Create and execute workflows', category: 'Pages', action: '/chat', keywords: ['chat', 'prompt', 'execute', 'workflow'] },
  { id: 'nav-workflows', icon: <GitBranch size={14} />, label: 'Workflows', description: 'Manage all workflows', category: 'Pages', action: '/workflows', keywords: ['pipelines', 'automation'] },
  { id: 'nav-history', icon: <Clock size={14} />, label: 'Execution History', description: 'View past executions', category: 'Pages', action: '/history', keywords: ['past', 'runs', 'logs'] },
  { id: 'nav-files', icon: <FileText size={14} />, label: 'File Explorer', description: 'Browse local files', category: 'Pages', action: '/files', keywords: ['explorer', 'folders', 'documents'] },
  { id: 'nav-analytics', icon: <BarChart3 size={14} />, label: 'Analytics', description: 'View metrics and charts', category: 'Pages', action: '/analytics', keywords: ['metrics', 'stats', 'charts'] },
  { id: 'nav-settings', icon: <Settings size={14} />, label: 'Settings', description: 'Application configuration', category: 'Pages', action: '/settings', keywords: ['config', 'preferences'] },
  { id: 'nav-help', icon: <HelpCircle size={14} />, label: 'Help & Documentation', description: 'Guides and FAQ', category: 'Pages', action: '/help', keywords: ['docs', 'faq', 'guide'] },
  { id: 'act-new', icon: <Play size={14} />, label: 'New Workflow', description: 'Start a new AI workflow', category: 'Actions', action: '/chat', keywords: ['create', 'start', 'run'] },
];

export function CommandPalette({ open, onClose, onNavigate, triggerRef }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (open) { onClose(); setTimeout(() => triggerRef?.current?.focus(), 50); }
      }
      if (e.key === 'Escape' && open) { onClose(); setTimeout(() => triggerRef?.current?.focus(), 50); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose, triggerRef]);

  const filtered = useMemo(() => {
    if (!query) return allItems;
    const q = query.toLowerCase();
    return allItems.filter(item =>
      item.label.toLowerCase().includes(q) ||
      item.description?.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q) ||
      item.keywords.some(k => k.includes(q))
    );
  }, [query]);

  const grouped = useMemo(() => {
    const groups: Record<string, PaletteItem[]> = {};
    filtered.forEach(item => {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    });
    return groups;
  }, [filtered]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, filtered.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)); }
      else if (e.key === 'Enter' && filtered[selectedIdx]) {
        e.preventDefault(); onNavigate(filtered[selectedIdx].action); onClose();
        setTimeout(() => triggerRef?.current?.focus(), 50);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, selectedIdx, onNavigate, onClose, triggerRef]);

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  useEffect(() => { setSelectedIdx(0); }, [query]);

  if (!open) return null;
  let runningIdx = -1;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12 }}
        className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]"
        style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.12 }}
          className="w-full max-w-lg bg-surface border border-theme-strong rounded-xl overflow-hidden shadow-theme-dropdown"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-3 px-4 py-3 border-b border-theme">
            <Search size={16} className="text-theme-tertiary shrink-0" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Type a command or search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm text-theme placeholder:text-theme-tertiary"
            />
            <kbd className="text-[10px] bg-surface-2 px-1.5 py-0.5 rounded border border-theme text-theme-tertiary font-mono">Esc</kbd>
          </div>

          <div ref={listRef} className="p-2 max-h-[360px] overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-xs text-theme-secondary">No results found for &quot;{query}&quot;</p>
                <p className="text-[10px] text-theme-tertiary mt-1">Try a different search term</p>
              </div>
            ) : (
              Object.entries(grouped).map(([category, items]) => (
                <div key={category} className="mb-2">
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">{category}</div>
                  {items.map((item) => {
                    runningIdx++;
                    const idx = runningIdx;
                    const isSelected = idx === selectedIdx;
                    return (
                      <button
                        key={item.id}
                        data-idx={idx}
                        onClick={() => { onNavigate(item.action); onClose(); setTimeout(() => triggerRef?.current?.focus(), 50); }}
                        onMouseEnter={() => setSelectedIdx(idx)}
                        className={cn(
                          'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition text-sm cursor-pointer',
                          isSelected ? 'bg-surface-active text-theme' : 'text-theme-secondary hover:bg-surface-hover hover:text-theme'
                        )}
                      >
                        <span className="shrink-0 text-theme-tertiary">{item.icon}</span>
                        <div className="flex-1 text-left min-w-0">
                          <p className="text-xs font-medium truncate">{item.label}</p>
                          {item.description && <p className="text-[10px] text-theme-tertiary truncate">{item.description}</p>}
                        </div>
                        {isSelected && <ArrowRight size={12} className="text-theme-secondary shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          <div className="flex items-center justify-between px-4 py-2 border-t border-theme text-[10px] text-theme-tertiary">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1"><kbd className="bg-surface-2 px-1 py-0.5 rounded border border-theme font-mono">↑↓</kbd> Navigate</span>
              <span className="flex items-center gap-1"><kbd className="bg-surface-2 px-1 py-0.5 rounded border border-theme font-mono">↵</kbd> Select</span>
            </div>
            <span>{filtered.length} results</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
