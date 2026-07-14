'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Globe, Terminal, Monitor, FileText, Eye,
  CheckCircle2, Loader2, RefreshCw, Shield, Clock, Cpu,
  Gauge, RotateCcw, Zap, Timer, TrendingUp, Reply
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExecutionPanelProps {
  stateMachineStatus: string;
  activeStepIndex: number;
  totalSteps: number;
  currentStepName: string;
  currentAgent: string;
  progress: number;
  startTime?: number | null;
  onReply?: () => void;
}

const agentIcons: Record<string, React.ComponentType<any>> = {
  browser: Globe, terminal: Terminal, desktop: Monitor, file: FileText, vision: Eye,
};

export function ExecutionPanel({ stateMachineStatus, activeStepIndex, totalSteps, currentStepName, currentAgent, progress, startTime, onReply }: ExecutionPanelProps) {
  const isExecuting = stateMachineStatus === 'Executing';
  const AgentIcon = agentIcons[currentAgent] || Activity;
  const pct = totalSteps > 0 ? Math.round(((activeStepIndex + 1) / totalSteps) * 100) : 0;

  // Elapsed time
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!startTime || !isExecuting) return;
    const i = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000);
    return () => clearInterval(i);
  }, [startTime, isExecuting]);

  // ETA (simple estimation)
  const eta = activeStepIndex > 0 && totalSteps > 0
    ? Math.round((elapsed / activeStepIndex) * (totalSteps - activeStepIndex))
    : 0;

  const formatTime = (s: number) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  const retries = 0;
  const confidence = 0;

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Execution</span>
        {isExecuting && (
          <span className="flex items-center gap-1.5 text-[10px] text-primary">
            <Loader2 size={10} className="animate-spin" />
            Running
          </span>
        )}
        {!isExecuting && stateMachineStatus === 'Completed' && (
          <span className="flex items-center gap-1.5 text-[10px] text-accent">
            <CheckCircle2 size={10} />
            Done
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-500">
            Step {Math.max(0, activeStepIndex + 1)} of {totalSteps}
          </span>
          <span className="text-gray-400">{pct}%</span>
        </div>
        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
          <motion.div
            className={cn('h-full rounded-full', stateMachineStatus === 'Failed' ? 'bg-danger' : 'bg-primary')}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Current step info */}
      {currentStepName && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-surface border border-border">
          {isExecuting ? (
            <Loader2 size={14} className="text-primary animate-spin shrink-0" />
          ) : stateMachineStatus === 'Completed' ? (
            <CheckCircle2 size={14} className="text-accent shrink-0" />
          ) : stateMachineStatus === 'Failed' ? (
            <span className="h-3.5 w-3.5 rounded-full bg-danger flex items-center justify-center shrink-0"><span className="text-white text-[8px] font-bold">!</span></span>
          ) : (
            <AgentIcon size={14} className="text-gray-500 shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-[11px] font-medium text-foreground truncate">{currentStepName}</p>
            <p className="text-[10px] text-gray-500">{currentAgent || '—'}</p>
          </div>
        </div>
      )}

      {/* Time stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded-lg bg-surface border border-border">
          <div className="flex items-center gap-1 mb-1">
            <Timer size={10} className="text-gray-500" />
            <span className="text-[9px] text-gray-500">Elapsed</span>
          </div>
          <p className="text-[11px] font-mono font-semibold">{formatTime(elapsed)}</p>
        </div>
        <div className="p-2 rounded-lg bg-surface border border-border">
          <div className="flex items-center gap-1 mb-1">
            <Clock size={10} className="text-gray-500" />
            <span className="text-[9px] text-gray-500">ETA</span>
          </div>
          <p className="text-[11px] font-mono font-semibold">{isExecuting && eta > 0 ? formatTime(eta) : '—'}</p>
        </div>
      </div>

      {/* Status indicators */}
      <div className="grid grid-cols-3 gap-2">
        <MiniStat
          icon={<Shield size={10} />}
          label="Verify"
          value={stateMachineStatus === 'Completed' ? 'Pass' : isExecuting ? 'Running' : '—'}
          ok={stateMachineStatus === 'Completed' || isExecuting}
        />
        <MiniStat
          icon={<RefreshCw size={10} />}
          label="Recovery"
          value={retries > 0 ? `${retries} retries` : 'None'}
          ok={retries === 0}
        />
        <MiniStat
          icon={<TrendingUp size={10} />}
          label="Confidence"
          value={confidence > 0 ? `${confidence}%` : '—'}
          ok={confidence >= 80}
        />
      </div>

      {/* Resource indicators */}
      <div className="grid grid-cols-3 gap-2">
        <MiniStat icon={<Cpu size={10} />} label="CPU" value="—" ok />
        <MiniStat icon={<Gauge size={10} />} label="RAM" value="—" ok />
        <MiniStat icon={<Zap size={10} />} label="Agent" value={currentAgent || '—'} ok />
      </div>

      {/* Reply button — visible when workflow completed or failed */}
      {(stateMachineStatus === 'Completed' || stateMachineStatus === 'Failed') && onReply && (
        <button
          onClick={onReply}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 text-primary text-[11px] font-semibold transition cursor-pointer"
        >
          <Reply size={13} />
          Reply with same prompt
        </button>
      )}
    </div>
  );
}

function MiniStat({ icon, label, value, ok }: { icon: React.ReactNode; label: string; value: string; ok: boolean }) {
  return (
    <div className="p-2 rounded-lg bg-surface border border-border text-center">
      <div className={cn('flex items-center justify-center mb-1', ok ? 'text-gray-400' : 'text-danger')}>{icon}</div>
      <p className="text-[9px] text-gray-500">{label}</p>
      <p className={cn('text-[10px] font-semibold', ok ? 'text-foreground' : 'text-danger')}>{value}</p>
    </div>
  );
}
