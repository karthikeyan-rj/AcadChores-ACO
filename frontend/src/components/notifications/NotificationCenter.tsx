'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell, X
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  time: string;
  read: boolean;
  icon?: React.ReactNode;
}

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const unread = notifications.filter(n => !n.read).length;

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const clearAll = () => {
    setNotifications([]);
  };

  const dismiss = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[90]"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="fixed right-4 top-12 z-[95] w-[380px] max-h-[500px] rounded-xl border border-theme-strong bg-surface overflow-hidden shadow-theme-dropdown"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-theme">
              <div className="flex items-center gap-2">
                <Bell size={14} className="text-theme" />
                <span className="text-xs font-semibold text-theme">Notifications</span>
                {unread > 0 && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-text-primary text-text-inverse font-bold">{unread}</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {notifications.length > 0 && (
                  <>
                    <button onClick={markAllRead} className="text-[10px] text-theme-tertiary hover:text-theme transition cursor-pointer px-2 py-1 rounded hover:bg-surface-hover">
                      Mark all read
                    </button>
                    <button onClick={clearAll} className="text-[10px] text-theme-tertiary hover:text-status-error transition cursor-pointer px-2 py-1 rounded hover:bg-surface-hover">
                      Clear all
                    </button>
                  </>
                )}
                <button onClick={onClose} className="p-1 rounded hover:bg-surface-hover text-theme-tertiary cursor-pointer">
                  <X size={13} />
                </button>
              </div>
            </div>
            <div className="overflow-y-auto max-h-[420px]">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-theme-tertiary">
                  <Bell size={24} className="text-theme-tertiary mb-2" />
                  <p className="text-xs font-medium">No notifications</p>
                  <p className="text-[10px] text-theme-tertiary mt-1">Notifications from workflow executions will appear here</p>
                </div>
              ) : (
                notifications.map((n, i) => (
                  <motion.div
                    key={n.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className={cn(
                      'flex items-start gap-3 px-4 py-3 border-b border-theme/50 hover:bg-surface-2 transition group',
                      !n.read && 'bg-surface-2'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-[11px] font-semibold text-theme truncate">{n.title}</p>
                        {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-text-primary shrink-0" />}
                      </div>
                      <p className="text-[10px] text-theme-secondary truncate">{n.message}</p>
                      <p className="text-[9px] text-theme-tertiary mt-0.5">{n.time}</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); dismiss(n.id); }}
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-surface-hover transition cursor-pointer"
                    >
                      <X size={11} className="text-theme-tertiary" />
                    </button>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const unread = notifications.filter(n => !n.read).length;

  const addNotification = (n: Omit<Notification, 'id' | 'time' | 'read'>) => {
    setNotifications(prev => [{
      ...n,
      id: Date.now().toString(),
      time: 'Just now',
      read: false,
    }, ...prev]);
  };

  return { notifications, unread, addNotification, setNotifications };
}
