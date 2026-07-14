'use client';

import React from 'react';
import {
  Database, Wifi, Globe, Cpu, HardDrive, MonitorPlay,
  Activity, Layers
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatusBarProps {
  backendConnected: boolean;
  wsConnected: boolean;
  stateMachineStatus: string;
  activeStepIndex: number;
  totalSteps: number;
}

export function StatusBar({ backendConnected, wsConnected, stateMachineStatus, activeStepIndex, totalSteps }: StatusBarProps) {
  return (
    <footer className="h-6 border-t border-border bg-card flex items-center justify-between px-4 no-select text-[10px] text-gray-500 shrink-0">
      <div className="flex items-center gap-3">
        <StatusPill icon={<Database size={10} />} label="Mongo" active={backendConnected} />
        <StatusPill icon={<Wifi size={10} />} label="Redis" active={backendConnected} />
        <StatusPill icon={<Globe size={10} />} label="Browser" active={backendConnected} />
        <StatusPill icon={<Layers size={10} />} label="Workers" active={backendConnected} />
      </div>
      <div className="flex items-center gap-4">
        {activeStepIndex >= 0 && totalSteps > 0 && (
          <span className="text-primary">
            Step {activeStepIndex + 1}/{totalSteps}
          </span>
        )}
        <span className="text-gray-600">Host: Windows Native</span>
        <span className="flex items-center gap-1">
          <span className={cn('h-1 w-1 rounded-full', stateMachineStatus === 'Completed' ? 'bg-accent' : stateMachineStatus === 'Failed' ? 'bg-danger' : stateMachineStatus === 'Executing' ? 'bg-primary animate-pulse' : 'bg-gray-600')} />
          {stateMachineStatus}
        </span>
      </div>
    </footer>
  );
}

function StatusPill({ icon, label, active }: { icon: React.ReactNode; label: string; active: boolean }) {
  return (
    <span className="flex items-center gap-1" title={label}>
      <span className={cn(active ? 'text-accent' : 'text-gray-600')}>{icon}</span>
      <span className={active ? 'text-gray-400' : 'text-gray-600'}>{label}</span>
    </span>
  );
}
