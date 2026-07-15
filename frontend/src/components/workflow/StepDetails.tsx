'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, Globe, Terminal, Monitor, FileText, Eye, Shield, RefreshCw, Hash, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskStep {
  step_id: string;
  name: string;
  agent_type: string;
  action: string;
}

interface StepDetailsProps {
  step: TaskStep | null;
  index: number;
  status: string;
  onClose: () => void;
}

const agentIcons: Record<string, React.ComponentType<any>> = {
  browser: Globe, terminal: Terminal, desktop: Monitor, file: FileText, vision: Eye,
};

export function StepDetails({ step, index, status, onClose }: StepDetailsProps) {
  if (!step) return null;

  const AgentIcon = agentIcons[step.agent_type] || Settings;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        className="rounded-[10px] border border-white/[0.07] bg-[#121419] overflow-hidden"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.07]">
          <div className="flex items-center gap-2">
            <AgentIcon size={14} className="text-[#7C3AED]" />
            <span className="text-xs font-semibold text-[#F4F4F5]">Step {index + 1} Details</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-white/5 transition cursor-pointer text-[#71717A] hover:text-[#F4F4F5]">
            <X size={14} />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <DetailRow icon={<Hash size={12} />} label="Name" value={step.name} />
          <DetailRow icon={<Settings size={12} />} label="Agent" value={step.agent_type} />
          <DetailRow icon={<Clock size={12} />} label="Action" value={step.action} />
          <DetailRow icon={<Shield size={12} />} label="Status" value={status} />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

function DetailRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-1.5 text-[11px] text-[#71717A]">
        {icon} {label}
      </span>
      <span className="text-[11px] text-[#F4F4F5] font-medium">{value}</span>
    </div>
  );
}
