import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(started: string, completed?: string): string | null {
  if (!completed) return null;
  const ms = new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export function formatRelativeTime(d: string): string {
  const date = new Date(d);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return date.toLocaleDateString();
}

export function statusColor(s: string): string {
  const n = s.toLowerCase();
  if (n === 'completed') return 'text-[#4ADE80]';
  if (n === 'failed') return 'text-[#F87171]';
  if (n === 'executing' || n === 'running') return 'text-[#ADFF2F]';
  if (n === 'waiting' || n === 'planning') return 'text-[#7C3AED]';
  if (n === 'awaiting' || n === 'approval') return 'text-[#FBBF24]';
  if (n === 'retry') return 'text-[#FB923C]';
  if (n === 'queued') return 'text-[#71717A]';
  if (n === 'cancelled') return 'text-[#71717A]';
  return 'text-[#71717A]';
}

export function statusBg(s: string): string {
  const n = s.toLowerCase();
  if (n === 'completed') return 'bg-[#4ADE80]/10 border-[#4ADE80]/20';
  if (n === 'failed') return 'bg-[#F87171]/10 border-[#F87171]/20';
  if (n === 'executing' || n === 'running') return 'bg-[#ADFF2F]/10 border-[#ADFF2F]/20';
  if (n === 'waiting' || n === 'planning') return 'bg-[#7C3AED]/10 border-[#7C3AED]/20';
  if (n === 'awaiting' || n === 'approval') return 'bg-[#FBBF24]/10 border-[#FBBF24]/20';
  if (n === 'retry') return 'bg-[#FB923C]/10 border-[#FB923C]/20';
  if (n === 'queued') return 'bg-white/5 border-white/5';
  return 'bg-white/5 border-white/5';
}

export function statusDot(s: string): string {
  const n = s.toLowerCase();
  if (n === 'completed') return 'bg-[#4ADE80]';
  if (n === 'failed') return 'bg-[#F87171]';
  if (n === 'executing' || n === 'running') return 'bg-[#ADFF2F] animate-pulse-slow';
  if (n === 'waiting' || n === 'planning') return 'bg-[#7C3AED] animate-pulse-slow';
  if (n === 'awaiting' || n === 'approval') return 'bg-[#FBBF24] animate-pulse-slow';
  if (n === 'retry') return 'bg-[#FB923C] animate-pulse-slow';
  return 'bg-white/20';
}

export function agentIcon(agentType: string): string {
  switch (agentType) {
    case 'browser': return 'Globe';
    case 'terminal': return 'Terminal';
    case 'desktop': return 'Monitor';
    case 'file': return 'FileText';
    case 'vision': return 'Eye';
    default: return 'Cog';
  }
}
