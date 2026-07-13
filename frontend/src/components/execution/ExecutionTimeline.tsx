'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2, XCircle, Clock, ChevronRight } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration } from '@/lib/utils';

interface LogMessage {
  time: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

interface ExecutionTimelineProps {
  logs: LogMessage[];
  stateMachineStatus: string;
}

export function ExecutionTimeline({ logs, stateMachineStatus }: ExecutionTimelineProps) {
  if (logs.length === 0 && stateMachineStatus === 'Idle') return null;

  return (
    <div className="rounded-xl border border-border bg-card/80 backdrop-blur-sm overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Timeline</span>
      </div>
      <div className="p-3 max-h-60 overflow-y-auto space-y-1">
        <AnimatePresence initial={false}>
          {logs.map((log, i) => {
            const isError = log.level === 'error';
            const isWarn = log.level === 'warn';
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="flex items-start gap-2 py-1.5"
              >
                <div className="mt-0.5 shrink-0">
                  {isError ? (
                    <XCircle size={12} className="text-danger" />
                  ) : isWarn ? (
                    <Clock size={12} className="text-warning" />
                  ) : (
                    <CheckCircle2 size={12} className="text-gray-600" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={cn(
                    'text-[10px] leading-relaxed',
                    isError ? 'text-danger' : isWarn ? 'text-warning' : 'text-gray-400'
                  )}>
                    {log.message}
                  </p>
                  <p className="text-[9px] text-gray-600">{log.time}</p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
