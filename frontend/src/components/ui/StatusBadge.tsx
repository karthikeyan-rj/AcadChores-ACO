'use client';

import React from 'react';
import { cn, statusColor, statusBg, statusDot } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  className?: string;
}

export function StatusBadge({ status, size = 'sm', showDot = true, className }: StatusBadgeProps) {
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5',
  };

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wider',
      statusBg(status),
      statusColor(status),
      sizeClasses[size],
      className
    )}>
      {showDot && <span className={cn('h-1.5 w-1.5 rounded-full', statusDot(status))} />}
      {status}
    </span>
  );
}
