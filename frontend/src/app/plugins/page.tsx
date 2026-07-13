'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Puzzle, Search, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function PluginsPage() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('All');

  const categories = ['All', 'Browser', 'Terminal', 'File', 'Vision', 'Database', 'Utility'];

  return (
    <div className="p-6 space-y-5 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Plugin Marketplace</h1>
          <p className="text-xs text-gray-500 mt-0.5">No plugins available — plugin API not connected</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input type="text" placeholder="Search plugins..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-card border border-border rounded-lg outline-none focus:border-primary transition" disabled />
        </div>
        <div className="flex gap-1">
          {categories.map(c => (
            <button key={c} onClick={() => setCategory(c)}
              className={cn('px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer border',
                category === c ? 'bg-primary/10 text-primary border-primary/30' : 'bg-card border-border text-gray-400 hover:text-foreground')}>
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-16 text-gray-500">
        <div className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center mb-4">
          <Puzzle size={28} className="text-gray-600" />
        </div>
        <p className="text-sm font-medium">No plugins available</p>
        <p className="text-xs text-gray-600 mt-1 max-w-sm text-center">
          The plugin marketplace is not connected. Plugins will appear here once the backend plugin API is available.
        </p>
      </div>
    </div>
  );
}
