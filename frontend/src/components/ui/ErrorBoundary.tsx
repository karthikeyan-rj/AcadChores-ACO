'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] gap-4 text-center">
          <div className="w-12 h-12 rounded-xl bg-status-error-soft border border-status-error flex items-center justify-center">
            <AlertTriangle size={20} className="text-status-error" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-theme">Something went wrong</p>
            <p className="text-xs text-theme-tertiary max-w-md">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
          </div>
          <button
            onClick={this.reset}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-text-primary text-text-inverse text-xs font-medium hover:opacity-90 transition cursor-pointer"
          >
            <RefreshCw size={13} />
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
