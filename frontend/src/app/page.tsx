'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, useScroll, useTransform, useInView, AnimatePresence } from 'framer-motion';
import {
  Cpu, Globe, Terminal, Monitor, FileText, Eye, Play, ArrowRight, Check,
  X, ChevronRight, Github, ExternalLink, Zap, Shield, Brain, Layers,
  Search, Puzzle, Clock, Database, BarChart3, Settings, Mail, MessageSquare,
  Copy, Send, ArrowUpRight, Sparkles, Bot, Workflow, RefreshCw, CheckCircle2,
  XCircle, ChevronDown, Menu, XIcon, MonitorPlay, Keyboard, Lock, Fingerprint,
  Scan, Server, HardDrive, Binary, Code2, Box, Rocket, Users, Globe2,
  FileSearch, Timer, Activity, GitBranch, Cog
} from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.08 } }
};

function useSectionInView(threshold = 0.15) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: threshold });
  return { ref, isInView };
}

function Section({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  const { ref, isInView } = useSectionInView();
  return (
    <motion.section
      ref={ref}
      id={id}
      initial="hidden"
      animate={isInView ? 'visible' : 'hidden'}
      variants={{ visible: { transition: { staggerChildren: 0.06 } } }}
      className={`relative ${className}`}
    >
      {children}
    </motion.section>
  );
}

function FadeIn({ children, className = '', delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div
      variants={fadeUp}
      className={className}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  );
}

/* ─── NAVBAR ─── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const links = [
    { label: 'Features', href: '#features' },
    { label: 'Architecture', href: '#architecture' },
    { label: 'Security', href: '#security' },
    { label: 'Demo', href: '#demo' },
  ];

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#09090B]/80 backdrop-blur-xl border-b border-white/5'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <Cpu size={16} className="text-primary" />
          </div>
          <span className="font-bold text-base text-white">ACO</span>
        </a>

        <nav className="hidden md:flex items-center gap-8">
          {links.map(l => (
            <a key={l.href} href={l.href} className="text-[13px] text-gray-400 hover:text-white transition-colors duration-200">
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <a href="https://github.com" target="_blank" rel="noopener noreferrer"
            className="text-[13px] text-gray-400 hover:text-white transition-colors flex items-center gap-1.5">
            <Github size={14} />
            GitHub
          </a>
          <a href="/login"
            className="text-[13px] text-gray-400 hover:text-white transition-colors px-3 py-1.5">
            Sign In
          </a>
          <a href="/login"
            className="text-[13px] font-medium bg-primary hover:bg-primary-hover text-white px-4 py-1.5 rounded-lg transition-all duration-200 shadow-lg shadow-primary/20">
            Get Started
          </a>
        </div>

        <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-gray-400 hover:text-white">
          {mobileOpen ? <XIcon size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-[#09090B]/95 backdrop-blur-xl border-b border-white/5 overflow-hidden"
          >
            <div className="px-6 py-4 space-y-3">
              {links.map(l => (
                <a key={l.href} href={l.href} onClick={() => setMobileOpen(false)}
                  className="block text-sm text-gray-400 hover:text-white transition-colors py-2">
                  {l.label}
                </a>
              ))}
              <div className="pt-3 border-t border-white/5 flex flex-col gap-2">
                <a href="/login" className="text-sm text-gray-400 hover:text-white py-2">Sign In</a>
                <a href="/login" className="text-sm font-medium bg-primary text-white px-4 py-2.5 rounded-lg text-center">Get Started</a>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

/* ─── HERO ─── */
function Hero() {
  const commands = [
    { text: 'Summarize today\'s AI news', icon: Globe, color: 'text-blue-400' },
    { text: 'Send email to team@company.com', icon: Mail, color: 'text-green-400' },
    { text: 'Organize my Downloads folder', icon: FolderIcon, color: 'text-amber-400' },
    { text: 'Search YouTube for tutorials', icon: Play, color: 'text-red-400' },
  ];

  const [cmdIdx, setCmdIdx] = useState(0);
  const [typed, setTyped] = useState('');
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    const target = commands[cmdIdx].text;
    let i = 0;
    setTyped('');
    const interval = setInterval(() => {
      if (i <= target.length) {
        setTyped(target.slice(0, i));
        i++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          setCmdIdx(p => (p + 1) % commands.length);
        }, 2000);
      }
    }, 50);
    return () => clearInterval(interval);
  }, [cmdIdx]);

  useEffect(() => {
    const c = setInterval(() => setShowCursor(p => !p), 530);
    return () => clearInterval(c);
  }, []);

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center pt-24 pb-20 px-6 overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/8 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/3 w-[400px] h-[400px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="text-center max-w-4xl mx-auto relative z-10"
      >
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 mb-8"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <span className="text-[11px] font-medium text-primary">v1.0 — Now Available</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.7 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-white leading-[1.05]"
        >
          Your Autonomous
          <br />
          <span className="bg-gradient-to-r from-primary via-purple-400 to-blue-400 bg-clip-text text-transparent">
            Computer Operator
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.7 }}
          className="mt-6 text-base md:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed"
        >
          An autonomous AI agent that understands goals, plans workflows, and operates your computer securely.
          Browse websites, automate tasks, manage files, and execute commands — all from natural language.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
        >
          <a href="/login"
            className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-primary/25 hover:shadow-primary/40 hover:-translate-y-0.5">
            Get Started <ArrowRight size={16} />
          </a>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all duration-200 border border-white/10 hover:border-white/20">
            <Github size={16} /> View GitHub
          </a>
          <a href="#demo"
            className="flex items-center gap-2 text-gray-400 hover:text-white px-6 py-3 rounded-xl text-sm font-medium transition-all duration-200 border border-white/5 hover:border-white/15">
            <Play size={14} className="fill-current" /> Watch Demo
          </a>
        </motion.div>

        {/* Typing terminal */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="mt-16 max-w-xl mx-auto"
        >
          <div className="rounded-2xl border border-white/10 bg-[#111219]/80 backdrop-blur-xl overflow-hidden shadow-2xl shadow-black/50">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
              </div>
              <span className="text-[10px] text-gray-500 ml-2 font-mono">ACO Terminal</span>
            </div>
            <div className="p-5 font-mono text-sm">
              <div className="flex items-center gap-2 text-gray-500 mb-3">
                <Sparkles size={12} className="text-primary" />
                <span className="text-[11px]">Tell ACO what to do...</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-primary">$</span>
                <span className="text-white">{typed}</span>
                <span className={`w-2 h-4 bg-primary ${showCursor ? 'opacity-100' : 'opacity-0'} transition-opacity`} />
              </div>
              <div className="mt-4 flex items-center gap-3">
                {commands.map((cmd, i) => {
                  const Icon = cmd.icon;
                  return (
                    <div key={i} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] transition-all duration-300 ${
                      i === cmdIdx ? 'bg-white/5 border border-white/10 text-white' : 'text-gray-600'
                    }`}>
                      <Icon size={10} className={i === cmdIdx ? cmd.color : ''} />
                      {cmd.text.length > 20 ? cmd.text.slice(0, 20) + '...' : cmd.text}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Floating agent badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="mt-10 flex flex-wrap justify-center gap-3"
        >
          {[
            { icon: Globe, label: 'Browser', color: 'text-blue-400' },
            { icon: Monitor, label: 'Desktop', color: 'text-green-400' },
            { icon: Terminal, label: 'Terminal', color: 'text-amber-400' },
            { icon: Eye, label: 'Vision', color: 'text-purple-400' },
            { icon: FileText, label: 'Files', color: 'text-cyan-400' },
          ].map((a, i) => (
            <motion.div
              key={a.label}
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 3, delay: i * 0.3, repeat: Infinity, ease: 'easeInOut' }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/5 bg-white/[0.02] text-[11px] text-gray-400"
            >
              <a.icon size={12} className={a.color} />
              {a.label}
            </motion.div>
          ))}
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div animate={{ y: [0, 6, 0] }} transition={{ duration: 2, repeat: Infinity }}
          className="w-5 h-8 rounded-full border border-white/10 flex items-start justify-center p-1">
          <div className="w-1 h-2 rounded-full bg-white/20" />
        </motion.div>
      </motion.div>
    </section>
  );
}

function FolderIcon({ size, className }: { size: number; className?: string }) {
  return <FileText size={size} className={className} />;
}

/* ─── LIVE DEMO ─── */
function LiveDemo() {
  const examples = [
    { text: 'Summarize today\'s AI news', category: 'Research' },
    { text: 'Send an email to john@example.com about the meeting', category: 'Email' },
    { text: 'Organize my Downloads folder by file type', category: 'Files' },
    { text: 'Search YouTube for LangGraph tutorials', category: 'Browser' },
    { text: 'Create a Python script for data analysis', category: 'Code' },
  ];

  const [activeIdx, setActiveIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const t = setInterval(() => setActiveIdx(p => (p + 1) % examples.length), 3000);
    return () => clearInterval(t);
  }, []);

  const steps = selected ? [
    { label: 'Planning', desc: 'AI decomposes your task into executable steps', icon: Brain, status: 'done' },
    { label: 'Navigate', desc: 'Opens browser and navigates to target', icon: Globe, status: 'done' },
    { label: 'Execute', desc: 'Performs actions with precision', icon: Zap, status: 'active' },
    { label: 'Verify', desc: 'Validates the results automatically', icon: CheckCircle2, status: 'pending' },
  ] : [];

  return (
    <Section className="py-32 px-6" id="demo">
      <div className="max-w-6xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Live Demo</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Try it yourself</h2>
          <p className="mt-4 text-gray-400 max-w-lg mx-auto text-sm">
            Type a natural language command and watch ACO plan and execute the workflow in real time.
          </p>
        </FadeIn>

        <FadeIn className="max-w-2xl mx-auto">
          <div className="rounded-2xl border border-white/10 bg-[#111219]/80 backdrop-blur-xl overflow-hidden">
            <div className="p-4 border-b border-white/5">
              <div className="flex items-center gap-3 bg-white/[0.03] rounded-xl px-4 py-3 border border-white/5 focus-within:border-primary/30 transition-colors">
                <Sparkles size={16} className="text-primary shrink-0" />
                <input
                  type="text"
                  placeholder="Tell ACO what to do..."
                  value={selected || ''}
                  onChange={(e) => setSelected(e.target.value)}
                  className="flex-1 bg-transparent outline-none text-sm text-white placeholder-gray-500"
                />
                <button className="p-1.5 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors">
                  <Play size={14} className="fill-current" />
                </button>
              </div>
            </div>
            <div className="p-4 space-y-2">
              <p className="text-[10px] font-medium uppercase tracking-wider text-gray-500 mb-2">Examples</p>
              {examples.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setSelected(ex.text)}
                  className={`w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-all duration-200 ${
                    selected === ex.text
                      ? 'bg-primary/10 border border-primary/20 text-white'
                      : 'hover:bg-white/[0.03] text-gray-400 hover:text-gray-300 border border-transparent'
                  }`}
                >
                  <span>{ex.text}</span>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-gray-500">{ex.category}</span>
                </button>
              ))}
            </div>

            {selected && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="border-t border-white/5 p-4"
              >
                <p className="text-[10px] font-medium uppercase tracking-wider text-gray-500 mb-3">Execution Pipeline</p>
                <div className="space-y-2">
                  {steps.map((s, i) => {
                    const Icon = s.icon;
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.15 }}
                        className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.02]"
                      >
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                          s.status === 'done' ? 'bg-accent/10 text-accent' :
                          s.status === 'active' ? 'bg-primary/10 text-primary animate-pulse' :
                          'bg-white/5 text-gray-500'
                        }`}>
                          {s.status === 'done' ? <Check size={14} /> : <Icon size={14} />}
                        </div>
                        <div className="flex-1">
                          <p className="text-xs font-medium text-white">{s.label}</p>
                          <p className="text-[10px] text-gray-500">{s.desc}</p>
                        </div>
                        {s.status === 'active' && (
                          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                        )}
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </div>
        </FadeIn>
      </div>
    </Section>
  );
}

/* ─── FEATURES ─── */
function Features() {
  const features = [
    { icon: Globe, title: 'Browser Automation', desc: 'Navigate, click, fill forms, scrape content. Full Playwright-powered browser control.', color: 'text-blue-400', bg: 'bg-blue-400/10' },
    { icon: Monitor, title: 'Desktop Automation', desc: 'Click, type, drag, and interact with native desktop applications.', color: 'text-green-400', bg: 'bg-green-400/10' },
    { icon: Terminal, title: 'Terminal Commands', desc: 'Execute shell commands, scripts, and system operations safely.', color: 'text-amber-400', bg: 'bg-amber-400/10' },
    { icon: FileText, title: 'File Management', desc: 'Create, read, write, search, and organize files across your system.', color: 'text-cyan-400', bg: 'bg-cyan-400/10' },
    { icon: Eye, title: 'Vision Agent', desc: 'See and understand your screen. OCR, element detection, and visual reasoning.', color: 'text-purple-400', bg: 'bg-purple-400/10' },
    { icon: Brain, title: 'Workflow Planning', desc: 'AI-powered task decomposition. Translates goals into executable multi-step workflows.', color: 'text-pink-400', bg: 'bg-pink-400/10' },
    { icon: RefreshCw, title: 'Recovery Engine', desc: 'Automatically detects and recovers from failures. Self-healing workflows.', color: 'text-orange-400', bg: 'bg-orange-400/10' },
    { icon: CheckCircle2, title: 'Verification Engine', desc: 'Validates every step. Ensures actions produce expected results before proceeding.', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
    { icon: Puzzle, title: 'Plugin SDK', desc: 'Extend ACO with custom agents and capabilities. Build your own integrations.', color: 'text-indigo-400', bg: 'bg-indigo-400/10' },
    { icon: Database, title: 'Memory', desc: 'Persistent context across sessions. ACO remembers your preferences and history.', color: 'text-teal-400', bg: 'bg-teal-400/10' },
    { icon: Clock, title: 'Scheduler', desc: 'Schedule recurring tasks and automations. Set it and forget it.', color: 'text-sky-400', bg: 'bg-sky-400/10' },
    { icon: Layers, title: 'Multi-Agent System', desc: 'Specialized agents collaborate. Browser, desktop, terminal, vision, and file agents.', color: 'text-rose-400', bg: 'bg-rose-400/10' },
    { icon: MessageSquare, title: 'Natural Language', desc: 'Describe what you want in plain English. No scripting or configuration required.', color: 'text-violet-400', bg: 'bg-violet-400/10' },
    { icon: Server, title: 'Local AI Support', desc: 'Run entirely on your machine. No data leaves your computer with Ollama integration.', color: 'text-lime-400', bg: 'bg-lime-400/10' },
    { icon: Bot, title: 'Ollama Integration', desc: 'First-class support for local LLMs. Qwen, LLaMA, Mistral, and more.', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    { icon: Cpu, title: 'Multi Provider AI', desc: 'Switch between OpenAI, Claude, Gemini, Ollama. Use the best model for each task.', color: 'text-fuchsia-400', bg: 'bg-fuchsia-400/10' },
  ];

  return (
    <Section className="py-32 px-6" id="features">
      <div className="max-w-6xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Capabilities</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Everything you need</h2>
          <p className="mt-4 text-gray-400 max-w-lg mx-auto text-sm">
            A complete autonomous operator with specialized agents for every computing task.
          </p>
        </FadeIn>

        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="group p-5 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/10 transition-all duration-300"
              >
                <div className={`w-10 h-10 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
                  <Icon size={18} className={f.color} />
                </div>
                <h3 className="text-sm font-semibold text-white mb-1.5">{f.title}</h3>
                <p className="text-[12px] text-gray-500 leading-relaxed">{f.desc}</p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </Section>
  );
}

/* ─── HOW IT WORKS ─── */
function HowItWorks() {
  const steps = [
    { num: '01', title: 'Describe your task', desc: 'Tell ACO what you want in natural language.', icon: MessageSquare, color: 'text-blue-400' },
    { num: '02', title: 'AI plans the workflow', desc: 'The planner decomposes your goal into executable steps.', icon: Brain, color: 'text-purple-400' },
    { num: '03', title: 'Agents execute', desc: 'Specialized agents handle browser, desktop, terminal, and files.', icon: Zap, color: 'text-amber-400' },
    { num: '04', title: 'Verification validates', desc: 'Each step is verified for correctness before proceeding.', icon: CheckCircle2, color: 'text-green-400' },
    { num: '05', title: 'Recovery fixes failures', desc: 'If something fails, the recovery engine automatically retries.', icon: RefreshCw, color: 'text-orange-400' },
    { num: '06', title: 'Task completes', desc: 'Results are delivered with full execution history.', icon: Rocket, color: 'text-primary' },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-3xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">How It Works</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">From intent to execution</h2>
        </FadeIn>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-8 bottom-8 w-px bg-gradient-to-b from-primary/40 via-primary/20 to-transparent" />

          <div className="space-y-1">
            {steps.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-start gap-5 py-4 group"
                >
                  <div className="relative z-10 w-10 h-10 rounded-xl bg-[#111219] border border-white/10 flex items-center justify-center shrink-0 group-hover:border-primary/30 transition-colors">
                    <Icon size={16} className={s.color} />
                  </div>
                  <div className="pt-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-[10px] font-mono text-gray-600">{s.num}</span>
                      <h3 className="text-sm font-semibold text-white">{s.title}</h3>
                    </div>
                    <p className="text-[13px] text-gray-500">{s.desc}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ─── ARCHITECTURE ─── */
function Architecture() {
  const layers = [
    { label: 'Frontend', sub: 'Next.js + TypeScript', icon: Code2, color: 'text-blue-400' },
    { label: 'API Layer', sub: 'FastAPI + WebSocket', icon: Server, color: 'text-green-400' },
    { label: 'AI Planner', sub: 'LangGraph + Ollama', icon: Brain, color: 'text-purple-400' },
    { label: 'Workflow Engine', sub: 'State Machine', icon: Workflow, color: 'text-amber-400' },
    { label: 'Agent Dispatcher', sub: 'Multi-Agent Router', icon: Bot, color: 'text-pink-400' },
  ];

  const agents = [
    { icon: Globe, label: 'Browser', color: 'text-blue-400' },
    { icon: Monitor, label: 'Desktop', color: 'text-green-400' },
    { icon: Terminal, label: 'Terminal', color: 'text-amber-400' },
    { icon: Eye, label: 'Vision', color: 'text-purple-400' },
    { icon: FileText, label: 'Files', color: 'text-cyan-400' },
  ];

  const postSteps = [
    { label: 'Verification', icon: CheckCircle2, color: 'text-green-400' },
    { label: 'Recovery', icon: RefreshCw, color: 'text-orange-400' },
    { label: 'Completed', icon: Rocket, color: 'text-primary' },
  ];

  return (
    <Section className="py-32 px-6" id="architecture">
      <div className="max-w-4xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Architecture</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Built for reliability</h2>
          <p className="mt-4 text-gray-400 max-w-lg mx-auto text-sm">
            A layered architecture designed for extensibility, fault tolerance, and performance.
          </p>
        </FadeIn>

        <FadeIn>
          <div className="relative p-8 rounded-3xl border border-white/5 bg-white/[0.01]">
            {/* Main pipeline */}
            <div className="space-y-3">
              {layers.map((l, i) => {
                const Icon = l.icon;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.08 }}
                    className="flex items-center gap-4 px-5 py-3 rounded-xl border border-white/5 bg-white/[0.02] hover:border-white/10 transition-colors"
                  >
                    <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center ${l.color}`}>
                      <Icon size={16} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{l.label}</p>
                      <p className="text-[11px] text-gray-500">{l.sub}</p>
                    </div>
                    {i < layers.length - 1 && (
                      <ChevronDown size={14} className="text-gray-600" />
                    )}
                  </motion.div>
                );
              })}
            </div>

            {/* Agent grid */}
            <div className="mt-4 flex items-center justify-center gap-3">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider shrink-0">Agent Pool</span>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            </div>
            <div className="mt-4 grid grid-cols-5 gap-3">
              {agents.map((a, i) => {
                const Icon = a.icon;
                return (
                  <motion.div
                    key={i}
                    whileHover={{ y: -2 }}
                    className="flex flex-col items-center gap-2 p-3 rounded-xl border border-white/5 bg-white/[0.02] hover:border-white/10 transition-all"
                  >
                    <Icon size={18} className={a.color} />
                    <span className="text-[11px] text-gray-400">{a.label}</span>
                  </motion.div>
                );
              })}
            </div>

            {/* Post pipeline */}
            <div className="mt-4 flex items-center justify-center gap-3">
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider shrink-0">Post-Processing</span>
              <div className="h-px flex-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            </div>
            <div className="mt-4 space-y-2">
              {postSteps.map((s, i) => {
                const Icon = s.icon;
                return (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-white/5 bg-white/[0.02]">
                    <Icon size={14} className={s.color} />
                    <span className="text-xs font-medium text-white">{s.label}</span>
                    {i < postSteps.length - 1 && <ChevronDown size={12} className="text-gray-600 ml-auto" />}
                  </div>
                );
              })}
            </div>
          </div>
        </FadeIn>
      </div>
    </Section>
  );
}

