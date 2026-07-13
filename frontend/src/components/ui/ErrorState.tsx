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
    iconClass: 'text-danger',
    bgClass: 'bg-danger/5 border-danger/20',
  },
  offline: {
    icon: WifiOff,
    title: 'Connection lost',
    message: 'Unable to reach the backend server. Check your connection.',
    iconClass: 'text-warning',
    bgClass: 'bg-warning/5 border-warning/20',
  },
  'not-found': {
    icon: AlertTriangle,
    title: 'Not found',
    message: 'The resource you are looking for does not exist.',
    iconClass: 'text-gray-400',
    bgClass: 'bg-surface border-border',
  },
};

export function ErrorState({ title, message, onRetry, onBack, variant = 'error', className }: ErrorStateProps) {
  const v = variants[variant];
  const Icon = v.icon;

  return (
    <div className={cn('flex flex-col items-center justify-center py-16', className)}>
      <div className={cn('w-14 h-14 rounded-2xl border flex items-center justify-center mb-4', v.bgClass)}>
        <Icon size={24} className={v.iconClass} />
      </div>
      <h3 className="text-sm font-semibold mb-1">{title || v.title}</h3>
      <p className="text-xs text-gray-500 mb-4 text-center max-w-[300px]">{message || v.message}</p>
      <div className="flex gap-2">
        {onBack && (
          <button onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-foreground bg-card border border-border rounded-lg transition cursor-pointer">
            <ArrowLeft size={12} />Go Back
          </button>
        )}
        {onRetry && (
          <button onClick={onRetry}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-primary hover:bg-primary-hover text-white rounded-lg transition cursor-pointer shadow-lg shadow-primary/20">
            <RefreshCw size={12} />Retry
          </button>
        )}
      </div>
    </div>
  );
}
