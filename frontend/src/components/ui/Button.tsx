'use client';

import React from 'react';
import { cn } from '@/lib/utils';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-[#7C3AED] hover:bg-[#6D28D9] text-white shadow-matte',
  secondary: 'bg-[#181B21] hover:bg-[#1E2128] text-[#F4F4F5] border border-white/[0.07] hover:border-white/[0.12]',
  ghost: 'bg-transparent hover:bg-white/5 text-[#A1A1AA] hover:text-[#F4F4F5]',
  danger: 'bg-[#F87171]/10 hover:bg-[#F87171]/15 text-[#F87171] border border-[#F87171]/20',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-xs gap-2',
  lg: 'px-5 py-2.5 text-sm gap-2',
};

export function Button({ variant = 'primary', size = 'md', loading, icon, className, children, disabled, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium rounded-[10px] transition-all duration-150 cursor-pointer',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon}
      {children}
    </button>
  );
}
