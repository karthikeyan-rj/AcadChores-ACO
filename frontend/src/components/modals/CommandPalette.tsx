'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, FileText, GitBranch, Clock, Settings, Terminal, LayoutDashboard,
  MessageSquare, BarChart3, Puzzle, HelpCircle, Database, Globe, Play,
  Cpu, Shield, Moon, Keyboard, ExternalLink, ArrowRight, Hash, Zap
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
  // Pages
  { id: 'nav-dashboard', icon: <LayoutDashboard size={14} />, label: 'Dashboard', description: 'View overview and stats', category: 'Pages', action: '/', keywords: ['home', 'overview', 'main'] },
  { id: 'nav-chat', icon: <MessageSquare size={14} />, label: 'AI Assistant', description: 'Create and execute workflows', category: 'Pages', action: '/chat', keywords: ['chat', 'prompt', 'execute', 'workflow'] },
  { id: 'nav-workflows', icon: <GitBranch size={14} />, label: 'Workflows', description: 'Manage all workflows', category: 'Pages', action: '/workflows', keywords: ['pipelines', 'automation'] },
  { id: 'nav-history', icon: <Clock size={14} />, label: 'Execution History', description: 'View past executions', category: 'Pages', action: '/history', keywords: ['past', 'runs', 'logs'] },
  { id: 'nav-files', icon: <FileText size={14} />, label: 'File Explorer', description: 'Browse local files', category: 'Pages', action: '/files', keywords: ['explorer', 'folders', 'documents'] },
  { id: 'nav-memory', icon: <Database size={14} />, label: 'Memory Manager', description: 'Manage stored context', category: 'Pages', action: '/memory', keywords: ['context', 'cache', 'storage'] },
  { id: 'nav-analytics', icon: <BarChart3 size={14} />, label: 'Analytics', description: 'View metrics and charts', category: 'Pages', action: '/analytics', keywords: ['metrics', 'stats', 'charts', 'graphs'] },
  { id: 'nav-plugins', icon: <Puzzle size={14} />, label: 'Plugin Marketplace', description: 'Browse and install plugins', category: 'Pages', action: '/plugins', keywords: ['extensions', 'addons', 'marketplace'] },
  { id: 'nav-scheduler', icon: <Clock size={14} />, label: 'Task Scheduler', description: 'Schedule automated tasks', category: 'Pages', action: '/scheduler', keywords: ['cron', 'schedule', 'timer', 'recurring'] },
  { id: 'nav-settings', icon: <Settings size={14} />, label: 'Settings', description: 'Application configuration', category: 'Pages', action: '/settings', keywords: ['config', 'preferences', 'options'] },
  { id: 'nav-help', icon: <HelpCircle size={14} />, label: 'Help & Documentation', description: 'Guides and FAQ', category: 'Pages', action: '/help', keywords: ['docs', 'faq', 'guide', 'support'] },

  // Actions
  { id: 'act-new', icon: <Play size={14} className="text-[#ADFF2F]" />, label: 'New Workflow', description: 'Start a new AI workflow', category: 'Actions', action: '/chat', keywords: ['create', 'start', 'execute', 'run'] },
  { id: 'act-search-files', icon: <Search size={14} className="text-blue-400" />, label: 'Search Files', description: 'Find files on your system', category: 'Actions', action: '/files', keywords: ['find', 'browse', 'lookup'] },
  { id: 'act-schedule', icon: <Clock size={14} className="text-cyan-400" />, label: 'Schedule Task', description: 'Create a scheduled job', category: 'Actions', action: '/scheduler', keywords: ['cron', 'timer', 'automate'] },
  { id: 'act-plugins', icon: <Puzzle size={14} className="text-purple-400" />, label: 'Browse Plugins', description: 'Discover new capabilities', category: 'Actions', action: '/plugins', keywords: ['install', 'extensions', 'addons'] },
  { id: 'act-export', icon: <ExternalLink size={14} className="text-amber-400" />, label: 'Export History', description: 'Download execution history', category: 'Actions', action: '/history', keywords: ['download', 'csv', 'report'] },
  { id: 'act-clear-memory', icon: <Database size={14} className="text-[#F87171]" />, label: 'Clear Memory', description: 'Reset stored context', category: 'Actions', action: '/memory', keywords: ['reset', 'clear', 'delete', 'cache'] },
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
        if (open) {
          onClose();
          setTimeout(() => triggerRef?.current?.focus(), 50);
        }
      }
      if (e.key === 'Escape' && open) {
        onClose();
        setTimeout(() => triggerRef?.current?.focus(), 50);
      }
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

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, PaletteItem[]> = {};
    filtered.forEach(item => {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    });
    return groups;
  }, [filtered]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx(i => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx(i => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filtered[selectedIdx]) {
        e.preventDefault();
        onNavigate(filtered[selectedIdx].action);
        onClose();
        setTimeout(() => triggerRef?.current?.focus(), 50);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, selectedIdx, onNavigate, onClose]);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  // Reset selection on query change
  useEffect(() => { setSelectedIdx(0); }, [query]);

  if (!open) return null;

  let runningIdx = -1;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 z-[100] flex items-start justify-center pt-[15vh]"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.96, opacity: 0, y: -10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.96, opacity: 0, y: -10 }}
          className="w-full max-w-lg bg-[#121419] border border-white/[0.07] rounded-lg shadow-matte-lg overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search input */}
          <div className="command-palette-search flex items-center gap-3 px-4 py-3 border-b border-white/[0.07]">
            <Search size={16} className="text-[#71717A] shrink-0" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Type a command or search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent outline-none text-sm text-[#F4F4F5] placeholder-[#71717A]"
            />
            <kbd className="text-[10px] bg-[#181B21] px-1.5 py-0.5 rounded border border-white/[0.07] text-[#71717A] font-mono">Esc</kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="p-2 max-h-[360px] overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-xs text-[#71717A]">No results found for &quot;{query}&quot;</p>
                <p className="text-[10px] text-[#71717A]/60 mt-1">Try a different search term</p>
              </div>
            ) : (
              Object.entries(grouped).map(([category, items]) => (
                <div key={category} className="mb-2">
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#71717A]">{category}</div>
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
                          isSelected ? 'bg-[#7C3AED]/10 border border-[#7C3AED]/20 text-[#F4F4F5]' : 'text-[#A1A1AA] hover:bg-white/[0.04] hover:text-[#F4F4F5] border border-transparent'
                        )}
                      >
                        <span className="shrink-0">{item.icon}</span>
                        <div className="flex-1 text-left min-w-0">
                          <p className="text-xs font-medium truncate">{item.label}</p>
                          {item.description && <p className="text-[10px] text-[#71717A] truncate">{item.description}</p>}
                        </div>
                        {isSelected && <ArrowRight size={12} className="text-[#7C3AED] shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          {/* Footer hints */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-white/[0.07] text-[10px] text-[#71717A]">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1"><kbd className="bg-[#181B21] px-1 py-0.5 rounded border border-white/[0.07] font-mono">↑↓</kbd> Navigate</span>
              <span className="flex items-center gap-1"><kbd className="bg-[#181B21] px-1 py-0.5 rounded border border-white/[0.07] font-mono">↵</kbd> Select</span>
              <span className="flex items-center gap-1"><kbd className="bg-[#181B21] px-1 py-0.5 rounded border border-white/[0.07] font-mono">Esc</kbd> Close</span>
            </div>
            <span>{filtered.length} results</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
