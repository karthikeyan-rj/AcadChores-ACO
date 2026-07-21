'use client';

import React from 'react';

export function PageSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-7 w-48 rounded bg-surface-2 border border-theme" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-surface-2 border border-theme" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-surface-2 border border-theme" />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-7 w-40 rounded bg-surface-2 border border-theme" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-xl bg-surface-2 border border-theme p-4 space-y-2">
            <div className="h-3 w-20 rounded bg-surface-hover" />
            <div className="h-6 w-14 rounded bg-surface-hover" />
            <div className="h-2 w-24 rounded bg-surface-2" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-64 rounded-xl bg-surface-2 border border-theme" />
        <div className="h-64 rounded-xl bg-surface-2 border border-theme" />
      </div>
    </div>
  );
}

export function SettingsSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-7 w-36 rounded bg-surface-2 border border-theme" />
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-theme bg-surface p-5 space-y-3">
          <div className="h-4 w-32 rounded bg-surface-2" />
          {Array.from({ length: 2 }).map((_, j) => (
            <div key={j} className="flex items-center gap-3">
              <div className="h-3 flex-1 rounded bg-surface-2" />
              <div className="h-6 w-10 rounded-full bg-surface-hover" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export function ConversationSkeleton() {
  return (
    <div className="flex flex-col gap-3 animate-pulse">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
          <div className={`rounded-xl border border-theme ${
            i % 2 === 0 ? 'bg-surface-2 w-[65%]' : 'bg-surface w-[75%]'
          }`}>
            <div className="p-4 space-y-2">
              <div className="h-3 rounded bg-surface-hover w-[80%]" />
              <div className="h-3 rounded bg-surface-2 w-[60%]" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-7 w-40 rounded bg-surface-2 border border-theme" />
      <div className="rounded-xl border border-theme overflow-hidden">
        <div className="h-10 bg-surface-2 border-b border-theme flex items-center px-4 gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="h-3 rounded bg-surface-hover flex-1" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="h-12 border-b border-theme last:border-b-0 flex items-center px-4 gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="h-3 rounded bg-surface-2 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
