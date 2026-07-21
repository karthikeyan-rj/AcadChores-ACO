'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock, Plus, Calendar
} from 'lucide-react';
import { cn } from '@/lib/utils';

type ViewMode = 'list' | 'calendar';

export default function SchedulerPage() {
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [showAdd, setShowAdd] = useState(false);

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-theme">Task Scheduler</h1>
          <p className="text-xs text-theme-tertiary mt-0.5">No scheduled tasks — scheduler API not connected</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 bg-theme hover:opacity-90 text-white text-xs font-semibold rounded-xl transition cursor-pointer">
          <Plus size={14} />Schedule Task
        </button>
      </div>

      {/* Search + View Toggle */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Clock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-tertiary" />
          <input type="text" placeholder="Search scheduled tasks..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition text-theme" disabled />
        </div>
        <div className="flex gap-0.5 bg-surface border border-theme rounded-lg p-0.5">
          <button onClick={() => setViewMode('list')} className={cn('px-3 py-1.5 rounded-md text-[11px] font-medium transition cursor-pointer', viewMode === 'list' ? 'bg-surface-2 text-theme' : 'text-theme-tertiary')}>List</button>
          <button onClick={() => setViewMode('calendar')} className={cn('px-3 py-1.5 rounded-md text-[11px] font-medium transition cursor-pointer', viewMode === 'calendar' ? 'bg-surface-2 text-theme' : 'text-theme-tertiary')}>Calendar</button>
        </div>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-16 text-theme-tertiary">
        <div className="w-16 h-16 rounded-2xl bg-surface border border-theme flex items-center justify-center mb-4">
          <Clock size={28} className="text-theme-tertiary" />
        </div>
        <p className="text-sm font-medium">No scheduled tasks</p>
        <p className="text-xs text-theme-tertiary mt-1 max-w-sm text-center">
          Create your first scheduled task to automate workflows on a recurring basis. The scheduler API is not yet connected.
        </p>
        <button onClick={() => setShowAdd(true)} className="mt-4 flex items-center gap-2 px-4 py-2 bg-theme hover:opacity-90 text-white text-xs font-semibold rounded-xl transition cursor-pointer">
          <Plus size={14} />Schedule Task
        </button>
      </div>

      {/* Add task modal */}
      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-theme/32" onClick={() => setShowAdd(false)}>
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()} className="w-full max-w-md rounded-xl border border-theme bg-surface p-5 space-y-4">
              <h2 className="text-sm font-bold text-theme">Schedule New Task</h2>
              <div className="p-4 rounded-lg bg-surface-2 border border-theme text-center text-xs text-theme-tertiary">
                Task scheduling is not yet available. The scheduler API will be connected in a future update.
              </div>
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-xs text-theme-tertiary hover:text-theme border border-theme rounded-lg transition cursor-pointer">Close</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
