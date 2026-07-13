'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  HelpCircle, Search, BookOpen, Keyboard, MessageSquare, ChevronDown,
  ChevronRight, ExternalLink, Copy, Check, Github, Mail, FileText,
  Zap, Globe, Terminal, Database, Shield, Clock, AlertTriangle,
  RefreshCw, Wrench
} from 'lucide-react';
import { cn } from '@/lib/utils';

type HelpSection = 'docs' | 'shortcuts' | 'commands' | 'faq' | 'troubleshoot' | 'support';

const shortcuts = [
  { keys: ['Ctrl', 'K'], action: 'Open Command Palette', desc: 'Search and navigate anywhere' },
  { keys: ['Ctrl', 'N'], action: 'New Workflow', desc: 'Open AI Assistant to create a workflow' },
  { keys: ['Ctrl', '/'], action: 'Toggle Sidebar', desc: 'Collapse or expand the sidebar' },
  { keys: ['Ctrl', 'Enter'], action: 'Execute Prompt', desc: 'Run the current prompt in AI Assistant' },
  { keys: ['Escape'], action: 'Close Modal / Cancel', desc: 'Close any open modal or cancel action' },
  { keys: ['Ctrl', ','], action: 'Open Settings', desc: 'Navigate to application settings' },
  { keys: ['Ctrl', '1-9'], action: 'Navigate to Page', desc: 'Jump to a sidebar page by position' },
];

const supportedCommands = [
  { icon: <Globe size={14} className="text-blue-400" />, name: 'navigate', desc: 'Open a URL in the browser', example: 'navigate to google.com' },
  { icon: <Globe size={14} className="text-blue-400" />, name: 'click', desc: 'Click an element on the page', example: 'click the search button' },
  { icon: <Globe size={14} className="text-blue-400" />, name: 'fill', desc: 'Fill a form field', example: 'fill the email field with user@test.com' },
  { icon: <Globe size={14} className="text-blue-400" />, name: 'search', desc: 'Search on a website', example: 'search for AI news on google.com' },
  { icon: <Terminal size={14} className="text-green-400" />, name: 'run', desc: 'Execute a terminal command', example: 'run ls -la in terminal' },
  { icon: <FileText size={14} className="text-amber-400" />, name: 'create_file', desc: 'Create a new file', example: 'create a file called notes.txt on desktop' },
  { icon: <FileText size={14} className="text-amber-400" />, name: 'read_file', desc: 'Read file contents', example: 'read the contents of report.pdf' },
  { icon: <Mail size={14} className="text-red-400" />, name: 'send_email', desc: 'Send an email via Gmail', example: 'send email to john@example.com about the meeting' },
  { icon: <Globe size={14} className="text-red-400" />, name: 'youtube_search', desc: 'Search YouTube and extract info', example: 'search YouTube for top 5 AI tutorials' },
  { icon: <Search size={14} className="text-purple-400" />, name: 'summarize', desc: 'Summarize page content', example: 'summarize this page' },
];

