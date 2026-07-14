'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, useInView, AnimatePresence } from 'framer-motion';
import {
  Cpu, Globe, Terminal, Monitor, FileText, Eye, ArrowRight, Check,
  ChevronDown, Menu, XIcon, Shield, Lock, Fingerprint, Scan, Zap,
  Brain, Layers, RefreshCw, CheckCircle2, MessageSquare, Rocket,
  Server, Bot, Puzzle, Database, Clock, Code2, Workflow,
  ChevronRight, Sparkles
} from 'lucide-react';

import type { Variants } from 'framer-motion';

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } }
};

const stagger: Variants = {
  visible: { transition: { staggerChildren: 0.06 } }
};

function useSectionInView(threshold = 0.1) {
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

function SectionHeading({ label, title, desc }: { label: string; title: string; desc?: string }) {
  return (
    <FadeIn className="text-center mb-16">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-primary mb-3">{label}</p>
      <h2 className="text-3xl md:text-5xl font-bold text-[#e8e8ec]">{title}</h2>
      {desc && <p className="mt-4 text-gray-500 max-w-lg mx-auto text-sm">{desc}</p>}
    </FadeIn>
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
  ];

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-[#0c0c10] border-b border-[#1e1f2a]' : 'bg-transparent'
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Cpu size={16} className="text-primary" />
          </div>
          <span className="font-bold text-base text-[#e8e8ec]">ACO</span>
        </a>

        <nav className="hidden md:flex items-center gap-8">
          {links.map(l => (
            <a key={l.href} href={l.href} className="text-[13px] text-gray-500 hover:text-[#e8e8ec] transition-colors duration-200">
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <a href="/login"
            className="text-[13px] text-gray-500 hover:text-[#e8e8ec] transition-colors px-3 py-1.5">
            Sign In
          </a>
          <a href="/login"
            className="text-[13px] font-medium bg-primary hover:bg-primary-hover text-white px-4 py-1.5 rounded-lg transition-all duration-200">
            Get Started
          </a>
        </div>

        <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden text-gray-500 hover:text-[#e8e8ec]">
          {mobileOpen ? <XIcon size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-[#0c0c10] border-b border-[#1e1f2a] overflow-hidden"
          >
            <div className="px-6 py-4 space-y-3">
              {links.map(l => (
                <a key={l.href} href={l.href} onClick={() => setMobileOpen(false)}
                  className="block text-sm text-gray-500 hover:text-[#e8e8ec] transition-colors py-2">
                  {l.label}
                </a>
              ))}
              <div className="pt-3 border-t border-[#1e1f2a] flex flex-col gap-2">
                <a href="/login" className="text-sm text-gray-500 hover:text-[#e8e8ec] py-2">Sign In</a>
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
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center pt-24 pb-20 px-6 overflow-hidden bg-[#0c0c10]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-center max-w-4xl mx-auto relative z-10"
      >
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#272836] bg-[#14151c] mb-8"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="text-[11px] font-medium text-primary">v1.0 — Now Available</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-[#e8e8ec] leading-[1.05]"
        >
          Your Autonomous
          <br />
          <span className="text-[#e8e8ec]">Computer Operator</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="mt-6 text-base md:text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed"
        >
          An autonomous AI agent that understands goals, plans workflows, and operates your computer securely.
          Browse websites, automate tasks, manage files, and execute commands — all from natural language.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-4"
        >
          <a href="/login"
            className="flex items-center gap-2 bg-primary hover:opacity-90 text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200">
            Get Started <ArrowRight size={16} />
          </a>
          <a href="#features"
            className="flex items-center gap-2 bg-[#14151c] hover:bg-[#181922] text-[#e8e8ec] px-6 py-3 rounded-xl text-sm font-medium transition-all duration-200 border border-[#1e1f2a] hover:border-[#272836]">
            Learn More
          </a>
        </motion.div>

        {/* Static terminal prompt */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-16 max-w-xl mx-auto"
        >
          <div className="rounded-2xl border border-[#1e1f2a] bg-[#14151c] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1e1f2a]">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-gray-600" />
                <div className="w-2.5 h-2.5 rounded-full bg-gray-600" />
                <div className="w-2.5 h-2.5 rounded-full bg-gray-600" />
              </div>
              <span className="text-[10px] text-gray-600 ml-2 font-mono">ACO Terminal</span>
            </div>
            <div className="p-5 font-mono text-sm">
              <div className="flex items-center gap-2 text-gray-600 mb-3">
                <Sparkles size={12} className="text-primary" />
                <span className="text-[11px]">Tell ACO what to do...</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-primary">$</span>
                <span className="text-[#e8e8ec]">Summarize today's AI news</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#181922] border border-[#272836] text-gray-400 text-[10px]">
                  <Globe size={10} className="text-gray-400" />
                  Browse web
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#181922] border border-[#272836] text-gray-400 text-[10px]">
                  <MailIcon size={10} />
                  Send email
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#181922] border border-[#272836] text-gray-400 text-[10px]">
                  <FileText size={10} />
                  Organize files
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Agent badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="mt-10 flex flex-wrap justify-center gap-3"
        >
          {[
            { icon: Globe, label: 'Browser' },
            { icon: Monitor, label: 'Desktop' },
            { icon: Terminal, label: 'Terminal' },
            { icon: Eye, label: 'Vision' },
            { icon: FileText, label: 'Files' },
          ].map((a) => (
            <div
              key={a.label}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#1e1f2a] bg-[#14151c] text-[11px] text-gray-500"
            >
              <a.icon size={12} className="text-gray-400" />
              {a.label}
            </div>
          ))}
        </motion.div>
      </motion.div>
    </section>
  );
}

function MailIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}

/* ─── FEATURES ─── */
function Features() {
  const features = [
    { icon: Globe, title: 'Browser Automation', desc: 'Navigate, click, fill forms, scrape content. Full Playwright-powered browser control.' },
    { icon: Monitor, title: 'Desktop Automation', desc: 'Click, type, drag, and interact with native desktop applications.' },
    { icon: Terminal, title: 'Terminal Commands', desc: 'Execute shell commands, scripts, and system operations safely.' },
    { icon: FileText, title: 'File Management', desc: 'Create, read, write, search, and organize files across your system.' },
    { icon: Eye, title: 'Vision Agent', desc: 'See and understand your screen. OCR, element detection, and visual reasoning.' },
    { icon: Brain, title: 'Workflow Planning', desc: 'AI-powered task decomposition. Translates goals into executable multi-step workflows.' },
    { icon: RefreshCw, title: 'Recovery Engine', desc: 'Automatically detects and recovers from failures. Self-healing workflows.' },
    { icon: CheckCircle2, title: 'Verification Engine', desc: 'Validates every step. Ensures actions produce expected results before proceeding.' },
    { icon: Puzzle, title: 'Plugin SDK', desc: 'Extend ACO with custom agents and capabilities. Build your own integrations.' },
    { icon: Database, title: 'Memory', desc: 'Persistent context across sessions. ACO remembers your preferences and history.' },
    { icon: Clock, title: 'Scheduler', desc: 'Schedule recurring tasks and automations. Set it and forget it.' },
    { icon: Layers, title: 'Multi-Agent System', desc: 'Specialized agents collaborate. Browser, desktop, terminal, vision, and file agents.' },
    { icon: MessageSquare, title: 'Natural Language', desc: 'Describe what you want in plain English. No scripting or configuration required.' },
    { icon: Server, title: 'Local AI Support', desc: 'Run entirely on your machine. No data leaves your computer with Ollama integration.' },
    { icon: Bot, title: 'Ollama Integration', desc: 'First-class support for local LLMs. Qwen, LLaMA, Mistral, and more.' },
    { icon: Cpu, title: 'Multi Provider AI', desc: 'Switch between OpenAI, Claude, Gemini, Ollama. Use the best model for each task.' },
  ];

  return (
    <Section className="py-32 px-6" id="features">
      <div className="max-w-6xl mx-auto">
        <SectionHeading label="Capabilities" title="Everything you need" desc="A complete autonomous operator with specialized agents for every computing task." />

        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                className="p-5 rounded-2xl border border-[#1e1f2a] bg-[#14151c] hover:bg-[#181922] hover:border-[#272836] transition-all duration-300"
              >
                <div className="w-10 h-10 rounded-xl bg-[#181922] border border-[#272836] flex items-center justify-center mb-4">
                  <Icon size={18} className="text-gray-400" />
                </div>
                <h3 className="text-sm font-semibold text-[#e8e8ec] mb-1.5">{f.title}</h3>
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
    { num: '01', title: 'Describe your task', desc: 'Tell ACO what you want in natural language.', icon: MessageSquare },
    { num: '02', title: 'AI plans the workflow', desc: 'The planner decomposes your goal into executable steps.', icon: Brain },
    { num: '03', title: 'Agents execute', desc: 'Specialized agents handle browser, desktop, terminal, and files.', icon: Zap },
    { num: '04', title: 'Verification validates', desc: 'Each step is verified for correctness before proceeding.', icon: CheckCircle2 },
    { num: '05', title: 'Recovery fixes failures', desc: 'If something fails, the recovery engine automatically retries.', icon: RefreshCw },
    { num: '06', title: 'Task completes', desc: 'Results are delivered with full execution history.', icon: Rocket },
  ];

  return (
    <Section className="py-32 px-6 bg-[#101118]">
      <div className="max-w-3xl mx-auto">
        <SectionHeading label="How It Works" title="From intent to execution" />

        <div className="relative">
          <div className="absolute left-[19px] top-8 bottom-8 w-px bg-[#1e1f2a]" />

          <div className="space-y-1">
            {steps.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -16 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="flex items-start gap-5 py-4 group"
                >
                  <div className="relative z-10 w-10 h-10 rounded-xl bg-[#14151c] border border-[#1e1f2a] flex items-center justify-center shrink-0 group-hover:border-[#272836] transition-colors">
                    <Icon size={16} className="text-gray-400" />
                  </div>
                  <div className="pt-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-[10px] font-mono text-gray-600">{s.num}</span>
                      <h3 className="text-sm font-semibold text-[#e8e8ec]">{s.title}</h3>
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
    { label: 'Frontend', sub: 'Next.js + TypeScript', icon: Code2 },
    { label: 'API Layer', sub: 'FastAPI + WebSocket', icon: Server },
    { label: 'AI Planner', sub: 'LangGraph + Ollama', icon: Brain },
    { label: 'Workflow Engine', sub: 'State Machine', icon: Workflow },
    { label: 'Agent Dispatcher', sub: 'Multi-Agent Router', icon: Bot },
  ];

  const agents = [
    { icon: Globe, label: 'Browser' },
    { icon: Monitor, label: 'Desktop' },
    { icon: Terminal, label: 'Terminal' },
    { icon: Eye, label: 'Vision' },
    { icon: FileText, label: 'Files' },
  ];

  const postSteps = [
    { label: 'Verification', icon: CheckCircle2 },
    { label: 'Recovery', icon: RefreshCw },
    { label: 'Completed', icon: Rocket },
  ];

  return (
    <Section className="py-32 px-6" id="architecture">
      <div className="max-w-4xl mx-auto">
        <SectionHeading label="Architecture" title="Built for reliability" desc="A layered architecture designed for extensibility, fault tolerance, and performance." />

        <FadeIn>
          <div className="relative p-8 rounded-3xl border border-[#1e1f2a] bg-[#14151c]">
            <div className="space-y-3">
              {layers.map((l, i) => {
                const Icon = l.icon;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -16 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.08 }}
                    className="flex items-center gap-4 px-5 py-3 rounded-xl border border-[#1e1f2a] bg-[#101118] hover:border-[#272836] transition-colors"
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#181922] flex items-center justify-center text-gray-400">
                      <Icon size={16} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-[#e8e8ec]">{l.label}</p>
                      <p className="text-[11px] text-gray-500">{l.sub}</p>
                    </div>
                    {i < layers.length - 1 && (
                      <ChevronDown size={14} className="text-gray-600" />
                    )}
                  </motion.div>
                );
              })}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-[#1e1f2a]" />
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider shrink-0">Agent Pool</span>
              <div className="h-px flex-1 bg-[#1e1f2a]" />
            </div>

            <div className="mt-4 grid grid-cols-5 gap-3">
              {agents.map((a, i) => {
                const Icon = a.icon;
                return (
                  <motion.div
                    key={i}
                    className="flex flex-col items-center gap-2 p-3 rounded-xl border border-[#1e1f2a] bg-[#101118] hover:border-[#272836] hover:bg-[#181922] transition-all"
                  >
                    <Icon size={18} className="text-gray-400" />
                    <span className="text-[11px] text-gray-500">{a.label}</span>
                  </motion.div>
                );
              })}
            </div>

            <div className="mt-4 flex items-center gap-3">
              <div className="h-px flex-1 bg-[#1e1f2a]" />
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider shrink-0">Post-Processing</span>
              <div className="h-px flex-1 bg-[#1e1f2a]" />
            </div>

            <div className="mt-4 space-y-2">
              {postSteps.map((s, i) => {
                const Icon = s.icon;
                return (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-[#1e1f2a] bg-[#101118]">
                    <Icon size={14} className="text-gray-400" />
                    <span className="text-xs font-medium text-[#e8e8ec]">{s.label}</span>
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
    <Section className="py-32 px-6 bg-[#101118]" id="security">
      <div className="max-w-6xl mx-auto">
        <SectionHeading label="Security" title="Built to be safe" desc="Security is not an afterthought. Every layer is designed with privacy and safety in mind." />

        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={i}
                variants={fadeUp}
                className="p-5 rounded-2xl border border-[#1e1f2a] bg-[#14151c] hover:bg-[#181922] hover:border-[#272836] transition-all duration-300"
              >
                <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
                  <Icon size={18} className="text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-[#e8e8ec] mb-1.5">{item.title}</h3>
                <p className="text-[12px] text-gray-500 leading-relaxed">{item.desc}</p>
              </motion.div>
            );
          })}
        </motion.div>
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
        <SectionHeading label="FAQ" title="Questions & answers" />

        <div className="space-y-2">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              className="rounded-xl border border-[#1e1f2a] bg-[#14151c] overflow-hidden"
            >
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#181922] transition-colors"
              >
                <span className="text-sm font-medium text-[#e8e8ec]">{faq.q}</span>
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
                    <p className="px-5 pb-4 text-[13px] text-gray-500 leading-relaxed">{faq.a}</p>
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
    <section className="py-32 px-6 bg-[#101118]">
      <div className="max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative p-12 rounded-3xl border border-[#1e1f2a] bg-[#14151c]"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#e8e8ec] mb-4">
            Ready to automate?
          </h2>
          <p className="text-gray-500 text-sm mb-8 max-w-md mx-auto">
            Start building autonomous workflows today. Open source, local-first, and free.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href="/login"
              className="flex items-center gap-2 bg-primary hover:opacity-90 text-white px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200">
              Get Started <ArrowRight size={16} />
            </a>
            <a href="#features"
              className="flex items-center gap-2 bg-[#181922] hover:bg-[#1e1f2a] text-[#e8e8ec] px-6 py-3 rounded-xl text-sm font-medium transition-all border border-[#272836]">
              Learn More
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ─── FOOTER ─── */
function Footer() {
  return (
    <footer className="border-t border-[#1e1f2a] py-12 px-6 bg-[#0c0c10]">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                <Cpu size={14} className="text-primary" />
              </div>
              <span className="font-bold text-sm text-[#e8e8ec]">ACO</span>
            </div>
            <p className="text-[12px] text-gray-500 leading-relaxed">
              Your Autonomous Computer Operator.
              <br />Think Less. Execute More.
            </p>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Product</h4>
            <div className="space-y-2">
              <a href="#features" className="block text-[12px] text-gray-500 hover:text-[#e8e8ec] transition-colors">Features</a>
              <a href="#architecture" className="block text-[12px] text-gray-500 hover:text-[#e8e8ec] transition-colors">Architecture</a>
              <a href="#security" className="block text-[12px] text-gray-500 hover:text-[#e8e8ec] transition-colors">Security</a>
            </div>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Getting Started</h4>
            <div className="space-y-2">
              <a href="/login" className="block text-[12px] text-gray-500 hover:text-[#e8e8ec] transition-colors">Sign In</a>
              <a href="#features" className="block text-[12px] text-gray-500 hover:text-[#e8e8ec] transition-colors">Features</a>
            </div>
          </div>
          <div>
            <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Legal</h4>
            <div className="space-y-2">
              <span className="block text-[12px] text-gray-600">MIT License</span>
            </div>
          </div>
        </div>

        <div className="border-t border-[#1e1f2a] pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-gray-600">
            &copy; 2026 ACO. Built with FastAPI, LangGraph, Playwright, Next.js, MongoDB, and Tailwind.
          </p>
        </div>
      </div>
    </footer>
  );
}

/* ─── MAIN PAGE ─── */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0c0c10] text-[#e8e8ec] overflow-x-hidden">
      <Navbar />
      <Hero />
      <Features />
      <HowItWorks />
      <Architecture />
      <Security />
      <FAQ />
      <CTA />
      <Footer />
    </div>
  );
}
