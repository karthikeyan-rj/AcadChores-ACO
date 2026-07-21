'use client';

import React, { useRef, useEffect } from 'react';
import { Terminal } from 'lucide-react';
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
    <div className="flex flex-col h-full rounded-xl border border-theme bg-surface overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-theme bg-surface-2 shrink-0">
        <div className="flex items-center gap-2">
          <Terminal size={13} className="text-theme-secondary" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-theme-tertiary">Console</span>
        </div>
        <div className="flex items-center gap-2">
          {wsConnected && (
            <span className="flex items-center gap-1.5 text-[10px] text-status-active">
              <span className="h-1.5 w-1.5 rounded-full bg-status-active animate-pulse" />
              Live
            </span>
          )}
          <span className="text-[10px] text-theme-tertiary">{logs.length} entries</span>
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-1">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-theme-tertiary gap-2">
            <Terminal size={24} className="text-border-strong" />
            <p className="text-[11px]">Console waiting for workflow logs...</p>
          </div>
        ) : (
          logs.map((log, i) => (
            <div
              key={i}
              className={cn(
                'flex gap-2 leading-relaxed animate-[fadeIn_0.15s_ease-out]',
                log.level === 'error' ? 'text-status-error' :
                log.level === 'warn' ? 'text-status-warning' : 'text-theme-secondary'
              )}
            >
              <span className="text-theme-tertiary shrink-0 w-16">{log.time}</span>
              <span className="break-all leading-relaxed">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
