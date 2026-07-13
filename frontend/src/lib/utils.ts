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
  const normalized = s.toLowerCase();
  if (normalized === 'completed') return 'text-accent';
  if (normalized === 'failed') return 'text-danger';
  if (normalized === 'executing' || normalized === 'running') return 'text-primary';
  if (normalized === 'waiting' || normalized === 'planning') return 'text-warning';
  if (normalized === 'retry') return 'text-orange-400';
  if (normalized === 'cancelled') return 'text-gray-500';
  return 'text-gray-500';
}

export function statusBg(s: string): string {
  const normalized = s.toLowerCase();
  if (normalized === 'completed') return 'bg-accent/10 border-accent/20';
  if (normalized === 'failed') return 'bg-danger/10 border-danger/20';
  if (normalized === 'executing' || normalized === 'running') return 'bg-primary/10 border-primary/20';
  if (normalized === 'waiting' || normalized === 'planning') return 'bg-warning/10 border-warning/20';
  if (normalized === 'retry') return 'bg-orange-400/10 border-orange-400/20';
  return 'bg-gray-500/10 border-gray-500/20';
}

export function statusDot(s: string): string {
  const normalized = s.toLowerCase();
  if (normalized === 'completed') return 'bg-accent';
  if (normalized === 'failed') return 'bg-danger';
  if (normalized === 'executing' || normalized === 'running') return 'bg-primary animate-pulse';
  if (normalized === 'waiting' || normalized === 'planning') return 'bg-warning animate-pulse';
  if (normalized === 'retry') return 'bg-orange-400 animate-pulse';
  return 'bg-gray-500';
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
