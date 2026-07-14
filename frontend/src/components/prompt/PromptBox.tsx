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
        'rounded-2xl border transition-all duration-200',
        prompt ? 'border-primary/30' : 'border-border',
        'bg-card'
      )}>
        <div className="flex items-start gap-3 p-4">
          <Sparkles size={18} className="text-primary mt-1 shrink-0" />
          <textarea
            ref={textareaRef}
            placeholder="Tell ACO what to do..."
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => !prompt && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            rows={2}
            className="flex-1 bg-transparent outline-none resize-none text-sm placeholder-gray-500 text-foreground leading-relaxed"
          />
        </div>
        <div className="flex items-center justify-between px-4 pb-3">
          <div className="flex items-center gap-1">
            <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface-2 transition cursor-pointer" title="Attach file">
              <Paperclip size={14} />
            </button>
            <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface-2 transition cursor-pointer" title="Voice input">
              <Mic size={14} />
            </button>
            <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface-2 transition cursor-pointer" title="Screenshot">
              <Camera size={14} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-600 hidden sm:inline">Model: Qwen (Ollama)</span>
            <button
              onClick={onSubmit}
              disabled={disabled || loading || !prompt.trim()}
              className={cn(
                'flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200',
                prompt.trim() && !loading
                  ? 'bg-primary hover:bg-primary-hover text-white shadow-lg shadow-primary/20 cursor-pointer'
                  : 'bg-surface-2 text-gray-600 cursor-not-allowed'
              )}
            >
              {loading ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <>
                  <span>Execute</span>
                  <Play size={12} className="fill-current" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && !prompt && (
        <div className="absolute top-full left-0 right-0 mt-2 py-2 bg-card border border-border rounded-xl shadow-2xl z-50">
          <p className="px-3 py-1.5 text-[10px] text-gray-500 uppercase font-semibold tracking-wider">Suggestions</p>
          {suggestions.map((s, i) => (
            <button
              key={i}
              onMouseDown={(e) => {
                e.preventDefault();
                onPromptChange(s);
                setShowSuggestions(false);
              }}
              className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-surface-2 hover:text-foreground transition cursor-pointer flex items-center gap-2"
            >
              <Sparkles size={10} className="text-primary shrink-0" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
