'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import {
  MessageSquare, GitBranch, History, FileText, BarChart3,
  Settings, LayoutDashboard, PanelLeftClose,
  PanelLeft, Search, ChevronDown, Cpu, User, Menu, LogOut, Server, Check
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import { useSystemHealth } from '@/lib/health';
import { useWorkflowStore } from '@/lib/workflow-store';
import { CommandPalette } from '@/components/modals/CommandPalette';
import { PageSkeleton } from '@/components/ui/PageSkeleton';

const navItems = [
  { id: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: '/chat', icon: MessageSquare, label: 'AI Assistant' },
  { id: '/workflows', icon: GitBranch, label: 'Workflows' },
  { id: '/history', icon: History, label: 'History' },
  { id: '/files', icon: FileText, label: 'Files' },
  { id: '/analytics', icon: BarChart3, label: 'Analytics' },
  { id: '/settings', icon: Settings, label: 'Settings' },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout, loading: authLoading } = useAuth();
  const { theme, setTheme } = useTheme();
  const { services, overallStatus } = useSystemHealth();
  const { hasActiveWorkflow, status: workflowStatus } = useWorkflowStore();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const cmdTriggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('aco-sidebar-collapsed');
      if (stored !== null) setCollapsed(stored === 'true');
    } catch {}
  }, []);

  useEffect(() => {
    if (!authLoading && !user && pathname !== '/login' && pathname !== '/') {
      router.replace('/login');
    }
  }, [user, authLoading, pathname, router]);

  useEffect(() => {
    try { localStorage.setItem('aco-sidebar-collapsed', String(collapsed)); } catch {}
  }, [collapsed]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') { e.preventDefault(); setCollapsed(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); router.push('/chat'); }
      if ((e.ctrlKey || e.metaKey) && e.key === ',') { e.preventDefault(); router.push('/settings'); }
      if (e.key === 'Escape') { setProfileOpen(false); setCmdOpen(false); setMobileOpen(false); setStatusOpen(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router]);

  useEffect(() => {
    if (!profileOpen) return;
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [profileOpen]);

  useEffect(() => {
    if (!statusOpen) return;
    const handler = (e: MouseEvent) => {
      if (statusRef.current && !statusRef.current.contains(e.target as Node)) setStatusOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [statusOpen]);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  if (pathname === '/' || pathname === '/login') {
    return <>{children}</>;
  }

  if (!user && !authLoading) return null;

  const sidebarWidth = collapsed ? 56 : 248;

  const overallDotClass = overallStatus === 'connected' ? 'bg-status-active'
    : overallStatus === 'degraded' ? 'bg-status-warning'
    : 'bg-status-error';

  const overallTextClass = overallStatus === 'connected' ? 'text-status-active'
    : overallStatus === 'degraded' ? 'text-status-warning'
    : 'text-status-error';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-app text-theme">
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={(s) => { router.push(s); }} triggerRef={cmdTriggerRef} />

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/32 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={cn(
          'h-full border-r border-theme bg-sidebar flex flex-col no-select shrink-0 z-50',
          'fixed lg:relative transition-[width,transform] duration-200 ease-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        style={{ width: sidebarWidth }}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="h-[56px] flex items-center justify-between px-3 border-b border-theme shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
            <div className="w-7 h-7 rounded-lg bg-theme text-theme-inverse flex items-center justify-center shrink-0">
              <Cpu size={15} />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="font-semibold text-[13px] whitespace-nowrap text-theme">ACO</span>
                <span className="text-[9px] text-theme-tertiary ml-1.5 whitespace-nowrap">v1.0</span>
              </div>
            )}
          </div>
          <button
            onClick={() => setCollapsed(p => !p)}
            className={cn(
              'shrink-0 rounded-md transition-all duration-150 cursor-pointer',
              'text-theme-tertiary hover:text-theme hover:bg-surface-hover',
              collapsed ? 'p-1.5' : 'p-1.5'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto" aria-label="Sidebar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.id || (item.id !== '/' && pathname.startsWith(item.id));
            return (
              <button
                key={item.id}
                onClick={() => { router.push(item.id); setMobileOpen(false); }}
                title={collapsed ? item.label : undefined}
                aria-label={item.label}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'w-full flex items-center gap-2.5 rounded-lg transition-all duration-150 cursor-pointer group relative',
                  collapsed ? 'justify-center px-2 h-10' : 'px-2.5 h-10',
                  isActive
                    ? 'bg-[var(--surface-active)] border border-theme text-theme'
                    : 'text-theme-secondary hover:text-theme hover:bg-surface-hover border border-transparent'
                )}
              >
                <Icon size={18} className={cn('shrink-0', isActive && 'text-theme')} />
                {item.id === '/chat' && hasActiveWorkflow && (
                  <span className={cn(
                    'absolute right-2 top-2 h-1.5 w-1.5 rounded-full',
                    workflowStatus === 'Planning' ? 'bg-status-warning animate-pulse'
                    : workflowStatus === 'Stopping' ? 'bg-status-error animate-pulse'
                    : 'bg-status-active animate-pulse'
                  )} />
                )}
                {!collapsed && (
                  <span className="text-[13px] font-medium truncate whitespace-nowrap">
                    {item.label}
                  </span>
                )}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 rounded-md bg-surface border border-theme text-[11px] text-theme whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-theme-dropdown">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {hasActiveWorkflow && !collapsed && (
          <div className="mx-2 mb-2 px-2.5 py-2 rounded-lg border border-status-active/30 bg-surface">
            <div className="flex items-center gap-2">
              <span className={cn(
                'h-1.5 w-1.5 rounded-full shrink-0',
                workflowStatus === 'Planning' ? 'bg-status-warning animate-pulse'
                : workflowStatus === 'Stopping' ? 'bg-status-error animate-pulse'
                : 'bg-status-active animate-pulse'
              )} />
              <span className="text-[11px] font-medium text-status-active truncate">
                {workflowStatus === 'Planning' ? 'Planning...'
                 : workflowStatus === 'Executing' ? 'Running...'
                 : workflowStatus === 'Waiting' ? 'Awaiting...'
                 : workflowStatus === 'Stopping' ? 'Stopping...'
                 : workflowStatus}
              </span>
            </div>
            <button
              onClick={() => { router.push('/chat'); setMobileOpen(false); }}
              className="mt-1 text-[10px] text-status-active/70 hover:text-status-active transition cursor-pointer"
            >
              View in Assistant
            </button>
          </div>
        )}

        <div className="h-2 shrink-0" />
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <header className="h-[56px] border-b border-theme bg-header backdrop-blur-sm flex items-center justify-between px-4 no-select shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(p => !p)}
              className="lg:hidden p-1.5 rounded-lg hover:bg-surface-hover transition text-theme-secondary cursor-pointer"
              aria-label="Toggle mobile menu"
            >
              <Menu size={20} />
            </button>
            <span className="text-[14px] font-semibold text-theme">
              {navItems.find(n => pathname === n.id || pathname.startsWith(n.id))?.label || 'ACO'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              ref={cmdTriggerRef}
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-theme bg-surface text-theme-tertiary text-[12px] hover:border-theme-strong hover:text-theme-secondary transition cursor-pointer w-[220px]"
              aria-label="Open command palette"
            >
              <Search size={13} />
              <span>Search or command...</span>
              <kbd className="ml-auto text-[9px] bg-surface-hover px-1.5 py-0.5 rounded border border-theme font-mono text-theme-tertiary">Ctrl+K</kbd>
            </button>
            <div className="h-4 w-px bg-theme mx-1" />

            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen(p => !p)}
                className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-surface-hover transition cursor-pointer"
                aria-label="User menu"
                aria-expanded={profileOpen}
                aria-haspopup="true"
              >
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-theme text-theme-inverse flex items-center justify-center text-[10px] font-bold">
                    {user?.name?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                )}
                <ChevronDown size={13} className={cn('text-theme-tertiary transition-transform duration-150', profileOpen && 'rotate-180')} />
              </button>

              <AnimatePresence>
                {profileOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 4 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1 w-56 rounded-xl border border-theme bg-surface-elevated overflow-hidden z-50 shadow-theme-dropdown"
                    role="menu"
                    aria-label="User menu"
                  >
                    <div className="px-3 py-2.5 border-b border-theme">
                      <p className="text-[12px] font-medium text-theme truncate">{user?.name || 'User'}</p>
                      <p className="text-[10px] text-theme-tertiary truncate mt-0.5">{user?.email || ''}</p>
                    </div>
                    <div className="p-1" role="group">
                      <button
                        onClick={() => { router.push('/settings'); setProfileOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-theme-secondary hover:text-theme hover:bg-surface-hover transition cursor-pointer"
                        role="menuitem"
                      >
                        <Settings size={14} />
                        <span>Settings</span>
                      </button>
                    </div>
                    <div className="border-t border-theme p-1">
                      <p className="px-3 py-1 text-[10px] font-medium text-theme-tertiary uppercase tracking-wider">Theme</p>
                      <button
                        onClick={() => setTheme('dark')}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[12px] transition cursor-pointer',
                          theme === 'dark' ? 'text-theme font-medium' : 'text-theme-secondary hover:text-theme hover:bg-surface-hover'
                        )}
                        role="menuitem"
                      >
                        <span className={cn('w-2 h-2 rounded-full', theme === 'dark' ? 'bg-theme' : 'bg-theme-tertiary')} />
                        <span>Dark Professional</span>
                        {theme === 'dark' && <Check size={12} className="ml-auto text-theme" />}
                      </button>
                      <button
                        onClick={() => setTheme('light')}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[12px] transition cursor-pointer',
                          theme === 'light' ? 'text-theme font-medium' : 'text-theme-secondary hover:text-theme hover:bg-surface-hover'
                        )}
                        role="menuitem"
                      >
                        <span className={cn('w-2 h-2 rounded-full', theme === 'light' ? 'bg-theme' : 'bg-theme-tertiary')} />
                        <span>Nordic Alabaster</span>
                        {theme === 'light' && <Check size={12} className="ml-auto text-theme" />}
                      </button>
                      <button
                        onClick={() => setTheme('system')}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[12px] transition cursor-pointer',
                          theme === 'system' ? 'text-theme font-medium' : 'text-theme-secondary hover:text-theme hover:bg-surface-hover'
                        )}
                        role="menuitem"
                      >
                        <span className={cn('w-2 h-2 rounded-full', theme === 'system' ? 'bg-theme' : 'bg-theme-tertiary')} />
                        <span>System</span>
                        {theme === 'system' && <Check size={12} className="ml-auto text-theme" />}
                      </button>
                    </div>
                    <div className="border-t border-theme p-1">
                      <button
                        onClick={() => { logout(); router.replace('/login'); setProfileOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-status-error hover:bg-status-error-soft transition cursor-pointer"
                        role="menuitem"
                      >
                        <LogOut size={14} />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {authLoading ? <PageSkeleton /> : children}
        </main>

        <footer className="h-7 border-t border-theme bg-header backdrop-blur-sm flex items-center justify-between px-4 no-select text-[10px] text-theme-tertiary font-mono shrink-0">
          <div className="flex items-center gap-3">
            <span>{user?.email || ''}</span>
          </div>
          <div className="relative" ref={statusRef}>
            <button
              onClick={() => setStatusOpen(p => !p)}
              className="flex items-center gap-2 px-2.5 py-1 rounded-md hover:bg-surface-hover transition cursor-pointer"
              aria-label="System status"
              aria-expanded={statusOpen}
            >
              <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', overallDotClass)} />
              <span>System</span>
              <Server size={10} className="text-theme-tertiary" />
            </button>

            <AnimatePresence>
              {statusOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.12 }}
                  className="absolute right-0 bottom-full mb-2 w-[260px] rounded-xl border border-theme bg-surface-elevated overflow-hidden z-50 shadow-theme-dropdown"
                  role="dialog"
                  aria-label="System services status"
                >
                  <div className="px-3 py-2.5 border-b border-theme flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-theme">System Services</span>
                    <span className={cn('text-[9px] font-medium', overallTextClass)}>
                      {overallStatus === 'connected' ? 'All Operational' : overallStatus === 'degraded' ? 'Degraded' : 'Offline'}
                    </span>
                  </div>
                  <div className="p-2 space-y-0.5">
                    {services.map((s) => {
                      const dotClass = s.status === 'connected' ? 'bg-status-active'
                        : s.status === 'disabled' ? 'bg-theme-tertiary'
                        : s.status === 'reconnecting' ? 'bg-status-warning'
                        : 'bg-status-error';
                      const labelClass = s.status === 'connected' ? 'text-status-active'
                        : s.status === 'disabled' ? 'text-theme-tertiary'
                        : s.status === 'reconnecting' ? 'text-status-warning'
                        : 'text-status-error';
                      return (
                        <div key={s.name} className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-surface-hover transition">
                          <span className="text-[11px] text-theme-secondary">{s.name}</span>
                          <span className="flex items-center gap-1.5">
                            <span className={cn('h-1.5 w-1.5 rounded-full', dotClass)} />
                            <span className={cn('text-[9px] font-medium', labelClass)}>
                              {s.label || (s.status === 'connected' ? 'Connected' : s.status === 'disabled' ? 'Disabled' : s.status === 'reconnecting' ? 'Reconnecting' : 'Disconnected')}
                            </span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </footer>
      </div>
    </div>
  );
}
