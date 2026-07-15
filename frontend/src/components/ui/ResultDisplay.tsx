'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Link, FileText, Terminal, Globe } from 'lucide-react';
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
        <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1 my-2 text-[#A1A1AA]">
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
      if (match.index > lastIndex) {
        parts.push(t.slice(lastIndex, match.index));
      }
      if (match[2]) {
        parts.push(<strong key={match.index} className="text-[#F4F4F5] font-semibold">{match[2]}</strong>);
      } else {
        const url = match[0];
        parts.push(
          <a key={match.index} href={url} target="_blank" rel="noopener noreferrer" className="text-[#7C3AED] underline hover:text-[#6D28D9] break-all">
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
          <span className="text-[#7C3AED] font-bold text-xs mt-0.5 shrink-0 w-5 text-right">{numMatch[1]}.</span>
          <span className="text-[#A1A1AA] text-xs leading-relaxed">{renderInline(numMatch[2])}</span>
        </div>
      );
    } else if (bulletMatch) {
      listItems.push(
        <li key={i} className="text-xs">{renderInline(bulletMatch[1])}</li>
      );
    } else {
      flushList();
      elements.push(
        <p key={i} className="text-xs text-[#A1A1AA] leading-relaxed my-1">{renderInline(line)}</p>
      );
    }
  }
  flushList();
  return elements;
}

export function ResultDisplay({ result }: ResultDisplayProps) {
  if (!result) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-[14px] border border-[#4ADE80]/20 bg-[#4ADE80]/5 overflow-hidden shadow-matte"
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[#4ADE80]/10">
        <CheckCircle2 size={13} className="text-[#4ADE80]" />
        <span className="text-[11px] font-semibold text-[#4ADE80] uppercase tracking-wider">Result</span>
      </div>
      <div className="p-4 pl-8 max-h-[400px] overflow-y-auto">
        {renderResult(result)}
      </div>
    </motion.div>
  );
}
