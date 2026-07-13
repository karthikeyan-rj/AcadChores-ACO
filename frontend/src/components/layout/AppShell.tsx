'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, GitBranch, History, FileText, Database, BarChart3,
  Puzzle, Clock, Settings, HelpCircle, LayoutDashboard, PanelLeftClose,
  PanelLeft, LogOut, Search, Bell, ChevronDown, Cpu, Globe, Wifi,
  Database as DbIcon, Terminal, HardDrive, Activity, Layers, Shield,
  Moon, Sun, Keyboard, User
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { useBackendHealth } from '@/lib/hooks';
import { CommandPalette } from '@/components/modals/CommandPalette';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';

const navItems = [
  { id: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: '/chat', icon: MessageSquare, label: 'AI Assistant' },
  { id: '/workflows', icon: GitBranch, label: 'Workflows' },
  { id: '/history', icon: History, label: 'History' },
  { id: '/files', icon: FileText, label: 'Files' },
  { id: '/memory', icon: Database, label: 'Memory' },
  { id: '/analytics', icon: BarChart3, label: 'Analytics' },
  { id: '/plugins', icon: Puzzle, label: 'Plugins' },
  { id: '/scheduler', icon: Clock, label: 'Scheduler' },
  { id: '/settings', icon: Settings, label: 'Settings' },
  { id: '/help', icon: HelpCircle, label: 'Help' },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token, logout, loading: authLoading } = useAuth();
  const backendConnected = useBackendHealth();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  // IMPORTANT: All hooks MUST be called before any conditional returns.
  // Restore sidebar state from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('aco-sidebar-collapsed');
      if (stored !== null) setCollapsed(stored === 'true');
    } catch {}
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user && pathname !== '/login' && pathname !== '/') {
      router.replace('/login');
    }
  }, [user, authLoading, pathname, router]);

  // Save sidebar state
  useEffect(() => {
    try {
      localStorage.setItem('aco-sidebar-collapsed', String(collapsed));
    } catch {}
  }, [collapsed]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setCmdOpen(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') { e.preventDefault(); setCollapsed(p => !p); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); router.push('/chat'); }
      if ((e.ctrlKey || e.metaKey) && e.key === ',') { e.preventDefault(); router.push('/settings'); }
      if (e.key === 'Escape') { setProfileOpen(false); setNotifOpen(false); setCmdOpen(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router]);

  // Close profile dropdown on outside click
  useEffect(() => {
    if (!profileOpen) return;
    const handler = () => setProfileOpen(false);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [profileOpen]);

  // === CONDITIONAL RENDERS (after all hooks) ===

  // Landing page and login — render without shell
  if (pathname === '/' || pathname === '/login') {
    return <>{children}</>;
  }

  // Loading state — show nothing until auth is resolved
  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center animate-pulse">
            <Cpu size={20} className="text-primary" />
          </div>
          <span className="text-xs text-gray-500">Loading ACO...</span>
        </div>
      </div>
    );
  }

  // Not authenticated — show nothing (redirect is happening via useEffect)
  if (!user) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center animate-pulse">
            <Cpu size={20} className="text-primary" />
          </div>
          <span className="text-xs text-gray-500">Redirecting to login...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={(s) => { router.push(s); }} />
      <NotificationCenter open={notifOpen} onClose={() => setNotifOpen(false)} />

      {/* Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 60 : 220 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="h-full border-r border-border bg-card/50 backdrop-blur-xl flex flex-col no-select shrink-0 relative z-40"
      >
        {/* Logo */}
        <div className="h-12 flex items-center px-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
              <Cpu size={16} className="text-primary" />
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }} className="overflow-hidden">
                  <span className="font-bold text-sm whitespace-nowrap">ACO</span>
                  <span className="text-[9px] text-gray-500 ml-1.5 whitespace-nowrap">v1.0</span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.id || (item.id !== '/' && pathname.startsWith(item.id));
            return (
              <button
                key={item.id}
                onClick={() => router.push(item.id)}
                title={collapsed ? item.label : undefined}
                className={cn(
                  'w-full flex items-center gap-3 rounded-lg transition-all duration-150 cursor-pointer group relative',
                  collapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2',
                  isActive
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-gray-400 hover:text-foreground hover:bg-surface-2 border border-transparent'
                )}
              >
                <Icon size={16} className={cn('shrink-0', isActive && 'text-primary')} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }} className="text-xs font-medium truncate overflow-hidden whitespace-nowrap">
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {isActive && <motion.div layoutId="sidebar-indicator" className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r bg-primary" />}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 rounded-md bg-surface-3 border border-border text-xs text-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-lg">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-border p-2 space-y-1">
          <button
            onClick={() => setCollapsed(p => !p)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:text-foreground hover:bg-surface-2 transition cursor-pointer"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
            <AnimatePresence>
              {!collapsed && (
                <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-xs whitespace-nowrap">Collapse</motion.span>
              )}
            </AnimatePresence>
          </button>

          {/* User pill */}
          <div className="relative">
            <button
              onClick={(e) => { e.stopPropagation(); setProfileOpen(p => !p); }}
              className={cn(
                'w-full flex items-center gap-2 rounded-lg bg-surface transition cursor-pointer',
                collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2'
              )}
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full shrink-0" />
              ) : (
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary text-[10px] font-bold shrink-0">
                  {user.name.charAt(0).toUpperCase()}
                </div>
              )}
              <AnimatePresence>
                {!collapsed && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 min-w-0 text-left">
                    <p className="text-[11px] font-medium truncate">{user.name}</p>
                    <p className="text-[9px] text-gray-500 truncate">{user.email}</p>
                  </motion.div>
                )}
              </AnimatePresence>
              {!collapsed && <ChevronDown size={12} className="text-gray-500 shrink-0" />}
            </button>

            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.96 }}
                  className="absolute bottom-full left-0 right-0 mb-1 rounded-xl border border-border bg-card shadow-2xl overflow-hidden z-50"
                >
                  <div className="p-1">
                    <ProfileMenuItem icon={<User size={13} />} label="Profile" onClick={() => { router.push('/settings'); setProfileOpen(false); }} />
                    <ProfileMenuItem icon={<Settings size={13} />} label="Settings" onClick={() => { router.push('/settings'); setProfileOpen(false); }} />
                    <ProfileMenuItem icon={<Moon size={13} />} label="Theme" onClick={() => setProfileOpen(false)} />
                    <ProfileMenuItem icon={<Keyboard size={13} />} label="Shortcuts" onClick={() => { router.push('/help'); setProfileOpen(false); }} />
                    <ProfileMenuItem icon={<HelpCircle size={13} />} label="About" onClick={() => { router.push('/help'); setProfileOpen(false); }} />
                  </div>
                  <div className="border-t border-border p-1">
                    <ProfileMenuItem icon={<LogOut size={13} />} label="Sign Out" danger onClick={() => { logout(); router.replace('/login'); setProfileOpen(false); }} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top Nav */}
        <header className="h-12 border-b border-border bg-card/50 backdrop-blur-xl flex items-center justify-between px-4 no-select shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-gray-500 text-xs hover:border-border-light hover:text-gray-400 transition cursor-pointer w-[240px]"
            >
              <Search size={12} />
              <span>Search or type a command...</span>
              <kbd className="ml-auto text-[10px] bg-surface-2 px-1.5 py-0.5 rounded border border-border font-mono">Ctrl+K</kbd>
            </button>
          </div>
          <div className="flex items-center gap-1">
            <StatusPill icon={<DbIcon size={10} />} label="Mongo" active={backendConnected} />
            <StatusPill icon={<Wifi size={10} />} label="Redis" active={backendConnected} />
            <StatusPill icon={<Globe size={10} />} label="Browser" active={backendConnected} />
            <div className="h-4 w-px bg-border mx-1.5" />
            <button
              onClick={() => setNotifOpen(p => !p)}
              className="p-1.5 rounded-lg hover:bg-surface-2 transition text-gray-400 hover:text-foreground cursor-pointer relative"
            >
              <Bell size={15} />
              <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-primary" />
            </button>
            <button
              onClick={() => router.push('/settings')}
              className="p-1.5 rounded-lg hover:bg-surface-2 transition text-gray-400 hover:text-foreground cursor-pointer"
              title="Settings (Ctrl+,)"
            >
              <Settings size={15} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Status Bar */}
        <footer className="h-6 border-t border-border bg-card/30 backdrop-blur-xl flex items-center justify-between px-4 no-select text-[10px] text-gray-500 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1"><span className={cn('h-1 w-1 rounded-full', backendConnected ? 'bg-accent' : 'bg-danger')} />Backend</span>
            <span className="flex items-center gap-1"><span className="h-1 w-1 rounded-full bg-accent" />Mongo</span>
            <span className="flex items-center gap-1"><span className="h-1 w-1 rounded-full bg-accent" />Redis</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">Host: Windows Native</span>
            <span className="flex items-center gap-1"><Layers size={10} />3 Workers</span>
            <span className="flex items-center gap-1"><Cpu size={10} />Ollama</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

function StatusPill({ icon, label, active }: { icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <span className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px]" title={label}>
      <span className={cn('h-1.5 w-1.5 rounded-full', active ? 'bg-accent' : 'bg-gray-600')} />
      <span className={active ? 'text-gray-400' : 'text-gray-600'}>{label}</span>
    </span>
  );
}

function ProfileMenuItem({ icon, label, onClick, danger = false }: { icon: React.ReactNode; label: string; onClick: () => void; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition cursor-pointer',
        danger ? 'text-danger hover:bg-danger/5' : 'text-gray-400 hover:text-foreground hover:bg-surface-2'
      )}
    >
      {icon}
      {label}
    </button>
  );
}
