'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  active?: boolean;
  glow?: 'primary' | 'accent' | 'danger' | 'none';
}

export function GlassCard({ children, className, hover = false, active = false, glow = 'none', ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card/80 backdrop-blur-sm',
        hover && 'transition-all duration-200 hover:bg-card-hover hover:border-border-light cursor-pointer',
        active && 'border-primary/40 bg-primary/5',
        glow === 'primary' && 'glow-primary',
        glow === 'accent' && 'glow-accent',
        glow === 'danger' && 'glow-danger',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
