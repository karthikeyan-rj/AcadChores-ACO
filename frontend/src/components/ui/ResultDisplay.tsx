'use client';

import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ResultDisplayProps {
  result: string;
}

function renderResult(text: string) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1 my-2 text-theme-secondary">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  const renderInline = (t: string) => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*(.+?)\*\*|https?:\/\/[^\s→]+)/g;
    let lastIndex = 0;
    let match;
    while ((match = regex.exec(t)) !== null) {
      if (match.index > lastIndex) parts.push(t.slice(lastIndex, match.index));
      if (match[2]) {
        parts.push(<strong key={match.index} className="text-theme font-semibold">{match[2]}</strong>);
      } else {
        const url = match[0];
        parts.push(
          <a key={match.index} href={url} target="_blank" rel="noopener noreferrer" className="text-status-info underline hover:text-theme break-all">
            {url}
          </a>
        );
      }
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < t.length) parts.push(t.slice(lastIndex));
    return parts;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) { flushList(); continue; }
    const numMatch = line.match(/^(\d+)\.\s+(.+)/);
    const bulletMatch = line.match(/^[-•]\s+(.+)/);
    if (numMatch) {
      flushList();
      elements.push(
        <div key={i} className="flex gap-3 my-1.5">
          <span className="text-theme font-bold text-xs mt-0.5 shrink-0 w-5 text-right">{numMatch[1]}.</span>
          <span className="text-theme-secondary text-xs leading-relaxed">{renderInline(numMatch[2])}</span>
        </div>
      );
    } else if (bulletMatch) {
      listItems.push(<li key={i} className="text-xs">{renderInline(bulletMatch[1])}</li>);
    } else {
      flushList();
      elements.push(<p key={i} className="text-xs text-theme-secondary leading-relaxed my-1">{renderInline(line)}</p>);
    }
  }
  flushList();
  return elements;
}

export function ResultDisplay({ result }: ResultDisplayProps) {
  if (!result) return null;
  return (
    <div className="animate-[fadeIn_0.15s_ease-out] rounded-xl border border-theme bg-surface overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-theme">
        <CheckCircle2 size={13} className="text-status-active" />
        <span className="text-[11px] font-semibold text-status-active uppercase tracking-wider">Result</span>
      </div>
      <div className="p-4 pl-8 max-h-[400px] overflow-y-auto">
        {renderResult(result)}
      </div>
    </div>
  );
}