/* ─── COMPARISON TABLE ─── */
function Comparison() {
  const features = [
    'Natural Language',
    'Computer Control',
    'Desktop Automation',
    'Browser Automation',
    'Verification',
    'Recovery',
    'Multi Agent',
    'Workflow Planning',
    'Local AI',
    'Privacy',
    'Plugin Support',
  ];

  const cols = [
    { name: 'Manual', values: [true, true, false, false, false, false, false, false, false, true, false] },
    { name: 'Traditional RPA', values: [false, false, true, true, false, false, false, false, false, false, false] },
    { name: 'ChatGPT', values: [true, false, false, false, false, false, false, false, false, false, false] },
    { name: 'ACO', values: [true, true, true, true, true, true, true, true, true, true, true], highlight: true },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Why ACO</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">The difference</h2>
        </FadeIn>

        <FadeIn>
          <div className="overflow-x-auto rounded-2xl border border-white/5">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-left py-4 px-5 text-gray-500 font-medium text-xs">Feature</th>
                  {cols.map((c, i) => (
                    <th key={i} className={`py-4 px-5 text-center font-medium text-xs ${
                      c.highlight ? 'text-primary' : 'text-gray-500'
                    }`}>
                      {c.highlight && <span className="block text-[9px] text-primary/60 mb-0.5">★</span>}
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {features.map((f, fi) => (
                  <tr key={fi} className="border-b border-white/[0.03] last:border-0">
                    <td className="py-3 px-5 text-gray-400 text-xs">{f}</td>
                    {cols.map((c, ci) => (
                      <td key={ci} className="py-3 px-5 text-center">
                        {c.values[fi] ? (
                          <Check size={14} className={`mx-auto ${c.highlight ? 'text-primary' : 'text-accent'}`} />
                        ) : (
                          <X size={14} className="mx-auto text-gray-700" />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </FadeIn>
      </div>
    </Section>
  );
}

/* ─── SECURITY ─── */
function Security() {
  const items = [
    { icon: Shield, title: 'Permission Guard', desc: 'Every action requires explicit user approval. You stay in control.' },
    { icon: Lock, title: 'Per-User Isolation', desc: 'Each user has their own isolated workspace. Data never crosses boundaries.' },
    { icon: Monitor, title: 'Local Execution', desc: 'Everything runs on your machine. No cloud dependency required.' },
    { icon: Fingerprint, title: 'JWT Authentication', desc: 'Secure token-based authentication with role-based access control.' },
    { icon: Scan, title: 'Browser Sandboxing', desc: 'Each browser session runs in an isolated profile with controlled permissions.' },
    { icon: RefreshCw, title: 'Recovery Engine', desc: 'Automatic failure detection and self-healing. Workflows recover gracefully.' },
    { icon: CheckCircle2, title: 'Verification Engine', desc: 'Every action is verified for expected outcomes before proceeding.' },
    { icon: Zap, title: 'Safe Execution', desc: 'Destructive actions are gated. Read-only operations are auto-approved.' },
  ];

  return (
    <Section className="py-32 px-6" id="security">
      <div className="max-w-6xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Security</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Built to be safe</h2>
          <p className="mt-4 text-gray-400 max-w-lg mx-auto text-sm">
            Security is not an afterthought. Every layer is designed with privacy and safety in mind.
          </p>
        </FadeIn>

        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                className="p-5 rounded-2xl border border-white/5 bg-white/[0.02] hover:border-white/10 transition-all duration-300"
              >
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                  <Icon size={18} className="text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-white mb-1.5">{item.title}</h3>
                <p className="text-[12px] text-gray-500 leading-relaxed">{item.desc}</p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </Section>
  );
}

/* ─── TECHNOLOGY ─── */
function Technology() {
  const techs = [
    { name: 'FastAPI', desc: 'Backend API' },
    { name: 'LangGraph', desc: 'AI Workflows' },
    { name: 'Playwright', desc: 'Browser Automation' },
    { name: 'Next.js', desc: 'Frontend' },
    { name: 'MongoDB', desc: 'Database' },
    { name: 'Redis', desc: 'Caching' },
    { name: 'Ollama', desc: 'Local AI' },
    { name: 'TypeScript', desc: 'Type Safety' },
    { name: 'Tailwind', desc: 'Styling' },
    { name: 'Framer Motion', desc: 'Animations' },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Technology</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Powered by the best</h2>
        </FadeIn>

        <motion.div variants={stagger} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {techs.map((t, i) => (
            <motion.div
              key={i}
              variants={fadeUp}
              whileHover={{ y: -2, scale: 1.02 }}
              className="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:border-white/10 transition-all text-center"
            >
              <p className="text-sm font-semibold text-white">{t.name}</p>
              <p className="text-[10px] text-gray-500 mt-1">{t.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </Section>
  );
}

/* ─── PERFORMANCE ─── */
function Performance() {
  const stats = [
    { value: 94, suffix: '%', label: 'Workflow Success', icon: CheckCircle2, color: 'text-accent' },
    { value: 87, suffix: '%', label: 'Recovery Rate', icon: RefreshCw, color: 'text-blue-400' },
    { value: 96, suffix: '%', label: 'Verification Accuracy', icon: Shield, color: 'text-purple-400' },
    { value: 12, suffix: 's', label: 'Avg Runtime', icon: Timer, color: 'text-amber-400' },
    { value: 3, suffix: '', label: 'Active Workers', icon: Layers, color: 'text-green-400' },
    { value: 5, suffix: '+', label: 'Browser Sessions', icon: Globe, color: 'text-cyan-400' },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Performance</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Proven results</h2>
        </FadeIn>

        <motion.div variants={stagger} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {stats.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                className="p-5 rounded-2xl border border-white/5 bg-white/[0.02] text-center"
              >
                <Icon size={18} className={`${s.color} mx-auto mb-3`} />
                <p className="text-3xl font-bold text-white">
                  {s.value}<span className="text-lg text-gray-500">{s.suffix}</span>
                </p>
                <p className="text-[11px] text-gray-500 mt-1">{s.label}</p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </Section>
  );
}

/* ─── ROADMAP ─── */
function Roadmap() {
  const versions = [
    {
      version: 'v1',
      title: 'Foundation',
      status: 'current',
      items: [
        { text: 'Browser Automation', done: true },
        { text: 'Desktop Automation', done: true },
        { text: 'Terminal Commands', done: true },
        { text: 'File Management', done: true },
        { text: 'Plugin SDK', done: true },
      ]
    },
    {
      version: 'v2',
      title: 'Expansion',
      status: 'next',
      items: [
        { text: 'Plugin Marketplace', done: false },
        { text: 'Cloud Sync', done: false },
        { text: 'Voice Commands', done: false },
        { text: 'Multi-Model Routing', done: false },
      ]
    },
    {
      version: 'v3',
      title: 'Enterprise',
      status: 'future',
      items: [
        { text: 'Enterprise Edition', done: false },
        { text: 'Multi-User Teams', done: false },
        { text: 'Remote Agents', done: false },
        { text: 'Admin Dashboard', done: false },
      ]
    },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-5xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">Roadmap</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">What's next</h2>
        </FadeIn>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {versions.map((v, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`p-6 rounded-2xl border transition-all ${
                v.status === 'current' ? 'border-primary/20 bg-primary/[0.03]' :
                v.status === 'next' ? 'border-white/10 bg-white/[0.02]' :
                'border-white/5 bg-white/[0.01]'
              }`}
            >
              <div className="flex items-center gap-2 mb-4">
                <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                  v.status === 'current' ? 'bg-primary/10 text-primary' :
                  v.status === 'next' ? 'bg-white/5 text-gray-300' :
                  'bg-white/5 text-gray-500'
                }`}>{v.version}</span>
                <span className="text-sm font-semibold text-white">{v.title}</span>
                {v.status === 'current' && <span className="ml-auto text-[9px] text-primary font-medium">LIVE</span>}
              </div>
              <div className="space-y-2.5">
                {v.items.map((item, j) => (
                  <div key={j} className="flex items-center gap-2.5">
                    {item.done ? (
                      <CheckCircle2 size={14} className="text-accent shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-white/10 shrink-0" />
                    )}
                    <span className={`text-xs ${item.done ? 'text-gray-300' : 'text-gray-500'}`}>{item.text}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

/* ─── FAQ ─── */
function FAQ() {
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const faqs = [
    { q: 'What is ACO?', a: 'ACO (Autonomous Computer Operator) is an AI-powered agent that understands natural language commands and executes real computer actions — browsing the web, managing files, running terminal commands, and interacting with desktop applications.' },
    { q: 'How does it work?', a: 'ACO uses a multi-agent architecture. When you give it a task, the AI planner decomposes it into a workflow. Specialized agents (browser, desktop, terminal, file, vision) execute each step. A verification engine validates results, and a recovery engine handles failures automatically.' },
    { q: 'Does it support local models?', a: 'Yes. ACO has first-class support for Ollama, allowing you to run entirely on your machine with models like Qwen, LLaMA, and Mistral. Your data never leaves your computer.' },
    { q: 'Can I use Ollama?', a: 'Absolutely. Ollama is a first-class provider in ACO. Simply install Ollama, pull your preferred model, and ACO will use it for planning and execution.' },
    { q: 'Is my data private?', a: 'Yes. ACO runs locally on your machine. All data stays on your device. With Ollama integration, even AI inference happens locally. No data is sent to external servers unless you explicitly choose a cloud provider.' },
    { q: 'Can I build plugins?', a: 'Yes. ACO includes a Plugin SDK that lets you create custom agents, capabilities, and integrations. The plugin system is designed to be extensible and secure.' },
    { q: 'Does it support Windows?', a: 'ACO is built on Windows and supports Windows, macOS, and Linux. It uses Playwright for cross-browser automation and native APIs for desktop interaction.' },
  ];

  return (
    <Section className="py-32 px-6">
      <div className="max-w-2xl mx-auto">
        <FadeIn className="text-center mb-16">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">FAQ</p>
          <h2 className="text-3xl md:text-5xl font-bold text-white">Questions & answers</h2>
        </FadeIn>

        <div className="space-y-2">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden"
            >
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-sm font-medium text-white">{faq.q}</span>
                <ChevronDown size={14} className={`text-gray-500 transition-transform duration-200 shrink-0 ml-4 ${
                  openIdx === i ? 'rotate-180' : ''
                }`} />
              </button>
              <AnimatePresence>
                {openIdx === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-5 pb-4 text-[13px] text-gray-400 leading-relaxed">{faq.a}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>
    </Section>
  );
}

/* ─── CTA ─── */
function CTA() {
  return (
    <section className="py-32 px-6">
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative p-12 rounded-3xl border border-white/5 bg-white/[0.02] overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to automate?
            </h2>
            <p className="text-gray-400 text-sm mb-8 max-w-md mx-auto">
              Start building autonomous workflows today. Open source, local-first, and free.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <a href="/login"
                className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200 shadow-lg shadow-primary/25 hover:shadow-primary/40">
                Get Started <ArrowRight size={16} />
              </a>
              <a href="https://github.com" target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all border border-white/10">
                <Github size={16} /> GitHub
              </a>
              <a href="#"
                className="flex items-center gap-2 text-gray-400 hover:text-white px-6 py-3 rounded-xl text-sm font-medium transition-all border border-white/5 hover:border-white/10">
                Documentation
              </a>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ─── FOOTER ─── */
function Footer() {
  return (
    <footer className="border-t border-white/5 py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-primary/20 flex items-center justify-center">
                <Cpu size={14} className="text-primary" />
              </div>
              <span className="font-bold text-sm text-white">ACO</span>
            </div>
            <p className="text-[12px] text-gray-500 leading-relaxed">
              Your Autonomous Computer Operator.
              <br />Think Less. Execute More.
            </p>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Product</h4>
            <div className="space-y-2">
              <a href="#features" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Features</a>
              <a href="#architecture" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Architecture</a>
              <a href="#security" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Security</a>
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Roadmap</a>
            </div>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Developers</h4>
            <div className="space-y-2">
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Documentation</a>
              <a href="https://github.com" className="block text-[12px] text-gray-500 hover:text-white transition-colors">GitHub</a>
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Plugin SDK</a>
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">API Reference</a>
            </div>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Legal</h4>
            <div className="space-y-2">
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">License (MIT)</a>
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Privacy</a>
              <a href="#" className="block text-[12px] text-gray-500 hover:text-white transition-colors">Contact</a>
            </div>
          </div>
        </div>

        <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-gray-600">
            &copy; 2026 ACO. Built with
            <span className="text-gray-500"> FastAPI</span>,
            <span className="text-gray-500"> LangGraph</span>,
            <span className="text-gray-500"> Playwright</span>,
            <span className="text-gray-500"> Next.js</span>,
            <span className="text-gray-500"> MongoDB</span>, and
            <span className="text-gray-500"> Tailwind</span>.
          </p>
          <div className="flex items-center gap-4">
            <a href="https://github.com" className="text-gray-600 hover:text-white transition-colors">
              <Github size={14} />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ─── MAIN PAGE ─── */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#09090B] text-white overflow-x-hidden">
      <Navbar />
      <Hero />
      <LiveDemo />
      <Features />
      <HowItWorks />
      <Architecture />
      <Comparison />
      <Security />
      <Technology />
      <Performance />
      <Roadmap />
      <FAQ />
      <CTA />
      <Footer />
    </div>
  );
}
