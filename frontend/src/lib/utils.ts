import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(started: string, completed?: string): string | null {
  if (!completed) return null;
  const ms = new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 0) return null;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.floor((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export function formatRelativeTime(d: string): string {
  if (!d) return 'Unknown time';
  const date = new Date(d);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return date.toLocaleDateString();
}

export function formatLocalDateTime(value: string): string {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function statusColor(s: string): string {
  const n = (s || '').toLowerCase();
  if (n === 'completed') return 'text-status-active';
  if (n === 'stopped' || n === 'cancelled') return 'text-theme-secondary';
  if (n === 'failed') return 'text-status-error';
  if (n === 'draft') return 'text-status-warning';
  if (n === 'executing' || n === 'running') return 'text-status-active';
  if (n === 'waiting' || n === 'planning') return 'text-theme-secondary';
  if (n === 'stopping') return 'text-status-warning';
  if (n === 'awaiting' || n === 'approval') return 'text-status-warning';
  if (n === 'retry') return 'text-status-warning';
  if (n === 'queued') return 'text-theme-tertiary';
  return 'text-theme-tertiary';
}

export function statusBg(s: string): string {
  const n = (s || '').toLowerCase();
  if (n === 'completed') return 'bg-status-active-soft border-status-active';
  if (n === 'stopped' || n === 'cancelled') return 'bg-surface-2 border-theme';
  if (n === 'failed') return 'bg-status-error-soft border-status-error';
  if (n === 'draft') return 'bg-status-warning-soft border-status-warning';
  if (n === 'executing' || n === 'running') return 'bg-status-active-soft border-status-active';
  if (n === 'waiting' || n === 'planning') return 'bg-surface-2 border-theme';
  if (n === 'stopping') return 'bg-status-warning-soft border-status-warning';
  if (n === 'awaiting' || n === 'approval') return 'bg-status-warning-soft border-status-warning';
  if (n === 'retry') return 'bg-status-warning-soft border-status-warning';
  if (n === 'queued') return 'bg-surface-2 border-theme';
  return 'bg-surface-2 border-theme';
}

export function statusDot(s: string): string {
  const n = (s || '').toLowerCase();
  if (n === 'completed') return 'bg-status-active';
  if (n === 'stopped' || n === 'cancelled') return 'bg-text-secondary';
  if (n === 'failed') return 'bg-status-error';
  if (n === 'draft') return 'bg-status-warning';
  if (n === 'executing' || n === 'running') return 'bg-status-active animate-pulse-slow';
  if (n === 'waiting' || n === 'planning') return 'bg-text-secondary animate-pulse-slow';
  if (n === 'stopping') return 'bg-status-warning animate-pulse-slow';
  if (n === 'awaiting' || n === 'approval') return 'bg-status-warning animate-pulse-slow';
  if (n === 'retry') return 'bg-status-warning animate-pulse-slow';
  return 'bg-border';
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
