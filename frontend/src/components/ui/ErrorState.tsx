'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, RefreshCw, ArrowLeft, Wifi, WifiOff } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onBack?: () => void;
  variant?: 'error' | 'offline' | 'not-found';
  className?: string;
}

const variants = {
  error: {
    icon: AlertTriangle,
    title: 'Something went wrong',
    message: 'An unexpected error occurred. Please try again.',
    iconClass: 'text-[#F87171]',
    bgClass: 'bg-[#F87171]/5 border-[#F87171]/20',
  },
  offline: {
    icon: WifiOff,
    title: 'Connection lost',
    message: 'Unable to reach the backend server. Check your connection.',
    iconClass: 'text-[#FBBF24]',
    bgClass: 'bg-[#FBBF24]/5 border-[#FBBF24]/20',
  },
  'not-found': {
    icon: AlertTriangle,
    title: 'Not found',
    message: 'The resource you are looking for does not exist.',
    iconClass: 'text-[#71717A]',
    bgClass: 'bg-[#181B21] border-white/[0.07]',
  },
};

export function ErrorState({ title, message, onRetry, onBack, variant = 'error', className }: ErrorStateProps) {
  const v = variants[variant];
  const Icon = v.icon;

  return (
    <div className={cn('flex flex-col items-center justify-center py-16', className)}>
      <div className={cn('w-14 h-14 rounded-[14px] border flex items-center justify-center mb-4', v.bgClass)}>
        <Icon size={24} className={v.iconClass} />
      </div>
      <h3 className="text-sm font-semibold mb-1">{title || v.title}</h3>
      <p className="text-xs text-[#71717A] mb-4 text-center max-w-[300px]">{message || v.message}</p>
      <div className="flex gap-2">
        {onBack && (
          <button onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#A1A1AA] hover:text-[#F4F4F5] bg-[#181B21] border border-white/[0.07] rounded-[10px] transition cursor-pointer">
            <ArrowLeft size={12} />Go Back
          </button>
        )}
        {onRetry && (
          <button onClick={onRetry}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-[#7C3AED] hover:bg-[#6D28D9] text-white rounded-[10px] transition cursor-pointer shadow-matte">
            <RefreshCw size={12} />Retry
          </button>
        )}
      </div>
    </div>
  );
}
