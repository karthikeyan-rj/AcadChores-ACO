'use client';

import React, { useState } from 'react';
import {
  LayoutDashboard, MessageSquare, GitBranch, History, FileText,
  Database, BarChart3, Puzzle, Clock, Settings, ChevronLeft,
  ChevronRight, LogOut, PanelLeftClose, PanelLeft
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { useRouter } from 'next/navigation';

interface SidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { id: 'assistant', icon: MessageSquare, label: 'AI Assistant' },
  { id: 'workflows', icon: GitBranch, label: 'Workflows' },
  { id: 'history', icon: History, label: 'Execution History' },
  { id: 'files', icon: FileText, label: 'Files' },
  { id: 'memory', icon: Database, label: 'Memory' },
  { id: 'analytics', icon: BarChart3, label: 'Analytics' },
  { id: 'plugins', icon: Puzzle, label: 'Plugins' },
  { id: 'scheduler', icon: Clock, label: 'Scheduler' },
  { id: 'settings', icon: Settings, label: 'Settings' },
];

export function Sidebar({ activeSection, onSectionChange, collapsed, onToggle }: SidebarProps) {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <aside className={cn(
      'h-full border-r border-border bg-card/50 backdrop-blur-xl flex flex-col no-select shrink-0 transition-all duration-300',
      collapsed ? 'w-[60px]' : 'w-[220px]'
    )}>
      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSectionChange(item.id)}
              className={cn(
                'w-full flex items-center gap-3 rounded-lg transition-all duration-150 cursor-pointer group',
                collapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2',
                isActive
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-gray-400 hover:text-foreground hover:bg-surface-2 border border-transparent'
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={16} className={cn('shrink-0', isActive && 'text-primary')} />
              {!collapsed && (
                <span className="text-xs font-medium truncate">{item.label}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Collapse toggle + User */}
      <div className="border-t border-border p-2 space-y-1">
        <button
          onClick={onToggle}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:text-foreground hover:bg-surface-2 transition cursor-pointer"
        >
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>

        {!collapsed && user && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
            ) : (
              <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary text-[10px] font-bold">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium truncate">{user.name}</p>
              <p className="text-[9px] text-gray-500 truncate">{user.email}</p>
            </div>
          </div>
        )}
        <button
          onClick={() => { logout(); router.replace('/login'); }}
          className={cn(
            'w-full flex items-center gap-3 rounded-lg text-gray-500 hover:text-danger hover:bg-danger/5 transition cursor-pointer',
            collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2'
          )}
          title="Sign Out"
        >
          <LogOut size={14} />
          {!collapsed && <span className="text-xs">Sign Out</span>}
        </button>
      </div>
    </aside>
  );
}