const faqItems = [
  { q: 'What is ACO?', a: 'ACO (Autonomous Computer Operator) is an AI-powered workflow automation platform. It uses LLMs to plan tasks and Playwright to execute browser, terminal, and file operations autonomously on your local machine.' },
  { q: 'How does the AI planning work?', a: 'When you enter a prompt, ACO sends it to a local LLM (Ollama) which generates a structured plan of steps. Each step specifies an agent type (browser, terminal, file, etc.) and an action to perform. You can review and edit the plan before execution.' },
  { q: 'What browsers are supported?', a: 'ACO uses Playwright which supports Chromium, Firefox, and WebKit. By default it uses Chromium for maximum compatibility with modern websites. You can change this in Settings > Browser.' },
  { q: 'Is my data sent to external servers?', a: 'No. ACO runs entirely locally. The LLM runs via Ollama on your machine. Browser sessions, file operations, and all data remain on your system. No data is sent externally unless you explicitly configure external API providers.' },
  { q: 'How do I add custom workflows?', a: 'Go to the AI Assistant tab and describe what you want to do in natural language. ACO will generate a plan automatically. You can also use pre-built templates from the Plugin Marketplace.' },
  { q: 'Can I schedule tasks?', a: 'Yes. Go to the Scheduler page to create recurring or one-time tasks. You can set them to run hourly, daily, weekly, or monthly. View upcoming tasks in the calendar or list view.' },
  { q: 'What happens if a step fails?', a: 'ACO has a recovery engine that automatically retries failed steps with alternative strategies. If recovery fails, the workflow is marked as failed and you can manually intervene or retry.' },
  { q: 'How many workers can run simultaneously?', a: 'By default, ACO runs 3 workers, allowing up to 3 workflows to execute concurrently. This can be configured in the backend settings.' },
  { q: 'How do I connect Gmail?', a: 'Go to Settings > Permissions > API Keys and configure your Gmail OAuth token. You may need to set up Google Cloud OAuth credentials first. See the Gmail Enhanced plugin for detailed setup instructions.' },
  { q: 'Can I use ACO with external LLMs?', a: 'Yes. While ACO defaults to Ollama (local), you can configure OpenAI, Anthropic, or custom endpoints in Settings > AI Model. Note that external providers will send data to their servers.' },
];

const troubleshootingItems = [
  { problem: 'Backend shows as "Offline"', solution: 'Make sure the backend server is running: python -m uvicorn app.main:app --host 0.0.0.0 --port 8001. Check that port 8001 is not blocked by a firewall.', icon: <Globe size={14} className="text-danger" /> },
  { problem: 'WebSocket connection fails', solution: 'Verify the backend is accessible and the WebSocket URL in Settings > Developer matches your backend address. Check browser console for connection errors.', icon: <RefreshCw size={14} className="text-warning" /> },
  { problem: 'Workflow execution stalls', solution: 'The workflow may be waiting for a permission request. Check the AI Assistant page for permission modals. You can also check the Live Console for detailed logs.', icon: <Clock size={14} className="text-primary" /> },
  { problem: 'Gmail send fails', solution: 'Verify your Gmail OAuth token is configured in Settings > Permissions > API Keys. Ensure the browser session is active and you are logged into Gmail.', icon: <Mail size={14} className="text-danger" /> },
  { problem: 'LLM returns empty or invalid plans', solution: 'Check that Ollama is running and the selected model is loaded. Try a different model in Settings > AI Model. Check the Console for planner errors.', icon: <Zap size={14} className="text-amber-400" /> },
  { problem: 'Browser automation not working', solution: 'Ensure Playwright browsers are installed: playwright install chromium. Check if headless mode is causing issues with specific sites by disabling it in Settings > Browser.', icon: <Globe size={14} className="text-blue-400" /> },
];

const docsCategories = [
  { icon: Zap, title: 'Getting Started', desc: 'Quick start guide for new users', items: ['Installation', 'First Workflow', 'Connecting to Backend', 'System Requirements'] },
  { icon: Globe, title: 'Browser Automation', desc: 'Web navigation and interaction', items: ['Navigate', 'Click & Fill', 'Screenshots', 'Gmail Integration', 'YouTube Scraping'] },
  { icon: Terminal, title: 'Terminal Operations', desc: 'Shell command execution', items: ['Run Commands', 'SSH Access', 'Output Parsing', 'Script Generation'] },
  { icon: Database, title: 'Memory & Data', desc: 'Persistent storage and retrieval', items: ['Memory Manager', 'File Explorer', 'MongoDB Integration', 'Context Caching'] },
  { icon: Shield, title: 'Security & Permissions', desc: 'Access control and safety', items: ['Permission System', 'Auto-Approval', 'Sandboxing', 'API Key Management'] },
  { icon: Clock, title: 'Scheduling', desc: 'Automated task execution', items: ['Create Schedule', 'Recurring Tasks', 'Calendar View', 'Cron Expressions'] },
];

