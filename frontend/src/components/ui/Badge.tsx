'use client';

import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-[#181B21] text-[#A1A1AA] border border-white/[0.07]',
  success: 'bg-[#4ADE80]/10 text-[#4ADE80] border border-[#4ADE80]/20',
  warning: 'bg-[#FBBF24]/10 text-[#FBBF24] border border-[#FBBF24]/20',
  danger: 'bg-[#F87171]/10 text-[#F87171] border border-[#F87171]/20',
  info: 'bg-[#7C3AED]/10 text-[#7C3AED] border border-[#7C3AED]/20',
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
    healthy: 'bg-[#4ADE80]',
    degraded: 'bg-[#FBBF24]',
    down: 'bg-[#F87171]',
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
        <h1 className="text-xl font-bold text-[#F4F4F5]">{title}</h1>
        {description && <p className="text-xs text-[#71717A] mt-1">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }: {
  icon: any; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-[#71717A]">
      <Icon size={32} className="text-[#3F3F46] mb-3" />
      <p className="text-sm font-medium">{title}</p>
      <p className="text-xs text-[#3F3F46] mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}
