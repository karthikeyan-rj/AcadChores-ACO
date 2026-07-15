'use client';

import React, { useState, useRef } from 'react';
import { Play, Paperclip, Mic, Camera, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PromptBoxProps {
  prompt: string;
  onPromptChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  disabled: boolean;
}

const suggestions = [
  'Send email to user@domain.com about meeting tomorrow',
  'Search YouTube for top 5 AI news and summarize',
  'Open terminal and run ping google.com',
  'Find all PDF files on my desktop',
  'Go to google.com and search for machine learning',
];

export function PromptBox({ prompt, onPromptChange, onSubmit, loading, disabled }: PromptBoxProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <div className={cn(
        'composer-focus rounded-[14px] border transition-all duration-200',
        prompt ? 'border-[#7C3AED]/30' : 'border-white/[0.07]',
        'bg-[#121419]'
      )}>
        {/* Context label */}
        <div className="flex items-center gap-2 px-4 pt-3 pb-0">
          <Sparkles size={11} className="text-[#7C3AED]" />
          <span className="text-[10px] text-[#71717A] font-medium uppercase tracking-wider">
            Command Composer
          </span>
        </div>

        {/* Textarea */}
        <div className="px-4 py-3">
          <textarea
            ref={textareaRef}
            placeholder="Tell ACO what to do..."
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => !prompt && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            rows={2}
            aria-label="Task instruction"
            className="w-full bg-transparent outline-none resize-none text-[13px] placeholder-[#71717A] text-[#F4F4F5] leading-relaxed min-h-[44px] max-h-[160px]"
          />
        </div>

        {/* Footer bar */}
        <div className="flex items-center justify-between px-4 pb-3">
          <div className="flex items-center gap-0.5">
            <button className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition cursor-pointer" title="Attach file" aria-label="Attach file">
              <Paperclip size={15} />
            </button>
            <button className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition cursor-pointer" title="Voice input" aria-label="Voice input">
              <Mic size={15} />
            </button>
            <button className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition cursor-pointer" title="Screenshot" aria-label="Take screenshot">
              <Camera size={15} />
            </button>
            <span className="text-[10px] text-[#71717A]/50 ml-2 hidden sm:inline font-mono">Shift+Enter for newline</span>
          </div>
          <button
            onClick={onSubmit}
            disabled={disabled || loading || !prompt.trim()}
            aria-label={loading ? 'Executing...' : 'Run command'}
            className={cn(
              'flex items-center gap-1.5 px-3.5 py-1.5 rounded-[10px] text-[11px] font-semibold transition-all duration-200',
              prompt.trim() && !loading
                ? 'bg-[#7C3AED] hover:bg-[#6D28D9] text-white cursor-pointer'
                : 'bg-white/[0.04] text-[#71717A] cursor-not-allowed'
            )}
          >
            {loading ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <>
                <span>Run</span>
                <Play size={11} className="fill-current" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && !prompt && (
        <div className="absolute top-full left-0 right-0 mt-2 py-2 bg-[#121419] border border-white/[0.07] rounded-[10px] shadow-2xl z-50">
          <p className="px-3 py-1.5 text-[10px] text-[#71717A] uppercase font-semibold tracking-wider">Suggestions</p>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onMouseDown={(e) => {
                e.preventDefault();
                onPromptChange(s);
                setShowSuggestions(false);
              }}
              className="w-full text-left px-3 py-2 text-[12px] text-[#A1A1AA] hover:bg-white/[0.04] hover:text-[#F4F4F5] transition cursor-pointer flex items-center gap-2"
            >
              <Sparkles size={10} className="text-[#7C3AED] shrink-0" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
