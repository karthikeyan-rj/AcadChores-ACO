'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, RefreshCw, ArrowLeft, WifiOff } from 'lucide-react';

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
    iconClass: 'text-[#A23B3B]',
    bgClass: 'bg-[#F8EAEA] border-[#EBCACA]',
  },
  offline: {
    icon: WifiOff,
    title: 'Connection lost',
    message: 'Unable to reach the backend server. Check your connection.',
    iconClass: 'text-[#9A6A13]',
    bgClass: 'bg-[#F7F0E2] border-[#E8D8B9]',
  },
  'not-found': {
    icon: AlertTriangle,
    title: 'Not found',
    message: 'The resource you are looking for does not exist.',
    iconClass: 'text-[#989890]',
    bgClass: 'bg-[#F4F4F0] border-[#E5E5E0]',
  },
};

export function ErrorState({ title, message, onRetry, onBack, variant = 'error', className }: ErrorStateProps) {
  const v = variants[variant];
  const Icon = v.icon;

  return (
    <div className={cn('flex flex-col items-center justify-center py-16', className)}>
      <div className={cn('w-14 h-14 rounded-xl border flex items-center justify-center mb-4', v.bgClass)}>
        <Icon size={24} className={v.iconClass} />
      </div>
      <h3 className="text-sm font-semibold mb-1 text-[#1A1A1A]">{title || v.title}</h3>
      <p className="text-xs text-[#73736D] mb-4 text-center max-w-[300px]">{message || v.message}</p>
      <div className="flex gap-2">
        {onBack && (
          <button onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#73736D] hover:text-[#1A1A1A] bg-[#FFFFFF] border border-[#D4D4CE] rounded-lg transition cursor-pointer">
            <ArrowLeft size={12} />Go Back
          </button>
        )}
        {onRetry && (
          <button onClick={onRetry}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-[#1A1A1A] hover:bg-[#30302E] text-[#FFFFFF] rounded-lg transition cursor-pointer">
            <RefreshCw size={12} />Retry
          </button>
        )}
      </div>
    </div>
  );
}
