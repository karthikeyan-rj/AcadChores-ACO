'use client';

import React from 'react';
import {
  Search, Bell, Settings, Cpu, Database, Wifi, Globe,
  ChevronDown, Terminal
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TopNavProps {
  backendConnected: boolean;
  wsConnected: boolean;
  onCommandPalette: () => void;
}

export function TopNav({ backendConnected, wsConnected, onCommandPalette }: TopNavProps) {
  return (
    <header className="h-12 border-b border-border bg-card/50 backdrop-blur-xl flex items-center justify-between px-4 no-select z-50 shrink-0">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Cpu size={18} className="text-primary" />
            <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-accent animate-pulse" />
          </div>
          <span className="font-bold text-sm tracking-wide">ACO</span>
          <span className="text-[10px] text-gray-500 font-medium hidden sm:inline">Enterprise Orchestrator</span>
        </div>
        <div className="h-4 w-px bg-border mx-1 hidden md:block" />
        {/* Global Search trigger */}
        <button
          onClick={onCommandPalette}
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-gray-500 text-xs hover:border-border-light hover:text-gray-400 transition cursor-pointer"
        >
          <Search size={12} />
          <span>Search</span>
          <kbd className="ml-4 text-[10px] bg-surface-2 px-1.5 py-0.5 rounded border border-border font-mono">Ctrl+K</kbd>
        </button>
      </div>

      {/* Right: Status indicators */}
      <div className="flex items-center gap-1">
        <StatusIndicator icon={<Database size={12} />} label="Mongo" active={backendConnected} />
        <StatusIndicator icon={<Wifi size={12} />} label="WebSocket" active={wsConnected} />
        <StatusIndicator icon={<Globe size={12} />} label="Browser" active={backendConnected} />
        <StatusIndicator icon={<Terminal size={12} />} label="Workers" active={backendConnected} />

        <div className="h-4 w-px bg-border mx-1.5" />

        <button className="p-1.5 rounded-lg hover:bg-surface-2 transition text-gray-400 hover:text-foreground cursor-pointer relative">
          <Bell size={15} />
          <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-primary" />
        </button>
        <button className="p-1.5 rounded-lg hover:bg-surface-2 transition text-gray-400 hover:text-foreground cursor-pointer">
          <Settings size={15} />
        </button>
      </div>
    </header>
  );
}

function StatusIndicator({ icon, label, active }: { icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <div className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px]" title={label}>
      <span className={cn('h-1.5 w-1.5 rounded-full', active ? 'bg-accent' : 'bg-gray-600')} />
      <span className="text-gray-500">{label}</span>
    </div>
  );
}
