'use client';

import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogMessage {
  time: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

interface LiveConsoleProps {
  logs: LogMessage[];
  wsConnected: boolean;
}

export function LiveConsole({ logs, wsConnected }: LiveConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full rounded-xl border border-border bg-surface overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2">
          <Terminal size={13} className="text-primary" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Console</span>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="flex items-center gap-1.5 text-[10px] text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              Live
            </span>
          )}
          <span className="text-[10px] text-gray-600">{logs.length} entries</span>
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-1">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-600 gap-2">
            <Terminal size={24} className="text-gray-700" />
            <p className="text-[11px]">Console waiting for workflow logs...</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
                className={cn(
                  'flex gap-2 leading-relaxed',
                  log.level === 'error' ? 'text-danger' :
                  log.level === 'warn' ? 'text-warning' : 'text-gray-400'
                )}
              >
                <span className="text-gray-600 shrink-0 w-16">{log.time}</span>
                <span className="break-all leading-relaxed">{log.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
