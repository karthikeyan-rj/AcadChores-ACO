'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import {
  Globe, Terminal, Monitor, FileText, Eye, Cog, Loader2,
  CheckCircle2, XCircle, Clock, AlertTriangle, PlayCircle
} from 'lucide-react';

const iconMap: Record<string, React.ComponentType<any>> = {
  Globe, Terminal, Monitor, FileText, Eye, Cog,
  browser: Globe, terminal: Terminal, desktop: Monitor, file: FileText, vision: Eye,
};

interface AnimatedIconProps {
  name: string;
  status?: 'running' | 'completed' | 'failed' | 'idle' | 'warning';
  size?: number;
  className?: string;
}

export function AnimatedIcon({ name, status = 'idle', size = 16, className }: AnimatedIconProps) {
  const Icon = iconMap[name] || Cog;

  if (status === 'running') {
    return <Loader2 size={size} className={cn('animate-spin text-primary', className)} />;
  }
  if (status === 'completed') {
    return <CheckCircle2 size={size} className={cn('text-accent', className)} />;
  }
  if (status === 'failed') {
    return <XCircle size={size} className={cn('text-danger', className)} />;
  }
  if (status === 'warning') {
    return <AlertTriangle size={size} className={cn('text-warning', className)} />;
  }

  return <Icon size={size} className={cn('text-gray-400', className)} />;
}
