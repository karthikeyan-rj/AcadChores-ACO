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
    <div className="flex flex-col h-full rounded-[10px] border border-white/[0.07] bg-[#08090B] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.07] bg-[#121419] shrink-0">
        <div className="flex items-center gap-2">
          <Terminal size={13} className="text-[#7C3AED]" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#A1A1AA]">Console</span>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="flex items-center gap-1.5 text-[10px] text-[#ADFF2F]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#ADFF2F] animate-pulse" />
              Live
            </span>
          )}
          <span className="text-[10px] text-[#71717A]">{logs.length} entries</span>
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-1">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-[#71717A] gap-2">
            <Terminal size={24} className="text-[#71717A]/50" />
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
                  log.level === 'error' ? 'text-[#F87171]' :
                  log.level === 'warn' ? 'text-[#FBBF24]' : 'text-[#A1A1AA]'
                )}
              >
                <span className="text-[#71717A] shrink-0 w-16">{log.time}</span>
                <span className="break-all leading-relaxed">{log.message}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
