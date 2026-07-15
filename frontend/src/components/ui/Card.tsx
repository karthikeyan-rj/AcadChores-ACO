'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-[14px] border border-white/[0.07] bg-[#121419] p-5 shadow-matte shadow-inner-glow',
        hover && 'hover:bg-[#181B21] hover:border-white/[0.12] transition-all duration-150 cursor-pointer',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h3 className={cn('text-[10px] font-semibold uppercase tracking-wider text-[#71717A]', className)}>
      {children}
    </h3>
  );
}
