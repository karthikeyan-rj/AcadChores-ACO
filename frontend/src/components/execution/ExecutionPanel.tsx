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
  const isFailed = stateMachineStatus === 'Failed';
  const isCompleted = stateMachineStatus === 'Completed';
  const AgentIcon = agentIcons[currentAgent] || Activity;
  const pct = totalSteps > 0 ? Math.round(((activeStepIndex + 1) / totalSteps) * 100) : 0;

  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!startTime || !isExecuting) return;
    const i = setInterval(() => setElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000);
    return () => clearInterval(i);
  }, [startTime, isExecuting]);

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
    <div className="rounded-[10px] border border-white/[0.07] bg-[#121419] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#71717A]">Execution</span>
        {isExecuting && (
          <span className="flex items-center gap-1.5 text-[10px] text-[#ADFF2F]">
            <Loader2 size={10} className="animate-spin" />
            Running
          </span>
        )}
        {isCompleted && (
          <span className="flex items-center gap-1.5 text-[10px] text-[#4ADE80]">
            <CheckCircle2 size={10} />
            Done
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-[#71717A]">
            Step {Math.max(0, activeStepIndex + 1)} of {totalSteps}
          </span>
          <span className="text-[#A1A1AA]">{pct}%</span>
        </div>
        <div className="h-1.5 bg-[#0D0F12] rounded-full overflow-hidden">
          <motion.div
            className={cn(
              'h-full rounded-full',
              isFailed ? 'bg-[#F87171]' : isExecuting ? 'bg-[#ADFF2F]' : 'bg-[#7C3AED]'
            )}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Current step info */}
      {currentStepName && (
        <div className="flex items-center gap-3 p-3 rounded-[10px] bg-[#0D0F12] border border-white/[0.07]">
          {isExecuting ? (
            <Loader2 size={14} className="text-[#ADFF2F] animate-spin shrink-0" />
          ) : isCompleted ? (
            <CheckCircle2 size={14} className="text-[#4ADE80] shrink-0" />
          ) : isFailed ? (
            <span className="h-3.5 w-3.5 rounded-full bg-[#F87171] flex items-center justify-center shrink-0"><span className="text-white text-[8px] font-bold">!</span></span>
          ) : (
            <AgentIcon size={14} className="text-[#71717A] shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-[11px] font-medium text-[#F4F4F5] truncate">{currentStepName}</p>
            <p className="text-[10px] text-[#71717A]">{currentAgent || '—'}</p>
          </div>
        </div>
      )}

      {/* Time stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded-[10px] bg-[#0D0F12] border border-white/[0.07]">
          <div className="flex items-center gap-1 mb-1">
            <Timer size={10} className="text-[#71717A]" />
            <span className="text-[9px] text-[#71717A]">Elapsed</span>
          </div>
          <p className="text-[11px] font-mono font-semibold text-[#F4F4F5]">{formatTime(elapsed)}</p>
        </div>
        <div className="p-2 rounded-[10px] bg-[#0D0F12] border border-white/[0.07]">
          <div className="flex items-center gap-1 mb-1">
            <Clock size={10} className="text-[#71717A]" />
            <span className="text-[9px] text-[#71717A]">ETA</span>
          </div>
          <p className="text-[11px] font-mono font-semibold text-[#F4F4F5]">{isExecuting && eta > 0 ? formatTime(eta) : '—'}</p>
        </div>
      </div>

      {/* Status indicators */}
      <div className="grid grid-cols-3 gap-2">
        <MiniStat
          icon={<Shield size={10} />}
          label="Verify"
          value={isCompleted ? 'Pass' : isExecuting ? 'Running' : '—'}
          ok={isCompleted || isExecuting}
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

      {/* Reply button */}
      {(isCompleted || isFailed) && onReply && (
        <button
          onClick={onReply}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-[10px] border border-[#7C3AED]/20 bg-[#7C3AED]/5 hover:bg-[#7C3AED]/10 text-[#7C3AED] text-[11px] font-semibold transition cursor-pointer"
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
    <div className="p-2 rounded-[10px] bg-[#0D0F12] border border-white/[0.07] text-center">
      <div className={cn('flex items-center justify-center mb-1', ok ? 'text-[#A1A1AA]' : 'text-[#F87171]')}>{icon}</div>
      <p className="text-[9px] text-[#71717A]">{label}</p>
      <p className={cn('text-[10px] font-semibold', ok ? 'text-[#F4F4F5]' : 'text-[#F87171]')}>{value}</p>
    </div>
  );
}
