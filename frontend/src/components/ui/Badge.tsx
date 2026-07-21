'use client';

import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-2 text-theme-secondary border-theme',
  success: 'bg-status-active-soft text-status-active border-status-active',
  warning: 'bg-status-warning-soft text-status-warning border-status-warning',
  danger: 'bg-status-error-soft text-status-error border-status-error',
  info: 'bg-status-info-soft text-status-info border-status-info',
};

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'default', children, className }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wide border',
      variantStyles[variant],
      className
    )}>
      {children}
    </span>
  );
}

export function StatusDot({ status, size = 'sm' }: { status: 'healthy' | 'degraded' | 'down'; size?: 'sm' | 'md' }) {
  const colors = {
    healthy: 'bg-status-active',
    degraded: 'bg-status-warning',
    down: 'bg-status-error',
  };
  const sizes = { sm: 'h-1.5 w-1.5', md: 'h-2 w-2' };
  return <span className={cn('rounded-full', colors[status], sizes[size])} />;
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-theme tracking-tight">{title}</h1>
        {description && <p className="text-[13px] text-theme-secondary mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }: {
  icon: any; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-theme-tertiary">
      <Icon size={28} className="text-border-strong mb-3" />
      <p className="text-[13px] font-medium text-theme-secondary">{title}</p>
      <p className="text-[12px] text-theme-tertiary mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}
