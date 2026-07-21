'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4 text-center">
      <div className="w-12 h-12 rounded-xl bg-status-error-soft border border-status-error flex items-center justify-center">
        <AlertTriangle size={20} className="text-status-error" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-theme">Something went wrong</p>
        <p className="text-xs text-theme-tertiary max-w-md">
          {error?.message || 'An unexpected error occurred'}
        </p>
      </div>
      <button
        onClick={reset}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-text-primary text-text-inverse text-xs font-medium hover:opacity-90 transition cursor-pointer"
      >
        <RefreshCw size={13} />
        Try Again
      </button>
    </div>
  );
}