export default function HelpPage() {
  const [section, setSection] = useState<HelpSection>('docs');
  const [search, setSearch] = useState('');
  const [expandedFaq, setExpandedFaq] = useState<Set<number>>(new Set());
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const toggleFaq = (i: number) => {
    setExpandedFaq(prev => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const filteredFaq = faqItems.filter(f =>
    !search || f.q.toLowerCase().includes(search.toLowerCase()) || f.a.toLowerCase().includes(search.toLowerCase())
  );

  const filteredCommands = supportedCommands.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.desc.toLowerCase().includes(search.toLowerCase())
  );

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  };

  return (
    <div className="p-6 max-w-[1000px] mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">Help & Documentation</h1>
        <p className="text-xs text-gray-500 mt-0.5">Guides, shortcuts, commands, FAQ, and troubleshooting</p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input type="text" placeholder="Search docs, commands, FAQ..." value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 text-xs bg-card border border-border rounded-xl outline-none focus:border-primary transition" />
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 bg-card border border-border rounded-xl p-1 w-fit flex-wrap">
        {([
          ['docs', BookOpen, 'Documentation'],
          ['shortcuts', Keyboard, 'Shortcuts'],
          ['commands', Terminal, 'Commands'],
          ['faq', MessageSquare, 'FAQ'],
          ['troubleshoot', Wrench, 'Troubleshoot'],
          ['support', HelpCircle, 'Support'],
        ] as [HelpSection, any, string][]).map(([id, Icon, label]) => (
          <button key={id} onClick={() => setSection(id)}
            className={cn('flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition cursor-pointer',
              section === id ? 'bg-primary/10 text-primary' : 'text-gray-400 hover:text-foreground')}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div key={section} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.15 }}>

          {section === 'docs' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {docsCategories.map((cat, i) => {
                const Icon = cat.icon;
                return (
                  <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                    className="rounded-xl border border-border bg-card/80 p-5 hover:border-border-light hover:bg-card-hover transition-all cursor-pointer">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
                      <Icon size={20} className="text-primary" />
                    </div>
                    <h3 className="text-sm font-semibold mb-1">{cat.title}</h3>
                    <p className="text-[11px] text-gray-500 mb-3">{cat.desc}</p>
                    <div className="space-y-1">
                      {cat.items.map((item, j) => (
                        <div key={j} className="flex items-center gap-2 text-[11px] text-gray-400 hover:text-foreground transition cursor-pointer">
                          <ChevronRight size={10} className="text-gray-600" />{item}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}

          {section === 'shortcuts' && (
            <div className="rounded-xl border border-border bg-card/80 overflow-hidden">
              <div className="px-5 py-3 border-b border-border">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Keyboard Shortcuts</h3>
              </div>
              <div className="divide-y divide-border/50">
                {shortcuts.map((s, i) => (
                  <div key={i} className="flex items-center justify-between px-5 py-3.5 hover:bg-surface-2 transition">
                    <div>
                      <span className="text-xs text-gray-300">{s.action}</span>
                      <p className="text-[10px] text-gray-500 mt-0.5">{s.desc}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-4">
                      {s.keys.map((k, j) => (
                        <React.Fragment key={j}>
                          {j > 0 && <span className="text-gray-600 text-[10px]">+</span>}
                          <kbd className="px-2 py-1 rounded-md bg-surface border border-border text-[10px] font-mono text-gray-400">{k}</kbd>
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {section === 'commands' && (
            <div className="rounded-xl border border-border bg-card/80 overflow-hidden">
              <div className="px-5 py-3 border-b border-border">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Supported Commands</h3>
                <p className="text-[10px] text-gray-500 mt-1">Use these commands in the AI Assistant prompt</p>
              </div>
              <div className="divide-y divide-border/50">
                {filteredCommands.map((cmd, i) => (
                  <div key={i} className="px-5 py-3 hover:bg-surface-2 transition">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        {cmd.icon}
                        <span className="text-xs font-mono font-semibold text-foreground">{cmd.name}</span>
                      </div>
                      <button onClick={() => copyToClipboard(cmd.example, i)} className="p-1 rounded hover:bg-surface transition cursor-pointer" title="Copy example">
                        {copiedIdx === i ? <Check size={12} className="text-accent" /> : <Copy size={12} className="text-gray-500" />}
                      </button>
                    </div>
                    <p className="text-[11px] text-gray-400">{cmd.desc}</p>
                    <p className="text-[10px] text-gray-600 font-mono mt-1">Example: {cmd.example}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {section === 'faq' && (
            <div className="space-y-2">
              {filteredFaq.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-xs">No FAQ items match your search</div>
              ) : (
                filteredFaq.map((f, i) => (
                  <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                    className="rounded-xl border border-border bg-card/80 overflow-hidden">
                    <button onClick={() => toggleFaq(i)}
                      className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-surface-2 transition cursor-pointer">
                      <span className="text-xs font-medium text-foreground">{f.q}</span>
                      {expandedFaq.has(i) ? <ChevronDown size={14} className="text-gray-500 shrink-0" /> : <ChevronRight size={14} className="text-gray-500 shrink-0" />}
                    </button>
                    <AnimatePresence>
                      {expandedFaq.has(i) && (
                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                          <div className="px-5 pb-4 text-xs text-gray-400 leading-relaxed border-t border-border/50 pt-3">{f.a}</div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))
              )}
            </div>
          )}

          {section === 'troubleshoot' && (
            <div className="space-y-3">
              {troubleshootingItems.map((item, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                  className="rounded-xl border border-border bg-card/80 p-5">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center shrink-0">{item.icon}</div>
                    <div>
                      <h4 className="text-xs font-semibold mb-1">{item.problem}</h4>
                      <p className="text-[11px] text-gray-400 leading-relaxed">{item.solution}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {section === 'support' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-border bg-card/80 p-5">
                <h3 className="text-sm font-semibold mb-3">Get Help</h3>
                <div className="space-y-2">
                  <SupportLink icon={Github} label="GitHub Issues" desc="Report bugs or request features" href="https://github.com" />
                  <SupportLink icon={Mail} label="Email Support" desc="contact@aco.dev" href="mailto:contact@aco.dev" />
                  <SupportLink icon={FileText} label="API Documentation" desc="REST API reference" href="#" />
                  <SupportLink icon={MessageSquare} label="Community Discord" desc="Join the community" href="#" />
                </div>
              </div>
              <div className="rounded-xl border border-border bg-card/80 p-5 space-y-4">
                <h3 className="text-sm font-semibold">System Info</h3>
                <div className="space-y-2 text-xs">
                  <InfoRow label="ACO Version" value="1.0.0" />
                  <InfoRow label="Frontend" value="Next.js 14 + React 18" />
                  <InfoRow label="Backend" value="FastAPI + Playwright" />
                  <InfoRow label="AI" value="Ollama (Local)" />
                  <InfoRow label="Database" value="MongoDB" />
                  <InfoRow label="Cache" value="Redis" />
                </div>
                <div className="pt-3 border-t border-border">
                  <h4 className="text-xs font-semibold mb-2">Diagnostics</h4>
                  <button className="flex items-center gap-2 px-3 py-2 text-xs text-primary hover:bg-primary/5 border border-primary/20 rounded-lg transition cursor-pointer w-full">
                    <Wrench size={13} />Run System Diagnostics
                  </button>
                </div>
              </div>
            </div>
          )}

        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function SupportLink({ icon: Icon, label, desc, href }: { icon: any; label: string; desc: string; href: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-border-light hover:bg-surface-2 transition group cursor-pointer">
      <div className="w-8 h-8 rounded-lg bg-surface flex items-center justify-center shrink-0">
        <Icon size={16} className="text-gray-400 group-hover:text-primary transition" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium">{label}</p>
        <p className="text-[10px] text-gray-500">{desc}</p>
      </div>
      <ExternalLink size={12} className="text-gray-600 group-hover:text-gray-400 shrink-0" />
    </a>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
  );
}
