'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Loader2, Clock } from 'lucide-react';
import { cn, formatRelativeTime, formatDuration, statusColor } from '@/lib/utils';

interface ExecutionRecord {
  _id: string;
  workflow_id: string;
  title: string;
  description: string;
  status: string;
  current_step_index: number;
  total_steps: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  result?: string;
}

interface ExecutionHistoryProps {
  history: ExecutionRecord[];
  loading: boolean;
  activeExecutionId: string | null;
  onSelect: (record: ExecutionRecord) => void;
}

export function ExecutionHistory({ history, loading, activeExecutionId, onSelect }: ExecutionHistoryProps) {
  return (
    <div className="space-y-1">
      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 size={16} className="text-gray-500 animate-spin" />
        </div>
      ) : history.length === 0 ? (
        <p className="text-[10px] text-gray-600 text-center py-6">No execution history</p>
      ) : (
        history.slice(0, 20).map((ex, i) => (
          <motion.button
            key={ex._id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.02 }}
            onClick={() => onSelect(ex)}
            className={cn(
              'w-full text-left p-2.5 rounded-lg border transition-all duration-150 cursor-pointer',
              activeExecutionId === ex._id
                ? 'bg-primary/5 border-primary/30'
                : 'bg-transparent border-transparent hover:bg-surface-2 hover:border-border'
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span className={cn('font-semibold uppercase text-[9px]', statusColor(ex.status))}>
                {ex.status}
              </span>
              <div className="flex items-center gap-1.5">
                {ex.completed_at && (
                  <span className="text-[9px] text-accent font-mono">
                    {formatDuration(ex.started_at, ex.completed_at)}
                  </span>
                )}
                <span className="text-[9px] text-gray-600">
                  {formatRelativeTime(ex.started_at)}
                </span>
              </div>
            </div>
            <p className="text-[10px] text-gray-400 truncate">
              {ex.description || ex.title || `Execution ${ex._id.slice(-6)}`}
            </p>
          </motion.button>
        ))
      )}
    </div>
  );
}
