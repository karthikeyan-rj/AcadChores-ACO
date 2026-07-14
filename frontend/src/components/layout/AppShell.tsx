'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, GitBranch, History, FileText, BarChart3,
  Settings, LayoutDashboard, PanelLeftClose,
  PanelLeft, LogOut, Search, ChevronDown, Cpu, Globe, Wifi,
  Database as DbIcon, Layers, User
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { useBackendHealth } from '@/lib/hooks';
import { CommandPalette } from '@/components/modals/CommandPalette';

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
  const { user, token, logout, loading: authLoading } = useAuth();
  const backendConnected = useBackendHealth();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

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
    try {
      localStorage.setItem('aco-sidebar-collapsed', String(collapsed));
    } catch {}
  }, [collapsed]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') { e.preventDefault(); setCollapsed(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); router.push('/chat'); }
      if ((e.ctrlKey || e.metaKey) && e.key === ',') { e.preventDefault(); router.push('/settings'); }
      if (e.key === 'Escape') { setProfileOpen(false); setCmdOpen(false); setMobileOpen(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router]);

  useEffect(() => {
    if (!profileOpen) return;
    const handler = () => setProfileOpen(false);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [profileOpen]);

  // Close mobile sidebar on route change
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  if (pathname === '/' || pathname === '/login') {
    return <>{children}</>;
  }

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-surface-2 flex items-center justify-center">
            <Cpu size={18} className="text-primary" />
          </div>
          <span className="text-xs text-gray-500">Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const sidebarWidth = collapsed ? 56 : 200;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={(s) => { router.push(s); }} />

      {/* Mobile overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={cn(
          'h-full border-r border-border bg-surface flex flex-col no-select shrink-0 z-50',
          'fixed lg:relative transition-transform duration-200 ease-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        style={{ width: sidebarWidth }}
      >
        {/* Logo */}
        <div className="h-12 flex items-center px-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-7 h-7 rounded-md bg-primary/10 flex items-center justify-center shrink-0">
              <Cpu size={14} className="text-primary" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="font-semibold text-[13px] whitespace-nowrap text-foreground">ACO</span>
                <span className="text-[9px] text-gray-600 ml-1.5 whitespace-nowrap">v1.0</span>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 px-1.5 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.id || (item.id !== '/' && pathname.startsWith(item.id));
            return (
              <button
                key={item.id}
                onClick={() => { router.push(item.id); setMobileOpen(false); }}
                title={collapsed ? item.label : undefined}
                className={cn(
                  'w-full flex items-center gap-2.5 rounded-md transition-all duration-150 cursor-pointer group relative',
                  collapsed ? 'justify-center px-2 py-2' : 'px-2.5 py-1.5',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-500 hover:text-foreground hover:bg-surface-2'
                )}
              >
                <Icon size={15} className={cn('shrink-0', isActive && 'text-primary')} />
                {!collapsed && (
                  <span className="text-[12px] font-medium truncate whitespace-nowrap">
                    {item.label}
                  </span>
                )}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-3.5 rounded-r bg-primary" />
                )}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 rounded-md bg-surface-3 border border-border text-[11px] text-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="border-t border-border p-1.5 space-y-0.5">
          <button
            onClick={() => setCollapsed(p => !p)}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-gray-500 hover:text-foreground hover:bg-surface-2 transition cursor-pointer"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeft size={15} /> : <PanelLeftClose size={15} />}
            {!collapsed && <span className="text-[12px] whitespace-nowrap">Collapse</span>}
          </button>

          {/* User */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setProfileOpen(p => !p); }}
              className={cn(
                'w-full flex items-center gap-2 rounded-md bg-surface-2 transition cursor-pointer',
                collapsed ? 'justify-center px-2 py-1.5' : 'px-2.5 py-1.5'
              )}
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-5 h-5 rounded-full shrink-0" />
              ) : (
                <div className="w-5 h-5 rounded-full bg-primary/15 flex items-center justify-center text-primary text-[9px] font-bold shrink-0">
                  {user.name.charAt(0).toUpperCase()}
                </div>
              )}
              {!collapsed && (
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-[11px] font-medium truncate text-foreground">{user.name}</p>
                  <p className="text-[9px] text-gray-600 truncate">{user.email}</p>
                </div>
              )}
              {!collapsed && <ChevronDown size={11} className="text-gray-600 shrink-0" />}
            </button>

            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.12 }}
                  className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border border-border bg-card shadow-xl overflow-hidden z-50"
                >
                  <div className="p-0.5">
                    <button
                      onClick={() => { router.push('/settings'); setProfileOpen(false); }}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[12px] text-gray-400 hover:text-foreground hover:bg-surface-2 transition cursor-pointer"
                    >
                      <User size={12} />Settings
                    </button>
                  </div>
                  <div className="border-t border-border p-0.5">
                    <button
                      onClick={() => { logout(); router.replace('/login'); setProfileOpen(false); }}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[12px] text-danger hover:bg-danger/5 transition cursor-pointer"
                    >
                      <LogOut size={12} />Sign Out
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <header className="h-11 border-b border-border bg-surface flex items-center justify-between px-4 no-select shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(p => !p)}
              className="lg:hidden p-1 rounded-md hover:bg-surface-2 transition text-gray-400 cursor-pointer"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface-2 border border-border text-gray-500 text-[11px] hover:border-border-light hover:text-gray-400 transition cursor-pointer w-[220px]"
            >
              <Search size={11} />
              <span>Search or command...</span>
              <kbd className="ml-auto text-[9px] bg-surface-3 px-1.5 py-0.5 rounded border border-border font-mono text-gray-600">Ctrl+K</kbd>
            </button>
          </div>
          <div className="flex items-center gap-2">
            <StatusPill icon={<DbIcon size={9} />} label="Mongo" active={backendConnected} />
            <StatusPill icon={<Wifi size={9} />} label="Redis" active={backendConnected} />
            <StatusPill icon={<Globe size={9} />} label="Browser" active={backendConnected} />
            <div className="h-3.5 w-px bg-border mx-1" />
            <button
              onClick={() => router.push('/settings')}
              className="p-1.5 rounded-md hover:bg-surface-2 transition text-gray-500 hover:text-foreground cursor-pointer"
              title="Settings"
            >
              <Settings size={14} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Status bar */}
        <footer className="h-6 border-t border-border bg-surface flex items-center justify-between px-4 no-select text-[10px] text-gray-600 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className={cn('h-1 w-1 rounded-full', backendConnected ? 'bg-accent' : 'bg-danger')} />
              Backend
            </span>
            <span className="flex items-center gap-1"><span className="h-1 w-1 rounded-full bg-accent" />Mongo</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Windows Native</span>
            <span className="flex items-center gap-1"><Layers size={9} />3 Workers</span>
            <span className="flex items-center gap-1"><Cpu size={9} />Ollama</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

function StatusPill({ icon, label, active }: { icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <span className="hidden lg:flex items-center gap-1.5 px-1.5 py-0.5 rounded text-[10px]" title={label}>
      <span className={cn('h-1.5 w-1.5 rounded-full', active ? 'bg-accent' : 'bg-gray-700')} />
      <span className={active ? 'text-gray-400' : 'text-gray-600'}>{label}</span>
    </span>
  );
}
