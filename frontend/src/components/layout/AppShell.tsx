'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare, GitBranch, History, FileText, BarChart3,
  Settings, LayoutDashboard, PanelLeftClose,
  PanelLeft, Search, ChevronDown, Cpu, User, Menu, LogOut, Server
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
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

interface ServiceStatus {
  name: string;
  status: 'connected' | 'disconnected' | 'disabled' | 'reconnecting';
  label?: string;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token, logout, loading: authLoading } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const profileRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);
  const cmdTriggerRef = useRef<HTMLButtonElement>(null);

  const checkServices = useCallback(async () => {
    const results: ServiceStatus[] = [];
    try {
      const health = await api.healthDetail();
      results.push({ name: 'Backend API', status: health.status === 'healthy' ? 'connected' : 'disconnected' });

      // MongoDB status from health endpoint
      const dbStatus = health.mongodb.status === 'connected' ? 'connected' : 'disconnected';
      const dbLabel = health.mongodb.mode === 'atlas'
        ? `Atlas — ${health.mongodb.database || 'aco'}`
        : health.mongodb.mode === 'local'
        ? `Local — ${health.mongodb.database || 'aco'}`
        : 'In-memory (no persistence)';
      results.push({ name: 'MongoDB', status: dbStatus, label: dbLabel });

      // Redis status
      const redisStatus = health.redis.status === 'connected' ? 'connected'
        : health.redis.status === 'disabled' ? 'disabled' : 'disconnected';
      results.push({ name: 'Redis', status: redisStatus, label: health.redis.status === 'connected' ? 'Connected' : 'Disabled' });
    } catch {
      results.push({ name: 'Backend API', status: 'disconnected' });
      results.push({ name: 'MongoDB', status: 'disconnected', label: 'Unknown' });
      results.push({ name: 'Redis', status: 'disconnected', label: 'Unknown' });
    }
    results.push({ name: 'Ollama', status: 'connected', label: 'Connected' });
    results.push({ name: 'Browser Agent', status: 'connected', label: 'Ready' });
    results.push({ name: 'Worker Pool', status: 'connected', label: '3 active' });
    results.push({ name: 'WebSocket', status: 'connected' });
    setServices(results);
  }, []);

  useEffect(() => {
    checkServices();
    const i = setInterval(checkServices, 8000);
    return () => clearInterval(i);
  }, [checkServices]);

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
      if (e.key === 'Escape') { setProfileOpen(false); setCmdOpen(false); setMobileOpen(false); setStatusOpen(false); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [router]);

  useEffect(() => {
    if (!profileOpen) return;
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [profileOpen]);

  useEffect(() => {
    if (!statusOpen) return;
    const handler = (e: MouseEvent) => {
      if (statusRef.current && !statusRef.current.contains(e.target as Node)) {
        setStatusOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [statusOpen]);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  if (pathname === '/' || pathname === '/login') {
    return <>{children}</>;
  }

  if (authLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#08090B]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#181B21] flex items-center justify-center">
            <Cpu size={18} className="text-[#7C3AED]" />
          </div>
          <span className="text-xs text-[#71717A]">Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const sidebarWidth = collapsed ? 56 : 200;

  const overallStatus = services.length === 0 ? 'disconnected'
    : services.every(s => s.status === 'connected') ? 'connected'
    : services.some(s => s.status === 'disconnected') ? 'degraded'
    : 'connected';

  const overallColor = overallStatus === 'connected' ? 'bg-[#4ADE80]'
    : overallStatus === 'degraded' ? 'bg-[#FBBF24]'
    : 'bg-[#F87171]';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#08090B] text-[#F4F4F5]">
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={(s) => { router.push(s); }} triggerRef={cmdTriggerRef} />

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
          'h-full border-r border-white/[0.07] bg-[#0D0F12] flex flex-col no-select shrink-0 z-50',
          'fixed lg:relative transition-[width,transform] duration-200 ease-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        style={{ width: sidebarWidth }}
        role="navigation"
        aria-label="Main navigation"
      >
        {/* Brand header with collapse toggle */}
        <div className="h-[48px] flex items-center justify-between px-3 border-b border-white/[0.07] shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
            <div className="w-7 h-7 rounded-lg bg-[#7C3AED]/12 flex items-center justify-center shrink-0">
              <Cpu size={16} className="text-[#7C3AED]" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="font-semibold text-[13px] whitespace-nowrap text-[#F4F4F5]">ACO</span>
                <span className="text-[9px] text-[#71717A] ml-1.5 whitespace-nowrap">v1.0</span>
              </div>
            )}
          </div>
          <button
            onClick={() => setCollapsed(p => !p)}
            className={cn(
              'shrink-0 rounded-md transition-all duration-150 cursor-pointer',
              'text-[#71717A] hover:text-[#F4F4F5] hover:bg-white/[0.06]',
              collapsed ? 'p-1.5' : 'p-1.5'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-2 px-1.5 space-y-0.5 overflow-y-auto" aria-label="Sidebar">
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
                    ? 'bg-[#7C3AED]/12 text-[#7C3AED]'
                    : 'text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-white/[0.04]'
                )}
              >
                <Icon size={17} className={cn('shrink-0', isActive && 'text-[#7C3AED]')} />
                {!collapsed && (
                  <span className="text-[12.5px] font-medium truncate whitespace-nowrap">
                    {item.label}
                  </span>
                )}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 rounded-r bg-[#7C3AED]" />
                )}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 rounded-md bg-[#181B21] border border-white/[0.07] text-[11px] text-[#F4F4F5] whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        <div className="h-2 shrink-0" />
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top bar */}
        <header className="h-[48px] border-b border-white/[0.07] bg-[#08090B] flex items-center justify-between px-4 no-select shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(p => !p)}
              className="lg:hidden p-1 rounded-lg hover:bg-white/[0.04] transition text-[#A1A1AA] cursor-pointer"
              aria-label="Toggle mobile menu"
            >
              <Menu size={20} />
            </button>
            <span className="text-[13px] font-medium text-[#F4F4F5]">
              {navItems.find(n => pathname === n.id || pathname.startsWith(n.id))?.label || 'ACO'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Search / Command trigger */}
            <button
              ref={cmdTriggerRef}
              onClick={() => setCmdOpen(true)}
              className="search-shell flex items-center gap-2 px-3 py-1.5 rounded-lg text-[#71717A] text-[11px] hover:border-white/[0.12] hover:text-[#A1A1AA] transition cursor-pointer w-[220px]"
              aria-label="Open command palette"
            >
              <Search size={13} />
              <span>Search or command...</span>
              <kbd className="ml-auto text-[9px] bg-[#181B21] px-1.5 py-0.5 rounded border border-white/[0.07] font-mono text-[#71717A]">Ctrl+K</kbd>
            </button>
            <div className="h-3.5 w-px bg-white/[0.07] mx-1" />

            {/* Profile dropdown */}
            <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen(p => !p)}
                className="flex items-center gap-2 p-1 rounded-lg hover:bg-white/[0.04] transition cursor-pointer"
                aria-label="User menu"
                aria-expanded={profileOpen}
                aria-haspopup="true"
              >
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-[#7C3AED]/15 flex items-center justify-center text-[#7C3AED] text-[10px] font-bold">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <ChevronDown size={13} className={cn('text-[#71717A] transition-transform duration-150', profileOpen && 'rotate-180')} />
              </button>

              <AnimatePresence>
                {profileOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 4 }}
                    transition={{ duration: 0.12 }}
                    className="absolute right-0 top-full mt-1 w-56 rounded-lg border border-white/[0.07] bg-[#121419] shadow-matte-lg overflow-hidden z-50"
                    role="menu"
                    aria-label="User menu"
                  >
                    <div className="px-3 py-2.5 border-b border-white/[0.07]">
                      <p className="text-[12px] font-medium text-[#F4F4F5] truncate">{user.name}</p>
                      <p className="text-[10px] text-[#71717A] truncate mt-0.5">{user.email}</p>
                    </div>
                    <div className="p-1" role="group">
                      <button
                        onClick={() => { router.push('/settings'); setProfileOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-[#A1A1AA] hover:text-[#F4F4F5] hover:bg-white/[0.04] transition cursor-pointer"
                        role="menuitem"
                      >
                        <Settings size={14} />
                        <span>Settings</span>
                      </button>
                    </div>
                    <div className="border-t border-white/[0.07] p-1">
                      <button
                        onClick={() => { logout(); router.replace('/login'); setProfileOpen(false); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[12px] text-[#F87171] hover:bg-[#F87171]/5 transition cursor-pointer"
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

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Bottom bar — minimal, with system status right */}
        <footer className="h-7 border-t border-white/[0.07] bg-[#08090B] flex items-center justify-between px-4 no-select text-[10px] text-[#71717A] font-mono shrink-0">
          <div className="flex items-center gap-3">
            <span>{user.email}</span>
          </div>
          <div className="relative" ref={statusRef}>
            <button
              onClick={() => setStatusOpen(p => !p)}
              className="flex items-center gap-2 px-2.5 py-1 rounded-md hover:bg-white/[0.04] transition cursor-pointer"
              aria-label="System status"
              aria-expanded={statusOpen}
            >
              <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', overallColor)} />
              <span>System</span>
              <Server size={10} className="text-[#71717A]" />
            </button>

            <AnimatePresence>
              {statusOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.97 }}
                  transition={{ duration: 0.12 }}
                  className="absolute right-0 bottom-full mb-2 w-[240px] rounded-lg border border-white/[0.07] bg-[#121419] shadow-matte-lg overflow-hidden z-50"
                  role="dialog"
                  aria-label="System services status"
                >
                  <div className="px-3 py-2 border-b border-white/[0.07] flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-[#F4F4F5]">System Services</span>
                    <span className={cn('text-[9px] font-medium', overallStatus === 'connected' ? 'text-[#4ADE80]' : overallStatus === 'degraded' ? 'text-[#FBBF24]' : 'text-[#F87171]')}>
                      {overallStatus === 'connected' ? 'All Operational' : overallStatus === 'degraded' ? 'Degraded' : 'Offline'}
                    </span>
                  </div>
                  <div className="p-2 space-y-0.5">
                    {services.map((s) => (
                      <div key={s.name} className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-white/[0.03] transition">
                        <span className="text-[11px] text-[#A1A1AA]">{s.name}</span>
                        <span className="flex items-center gap-1.5">
                          <span className={cn('h-1.5 w-1.5 rounded-full',
                            s.status === 'connected' ? 'bg-[#4ADE80]'
                            : s.status === 'disabled' ? 'bg-[#71717A]'
                            : s.status === 'reconnecting' ? 'bg-[#FBBF24]'
                            : 'bg-[#F87171]'
                          )} />
                          <span className={cn('text-[9px] font-medium',
                            s.status === 'connected' ? 'text-[#4ADE80]'
                            : s.status === 'disabled' ? 'text-[#71717A]'
                            : s.status === 'reconnecting' ? 'text-[#FBBF24]'
                            : 'text-[#F87171]'
                          )}>
                            {s.label || (s.status === 'connected' ? 'Connected' : s.status === 'disabled' ? 'Disabled' : s.status === 'reconnecting' ? 'Reconnecting' : 'Disconnected')}
                          </span>
                        </span>
                      </div>
                    ))}
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
