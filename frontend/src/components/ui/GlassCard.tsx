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
        'rounded-[14px] border border-white/[0.07] bg-[#121419] shadow-matte shadow-inner-glow',
        hover && 'transition-all duration-200 hover:bg-[#181B21] hover:border-white/[0.12] cursor-pointer',
        active && 'border-[#7C3AED]/40 bg-[#7C3AED]/5',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
