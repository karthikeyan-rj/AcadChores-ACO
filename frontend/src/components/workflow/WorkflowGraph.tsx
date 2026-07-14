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
  browser: { icon: Globe, color: 'text-blue-400', label: 'Browser' },
  terminal: { icon: Terminal, color: 'text-green-400', label: 'Terminal' },
  desktop: { icon: Monitor, color: 'text-purple-400', label: 'Desktop' },
  file: { icon: FileText, color: 'text-amber-400', label: 'File' },
  vision: { icon: Eye, color: 'text-cyan-400', label: 'Vision' },
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
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 px-1">Workflow Plan</h3>
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-[19px] top-0 bottom-0 w-px bg-border" />

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
                {/* Node circle */}
                <div className={cn(
                  'relative z-10 w-[38px] h-[38px] rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-300',
                  status === 'completed' && 'bg-accent/10 border-accent/50',
                  status === 'running' && 'bg-primary/10 border-primary animate-pulse',
                  status === 'failed' && 'bg-danger/10 border-danger/50',
                  status === 'pending' && 'bg-surface border-border',
                  isSelected && 'ring-2 ring-primary/30 ring-offset-2 ring-offset-background'
                )}>
                  {status === 'completed' ? (
                    <CheckCircle2 size={16} className="text-accent" />
                  ) : status === 'running' ? (
                    <Loader2 size={16} className="text-primary animate-spin" />
                  ) : status === 'failed' ? (
                    <XCircle size={16} className="text-danger" />
                  ) : (
                    <AgentIcon size={14} className={cn(config.color, 'opacity-50')} />
                  )}
                </div>

                {/* Content card */}
                <div className={cn(
                  'flex-1 rounded-xl border p-3 transition-all duration-200',
                  isSelected ? 'bg-primary/5 border-primary/30' : 'bg-card border-border group-hover:border-border-light group-hover:bg-card-hover'
                )}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-foreground truncate pr-2">{step.name}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {onStepReplay && (status === 'completed' || status === 'failed') && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onStepReplay(step); }}
                          className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-primary/10 text-gray-500 hover:text-primary transition-all cursor-pointer"
                          title="Replay this step"
                        >
                          <RotateCcw size={12} />
                        </button>
                      )}
                      <span className={cn(
                        'text-[9px] px-1.5 py-0.5 rounded font-bold uppercase',
                        status === 'completed' && 'bg-accent/10 text-accent',
                        status === 'running' && 'bg-primary/10 text-primary',
                        status === 'failed' && 'bg-danger/10 text-danger',
                        status === 'pending' && 'bg-surface-2 text-gray-500'
                      )}>
                        {config.label}
                      </span>
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-500">
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
