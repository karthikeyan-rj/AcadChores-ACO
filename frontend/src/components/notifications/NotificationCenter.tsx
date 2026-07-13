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
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="fixed right-4 top-12 z-[95] w-[380px] max-h-[500px] rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Bell size={14} className="text-primary" />
                <span className="text-xs font-semibold">Notifications</span>
                {unread > 0 && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary text-white font-bold">{unread}</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {notifications.length > 0 && (
                  <>
                    <button onClick={markAllRead} className="text-[10px] text-gray-500 hover:text-foreground transition cursor-pointer px-2 py-1 rounded hover:bg-surface-2">
                      Mark all read
                    </button>
                    <button onClick={clearAll} className="text-[10px] text-gray-500 hover:text-danger transition cursor-pointer px-2 py-1 rounded hover:bg-surface-2">
                      Clear all
                    </button>
                  </>
                )}
                <button onClick={onClose} className="p-1 rounded hover:bg-surface-2 text-gray-500 cursor-pointer">
                  <X size={13} />
                </button>
              </div>
            </div>
            <div className="overflow-y-auto max-h-[420px]">
              {notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <Bell size={24} className="text-gray-600 mb-2" />
                  <p className="text-xs font-medium">No notifications</p>
                  <p className="text-[10px] text-gray-600 mt-1">Notifications from workflow executions will appear here</p>
                </div>
              ) : (
                notifications.map((n, i) => (
                  <motion.div
                    key={n.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className={cn(
                      'flex items-start gap-3 px-4 py-3 border-b border-border/50 hover:bg-surface-2 transition group',
                      !n.read && 'bg-primary/5'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-[11px] font-semibold truncate">{n.title}</p>
                        {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />}
                      </div>
                      <p className="text-[10px] text-gray-500 truncate">{n.message}</p>
                      <p className="text-[9px] text-gray-600 mt-0.5">{n.time}</p>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); dismiss(n.id); }}
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-surface-2 transition cursor-pointer"
                    >
                      <X size={11} className="text-gray-500" />
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
