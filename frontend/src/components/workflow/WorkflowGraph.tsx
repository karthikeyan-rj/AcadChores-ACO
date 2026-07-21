'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Globe, Terminal, Monitor, FileText, Eye, Cog, CheckCircle2,
  XCircle, Loader2, Clock, AlertTriangle, PlayCircle, Shield, RotateCcw
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskStep {
  step_id: string;
  name: string;
  agent_type: string;
  action: string;
}

interface WorkflowGraphProps {
  steps: TaskStep[];
  activeStepIndex: number;
  onStepClick: (index: number) => void;
  selectedStepIndex: number | null;
  onStepReplay?: (step: TaskStep) => void;
}

const agentConfig: Record<string, { icon: React.ComponentType<any>; color: string; label: string }> = {
  browser: { icon: Globe, color: 'text-status-info', label: 'Browser' },
  terminal: { icon: Terminal, color: 'text-status-active', label: 'Terminal' },
  desktop: { icon: Monitor, color: 'text-theme-secondary', label: 'Desktop' },
  file: { icon: FileText, color: 'text-status-warning', label: 'File' },
  vision: { icon: Eye, color: 'text-status-info', label: 'Vision' },
};

function getStepStatus(idx: number, activeStepIndex: number): 'completed' | 'running' | 'failed' | 'pending' {
  if (activeStepIndex === -1) return 'pending';
  if (idx < activeStepIndex) return 'completed';
  if (idx === activeStepIndex) return 'running';
  return 'pending';
}

export function WorkflowGraph({ steps, activeStepIndex, onStepClick, selectedStepIndex, onStepReplay }: WorkflowGraphProps) {
  if (steps.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-theme-tertiary px-1">Workflow Plan</h3>
      <div className="relative">
        <div className="absolute left-[19px] top-0 bottom-0 w-px bg-theme" />

        <AnimatePresence mode="wait">
          {steps.map((step, idx) => {
            const status = getStepStatus(idx, activeStepIndex);
            const config = agentConfig[step.agent_type] || agentConfig.browser;
            const AgentIcon = config.icon;
            const isSelected = selectedStepIndex === idx;

            return (
              <motion.div
                key={step.step_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
                onClick={() => onStepClick(idx)}
                className={cn(
                  'relative flex items-center gap-3 pl-0 pr-3 py-1.5 cursor-pointer group',
                  isSelected && 'z-10'
                )}
              >
                <div className={cn(
                  'relative z-10 w-[38px] h-[38px] rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-300',
                  status === 'completed' && 'bg-status-active-soft border-status-active/50',
                  status === 'running' && 'bg-surface-2 border-text-primary/50 animate-pulse',
                  status === 'failed' && 'bg-status-error-soft border-status-error/50',
                  status === 'pending' && 'bg-surface border-theme',
                  isSelected && 'ring-2 ring-text-primary/20 ring-offset-2 ring-offset-surface'
                )}>
                  {status === 'completed' ? (
                    <CheckCircle2 size={16} className="text-status-active" />
                  ) : status === 'running' ? (
                    <Loader2 size={16} className="text-text-primary animate-spin" />
                  ) : status === 'failed' ? (
                    <XCircle size={16} className="text-status-error" />
                  ) : (
                    <AgentIcon size={14} className={cn(config.color, 'opacity-50')} />
                  )}
                </div>

                <div className={cn(
                  'flex-1 rounded-xl border p-3 transition-all duration-200',
                  isSelected ? 'bg-surface-2 border-theme-strong' : 'bg-surface border-theme group-hover:border-theme-strong'
                )}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-theme truncate pr-2">{step.name}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {onStepReplay && (status === 'completed' || status === 'failed') && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onStepReplay(step); }}
                          className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-surface-hover text-theme-tertiary hover:text-theme transition-all cursor-pointer"
                          title="Replay this step"
                        >
                          <RotateCcw size={12} />
                        </button>
                      )}
                      <span className={cn(
                        'text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase',
                        status === 'completed' && 'bg-status-active-soft text-status-active',
                        status === 'running' && 'bg-surface-2 text-text-primary',
                        status === 'failed' && 'bg-status-error-soft text-status-error',
                        status === 'pending' && 'bg-surface-2 text-theme-tertiary'
                      )}>
                        {config.label}
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-theme-secondary">
                    {step.action}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
