'use client';

import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface-3 text-gray-400 border border-border',
  success: 'bg-accent/10 text-accent border border-accent/20',
  warning: 'bg-warning/10 text-warning border border-warning/20',
  danger: 'bg-danger/10 text-danger border border-danger/20',
  info: 'bg-primary/10 text-primary border border-primary/20',
};

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'default', children, className }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wide',
      variantStyles[variant],
      className
    )}>
      {children}
    </span>
  );
}

export function StatusDot({ status, size = 'sm' }: { status: 'healthy' | 'degraded' | 'down'; size?: 'sm' | 'md' }) {
  const colors = {
    healthy: 'bg-accent',
    degraded: 'bg-warning',
    down: 'bg-danger',
  };
  const sizes = {
    sm: 'h-1.5 w-1.5',
    md: 'h-2 w-2',
  };
  return <span className={cn('rounded-full', colors[status], sizes[size])} />;
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h1 className="text-xl font-bold text-foreground">{title}</h1>
        {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }: {
  icon: any; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      <Icon size={32} className="text-gray-600 mb-3" />
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs text-gray-600 mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}
