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
    <div className="rounded-[10px] border border-white/[0.07] bg-[#121419] overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/[0.07]">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#71717A]">Timeline</span>
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
                    <XCircle size={12} className="text-[#F87171]" />
                  ) : isWarn ? (
                    <Clock size={12} className="text-[#FBBF24]" />
                  ) : (
                    <CheckCircle2 size={12} className="text-[#71717A]" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={cn(
                    'text-[10px] leading-relaxed',
                    isError ? 'text-[#F87171]' : isWarn ? 'text-[#FBBF24]' : 'text-[#A1A1AA]'
                  )}>
                    {log.message}
                  </p>
                  <p className="text-[9px] font-mono text-[#71717A]">{log.time}</p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
