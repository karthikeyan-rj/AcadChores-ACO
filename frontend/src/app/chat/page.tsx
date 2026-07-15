'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Paperclip, Mic, Camera, Play, Loader2, CheckCircle2,
  XCircle, Globe, Terminal, Monitor, FileText, Eye, AlertTriangle,
  Shield, RefreshCw, Send, ArrowRight, X, Maximize2,
  Minimize2, MonitorPlay, Square
} from 'lucide-react';
import { cn, statusColor, statusBg, statusDot, formatDuration, formatRelativeTime } from '@/lib/utils';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useBackendHealth, useWebSocket } from '@/lib/hooks';
import { WorkflowGraph } from '@/components/workflow/WorkflowGraph';
import { StepDetails } from '@/components/workflow/StepDetails';
import { LiveConsole } from '@/components/execution/LiveConsole';
import { ExecutionPanel } from '@/components/execution/ExecutionPanel';
import { ExecutionTimeline } from '@/components/execution/ExecutionTimeline';
import { PermissionModal } from '@/components/modals/PermissionModal';
import { EmailDraftModal } from '@/components/modals/EmailDraftModal';
import { ResultDisplay } from '@/components/ui/ResultDisplay';

interface TaskStep { step_id: string; name: string; agent_type: string; action: string; parameters?: any; }
interface LogMessage { time: string; message: string; level: 'info' | 'warn' | 'error'; }
interface ChatMessage { role: 'user' | 'assistant'; content: string; time: string; }

const suggestions = [
  { text: 'Send email to user@domain.com about meeting tomorrow', icon: '📧', category: 'Email' },
  { text: 'Search YouTube for top 5 AI news and summarize', icon: '🎬', category: 'Research' },
  { text: 'Open terminal and run ping google.com 5 times', icon: '💻', category: 'Terminal' },
  { text: 'Find all PDF files on my desktop', icon: '📁', category: 'Files' },
  { text: 'Go to google.com and search for machine learning', icon: '🌐', category: 'Browser' },
  { text: 'Create a file on my desktop with meeting notes', icon: '📝', category: 'Files' },
];

export default function ChatPage() {
  const { token } = useAuth();
  const connected = useBackendHealth();

  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('Idle');
  const [plan, setPlan] = useState<TaskStep[]>([]);
  const [stepIdx, setStepIdx] = useState(-1);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [execId, setExecId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [showRecent, setShowRecent] = useState(false);
  const [consoleExpanded, setConsoleExpanded] = useState(true);

  const [perm, setPerm] = useState<any>(null);
  const [emailDraft, setEmailDraft] = useState<any>(null);
  const [editedSubj, setEditedSubj] = useState('');
  const [editedBody, setEditedBody] = useState('');
  const [pendingPrompt, setPendingPrompt] = useState('');

  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [lastUserPrompt, setLastUserPrompt] = useState('');

  const { connected: wsUp, lastEvent } = useWebSocket(execId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [stopping, setStopping] = useState(false);

  const addLog = useCallback((time: string, message: string, level: LogMessage['level'] = 'info') => {
    setLogs(p => [...p, { time, message, level }]);
  }, []);

  // --- Execution persistence across route changes ---
  // Save active execution_id to localStorage so we can restore it on remount
  useEffect(() => {
    if (execId && (status === 'Planning' || status === 'Executing' || status === 'Waiting')) {
      try { localStorage.setItem('aco_active_exec', execId); } catch {}
    } else if (['Completed', 'Failed', 'Cancelled'].includes(status) || status === 'Idle') {
      try { localStorage.removeItem('aco_active_exec'); } catch {}
    }
  }, [execId, status]);

  // Restore active execution on mount
  useEffect(() => {
    if (!token) return;
    const savedExecId = (() => { try { return localStorage.getItem('aco_active_exec'); } catch { return null; } })();
    if (!savedExecId) return;

    // Fetch execution status from backend
    api.getExecution(savedExecId, token).then((exec: any) => {
      if (exec && ['Executing', 'Planning', 'Waiting'].includes(exec.status)) {
        setExecId(savedExecId);
        setStatus(exec.status);
        if (exec.total_steps) setStepIdx(exec.current_step_index ?? 0);
        if (exec.title) setLastUserPrompt(exec.description || exec.title);
        // Fetch execution logs
        api.getExecutionLogs(savedExecId, token).then((logsData: any[]) => {
          if (Array.isArray(logsData)) {
            const restoredLogs = logsData.map((l: any) => ({
              time: l.created_at || '',
              message: l.logs || `${l.action}: ${l.status}`,
              level: l.status === 'failure' ? 'error' as const : 'info' as const,
            }));
            setLogs(restoredLogs);
          }
        }).catch(() => {});
      } else {
        try { localStorage.removeItem('aco_active_exec'); } catch {}
      }
    }).catch(() => {
      try { localStorage.removeItem('aco_active_exec'); } catch {}
    });
  }, [token]);

  const isChatMessage = (text: string): boolean => {
    const lower = text.toLowerCase().trim();
    const greetings = /^(hi|hello|hey|howdy|yo|hola|good\s*(morning|afternoon|evening)|namaste|vanakkam)\b/;
    const casual = /^(thanks|thank you|thx|bye|goodbye|see you|ok|okay|sure|cool|nice|great|awesome|lol|haha|yes|no|yep|nope|np|welcome|please|sorry)\b/;
    const chitchat = /(how are you|what('?s| is) (your name|up|going on)|who (are|r) you|what can you do|help me|what do you know)/;
    // System commands that look like questions but should be executed
    const systemQuery = /\b(disk\s*space|ipconfig|hostname|tasklist|running\s*process|system\s*(info|information)|memory|cpu|ram|whoami|date|time|path|environment|env\s*var|network|wifi|bluetooth|driver|service|port|firewall|registry|process|disk|drive|volume|partition|boot|startup|shutdown|restart|sleep|hibernate|lock|log\s*out|suspend|resume|cancel|abort|kill|terminate|force|format|del|delete|remove|erase|wipe|clean|purge|clear|empty|destroy|nuke|rm\s*-rf|rmdir|rd\s|move|rename|copy|xcopy|robocopy|mklink|junction|hardlink|symbolic|shortcut)\b/;
    const noActionWords = !/\b(open|send|search|create|write|run|execute|navigate|click|fill|delete|find|list|show|get|download|upload|install|compress|extract|summarize|read|play|pause|stop|close|copy|move|rename)\b/.test(lower);
    return (greetings.test(lower) || casual.test(lower) || chitchat.test(lower) || noActionWords) && !systemQuery.test(lower);
  };

  // Handle WebSocket events
  useEffect(() => {
    if (!lastEvent) return;
    const { topic, payload } = lastEvent;
    const t = new Date().toLocaleTimeString();

    if (topic === 'workflow.state_change') {
      setStatus(payload.new_state);
      addLog(t, `Workflow state: ${payload.new_state}`, payload.error_message ? 'error' : 'info');
      if (['Completed', 'Failed', 'Cancelled'].includes(payload.new_state)) setStepIdx(-1);
    } else if (topic === 'task.started') {
      addLog(t, `Task started: ${payload.task_id}`, 'info');
    } else if (topic === 'task.progress') {
      addLog(t, `[${payload.progress}%] ${payload.logs}`, 'info');
    } else if (topic === 'task.completed') {
      const r = payload.result;
      let msg = 'Step completed.';
      if (r) {
        if (r.entries && Array.isArray(r.entries)) {
          const count = r.entries.length;
          const pdfs = r.entries.filter((e: any) => !e.is_dir);
          msg = `Found ${count} file(s) in ${r.path || 'directory'}`;
          setResult(pdfs.map((e: any, i: number) => `${i + 1}. ${e.name}${e.size ? ` (${(e.size / 1024).toFixed(1)} KB)` : ''}`).join('\n'));
        }
        else if (r.links) { msg = `Found ${r.links.length} links`; setResult(r.links.map((l: any, i: number) => `${i + 1}. ${l.title} → ${l.url}`).join('\n')); }
        else if (r.summary) { msg = r.summary; setResult(r.summary); }
        else if (r.text) { msg = r.text; setResult(r.text); }
        else if (r.stdout) { msg = r.stdout; setResult(r.stdout); }
        else if (r.content) { msg = r.content; setResult(r.content); }
        else if (r.path && r.success) { msg = `File saved: ${r.path}`; setResult(msg); }
        else { msg = JSON.stringify(r).substring(0, 200); }
      }
      addLog(t, msg, 'info');
      setStepIdx(p => p + 1);
    } else if (topic === 'task.failed') {
      addLog(t, `Failed: ${payload.error}`, 'error');
    } else if (topic === 'permission.request') {
      setPerm(payload);
      addLog(t, `Permission requested: ${payload.action}`, 'warn');
    }
  }, [lastEvent, addLog]);

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    const userMsg = prompt.trim();
    const t = new Date().toLocaleTimeString();

    // Chat mode: conversational messages get a direct reply
    if (isChatMessage(userMsg)) {
      setChatHistory(prev => [...prev, { role: 'user', content: userMsg, time: t }]);
      setPrompt('');
      setChatLoading(true);
      try {
        const res = await api.chat(userMsg, token);
        const replyTime = new Date().toLocaleTimeString();
        setChatHistory(prev => [...prev, { role: 'assistant', content: res.reply, time: replyTime }]);
      } catch (e: any) {
        const errTime = new Date().toLocaleTimeString();
        setChatHistory(prev => [...prev, { role: 'assistant', content: `Sorry, I encountered an error: ${e.message}`, time: errTime }]);
      }
      setChatLoading(false);
      return;
    }

    // Task mode: existing workflow plan + execution flow (unchanged)
    setLogs([]); setPerm(null); setEmailDraft(null); setPlan([]); setStepIdx(-1); setResult(null); setSelectedStep(null);
    setStatus('Planning'); setStartTime(Date.now()); setPrompt(''); setLastUserPrompt(userMsg);
    addLog(t, `Analyzing: "${userMsg.substring(0, 40)}..."`, 'info');

    try {
      const planData = await api.generatePlan(userMsg, token!);
      setPlan(planData.steps);
      addLog(t, `Generated ${planData.steps.length} steps.`, 'info');

      if (planData.pending_confirmation?.type === 'email_draft') {
        setEmailDraft(planData.pending_confirmation);
        setPendingPrompt(userMsg);
        setEditedSubj(planData.pending_confirmation.subject);
        setEditedBody(planData.pending_confirmation.body);
        setStatus('Waiting');
        return;
      }
      if (planData.pending_confirmation?.type === 'file_write') {
        const msg = planData.pending_confirmation.message || 'ACO wants to create a file. Allow?';
        const allowed = window.confirm(msg);
        if (!allowed) {
          addLog(t, 'File creation cancelled by user.', 'info');
          setStatus('Idle');
          return;
        }
      }
      await executeSteps(planData.steps, userMsg);
    } catch (e: any) {
      addLog(t, `Error: ${e.message}`, 'error');
      setStatus('Failed');
    }
  };

  const executeSteps = async (steps: any[], originalPrompt?: string) => {
    const t = new Date().toLocaleTimeString();
    const desc = originalPrompt || prompt;
    try {
      const wf = await api.createWorkflow(`NLP: ${desc.substring(0, 30)}`, desc, steps, token!);
      const ex = await api.executeWorkflow(wf._id, token!);
      setExecId(ex.execution_id); setStepIdx(0); setStatus('Executing');
    } catch (e: any) {
      addLog(t, `Error: ${e.message}`, 'error');
      setStatus('Failed');
    }
  };

  const confirmEmail = async () => {
    if (!emailDraft) return;
    setEmailDraft(null); setStatus('Planning');
    const updated = plan.map((s: any) => {
      if (s.action === 'fill' && s.name?.toLowerCase().includes('subject')) return { ...s, parameters: { ...s.parameters, value: editedSubj } };
      if (s.action === 'fill' && s.name?.toLowerCase().includes('body')) return { ...s, parameters: { ...s.parameters, value: editedBody } };
      return s;
    });
    setPlan(updated);
    await executeSteps(updated, pendingPrompt);
  };

  const handlePerm = async (ok: boolean) => {
    if (!perm) { console.error('[PERM] handlePerm called but perm is null'); return; }
    try {
      const res = await api.respondPermission(perm.request_id, ok, token!);
      console.log('[PERM] API response:', res);
      setPerm(null);
      addLog(new Date().toLocaleTimeString(), `Permission ${ok ? 'granted' : 'denied'} for ${perm.action}`, 'info');
    } catch (e: any) {
      console.error('[PERM] API error:', e);
      addLog(new Date().toLocaleTimeString(), `Permission failed: ${e.message}`, 'error');
    }
  };

  const handleReply = () => {
    setPrompt(lastUserPrompt);
    textareaRef.current?.focus();
  };

  const handleStop = async () => {
    if (!execId || !token) return;
    setStopping(true);
    try {
      await api.abortExecution(execId, token);
      addLog(new Date().toLocaleTimeString(), 'Cancellation requested...', 'info');
    } catch (e: any) {
      addLog(new Date().toLocaleTimeString(), `Stop failed: ${e.message}`, 'error');
    }
    setStopping(false);
  };

  const handleStepReplay = async (step: any) => {
    const t = new Date().toLocaleTimeString();
    setLogs([]); setPerm(null); setEmailDraft(null); setStepIdx(-1); setResult(null); setSelectedStep(null);
    setStatus('Executing'); setStartTime(Date.now());
    addLog(t, `Replaying step: ${step.name}`, 'info');
    try {
      const desc = `Replay: ${step.name}`;
      const wf = await api.createWorkflow(desc, desc, [step], token!);
      const ex = await api.executeWorkflow(wf._id, token!);
      setExecId(ex.execution_id); setStepIdx(0);
    } catch (e: any) {
      addLog(t, `Replay error: ${e.message}`, 'error');
      setStatus('Failed');
    }
  };

  const currentStep = stepIdx >= 0 && stepIdx < plan.length ? plan[stepIdx] : null;
  const isRunning = status === 'Planning' || status === 'Executing';

  const statusDotColor = status === 'Idle' ? 'bg-[#71717A]'
    : status === 'Planning' ? 'bg-[#7C3AED]'
    : status === 'Executing' ? 'bg-[#ADFF2F]'
    : status === 'Completed' ? 'bg-[#4ADE80]'
    : status === 'Failed' ? 'bg-[#F87171]'
    : 'bg-[#71717A]';

  const statusLabel = status === 'Planning' ? 'Generating plan...'
    : status === 'Executing' ? 'Executing workflow'
    : status === 'Completed' ? 'Task completed'
    : status === 'Failed' ? 'Task failed'
    : status === 'Waiting' ? 'Awaiting input'
    : 'Ready';

  return (
    <div className="h-full flex flex-col lg:flex-row overflow-hidden bg-[#08090B]">

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 relative">

        {/* Subtle radial illumination behind active area */}
        {isRunning && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] rounded-full bg-[#7C3AED]/[0.03] blur-[100px]" />
          </div>
        )}

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-6 pt-5 pb-6 relative z-10">

          {/* Suggestions grid (when idle, no chat history, no plan) */}
          {plan.length === 0 && status === 'Idle' && chatHistory.length === 0 && (
            <div className="max-w-2xl mx-auto mt-8 mb-8">
              <div className="mb-5">
                <h2 className="text-[13px] font-semibold text-[#F4F4F5] mb-1">Command Workspace</h2>
                <p className="text-[11px] text-[#71717A]">Describe a task or choose a starting point</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestions.map((s, i) => (
                  <motion.button
                    key={i}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => setPrompt(s.text)}
                    className="text-left p-3.5 rounded-[14px] border border-white/[0.07] bg-[#121419] hover:border-white/[0.12] hover:bg-[#181B21] transition-all duration-200 group cursor-pointer"
                  >
                    <div className="flex items-start gap-2.5">
                      <span className="text-[15px] mt-0.5 shrink-0">{s.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] text-[#A1A1AA] group-hover:text-[#F4F4F5] leading-relaxed transition-colors truncate">{s.text}</p>
                        <p className="text-[10px] text-[#71717A] mt-1 uppercase tracking-wider font-medium">{s.category}</p>
                      </div>
                      <ArrowRight size={10} className="text-[#71717A] group-hover:text-[#7C3AED] mt-1 shrink-0 opacity-0 group-hover:opacity-100 transition-all duration-200" />
                    </div>
                  </motion.button>
                ))}
              </div>
            </div>
          )}

          {/* Chat History */}
          {chatHistory.length > 0 && (
            <div className="max-w-2xl mx-auto space-y-3 mb-5">
              {chatHistory.map((msg, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
                  className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                  <div className={cn('max-w-[85%] rounded-[14px] px-4 py-3 text-[13px] leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-[#7C3AED]/[0.08] text-[#F4F4F5] border border-[#7C3AED]/15'
                      : 'bg-[#121419] border border-white/[0.07] text-[#F4F4F5]')}>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <p className="text-[9px] text-[#71717A] mt-1.5">{msg.time}</p>
                  </div>
                </motion.div>
              ))}
              {chatLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-[#121419] border border-white/[0.07] rounded-[14px] px-4 py-3 text-[13px] text-[#71717A]">
                    <Loader2 size={13} className="animate-spin inline mr-2 text-[#7C3AED]" />Thinking...
                  </div>
                </motion.div>
              )}
            </div>
          )}

          {/* Result */}
          <AnimatePresence mode="wait">
            {result && (
              <motion.div
                key="result-card"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2 }}
                className="max-w-2xl mx-auto mb-5"
              >
                <ResultDisplay result={result} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Workflow Graph + Execution Panel */}
          {plan.length > 0 && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-5">
              <div className="xl:col-span-2">
                <WorkflowGraph steps={plan} activeStepIndex={stepIdx} onStepClick={setSelectedStep} selectedStepIndex={selectedStep} onStepReplay={handleStepReplay} />
              </div>
              <div className="space-y-3">
                {selectedStep !== null && plan[selectedStep] && (
                  <StepDetails step={plan[selectedStep]} index={selectedStep}
                    status={selectedStep < stepIdx ? 'Completed' : selectedStep === stepIdx ? 'Running' : 'Pending'}
                    onClose={() => setSelectedStep(null)} />
                )}
                <ExecutionPanel
                  stateMachineStatus={status}
                  activeStepIndex={stepIdx}
                  totalSteps={plan.length}
                  currentStepName={currentStep?.name || ''}
                  currentAgent={currentStep?.agent_type || ''}
                  progress={0}
                  startTime={startTime}
                  onReply={handleReply}
                />
              </div>
            </div>
          )}

          {/* Browser Preview */}
          {plan.length > 0 && isRunning && (
            <div className="rounded-[14px] border border-white/[0.07] bg-[#121419] overflow-hidden mb-5">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.07]">
                <div className="flex items-center gap-2">
                  <MonitorPlay size={12} className="text-[#7C3AED]" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#71717A]">Browser Preview</span>
                </div>
                <div className="flex items-center gap-1">
                  <button className="p-1 rounded-md hover:bg-white/[0.05] cursor-pointer transition-colors" title="Fullscreen"><Maximize2 size={11} className="text-[#71717A]" /></button>
                </div>
              </div>
              <div className="h-[200px] flex items-center justify-center bg-[#0D0F12]">
                <div className="text-center">
                  <Globe size={22} className="mx-auto mb-2 text-[#71717A]" />
                  <p className="text-[11px] text-[#71717A]">Browser session will appear here</p>
                  <p className="text-[10px] text-[#71717A]/60 mt-1">Connect a browser agent to see live preview</p>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Command Composer */}
        <div className="relative z-10 px-4 sm:px-6 pb-4 pt-2">
          <div className="max-w-2xl mx-auto">
            {/* Composer card */}
            <div className={cn(
              'composer-focus rounded-[14px] border transition-all duration-200',
              'bg-[#121419]',
              prompt ? 'border-[#7C3AED]/30' : 'border-white/[0.07]'
            )}>
              {/* Context label */}
              <div className="flex items-center gap-2 px-4 pt-3 pb-0">
                <div className="flex items-center gap-2">
                  <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', statusDotColor, isRunning && 'animate-pulse')} />
                  <span className="text-[10px] text-[#71717A] font-medium uppercase tracking-wider">
                    {statusLabel}
                  </span>
                </div>
                {status === 'Planning' && (
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#7C3AED]/10 border border-[#7C3AED]/20">
                    <Loader2 size={9} className="text-[#7C3AED] animate-spin" />
                    <span className="text-[9px] font-semibold text-[#7C3AED]">PLAN</span>
                  </span>
                )}
                {status === 'Executing' && (
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#ADFF2F]/10 border border-[#ADFF2F]/20">
                    <div className="w-1 h-1 rounded-full bg-[#ADFF2F] animate-pulse" />
                    <span className="text-[9px] font-semibold text-[#ADFF2F]">LIVE</span>
                  </span>
                )}
              </div>

              {/* Textarea */}
              <div className="px-4 py-3">
                <textarea
                  ref={textareaRef}
                  placeholder="Describe a task for ACO..."
                  value={prompt}
                  onChange={(e) => {
                    setPrompt(e.target.value);
                    // Auto-grow
                    const el = e.target;
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
                  }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                  rows={2}
                  aria-label="Task instruction"
                  className="w-full bg-transparent outline-none resize-none text-[13px] placeholder-[#71717A] text-[#F4F4F5] leading-relaxed min-h-[44px] max-h-[160px]"
                />
              </div>

              {/* Footer bar */}
              <div className="flex items-center justify-between px-4 pb-3">
                <div className="flex items-center gap-0.5">
                  <button
                    className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition-colors cursor-pointer"
                    title="Attach file"
                    aria-label="Attach file"
                  >
                    <Paperclip size={15} />
                  </button>
                  <button
                    className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition-colors cursor-pointer"
                    title="Voice input"
                    aria-label="Voice input"
                  >
                    <Mic size={15} />
                  </button>
                  <button
                    className="p-1.5 rounded-lg text-[#71717A] hover:text-[#A1A1AA] hover:bg-white/[0.05] transition-colors cursor-pointer"
                    title="Screenshot"
                    aria-label="Take screenshot"
                  >
                    <Camera size={15} />
                  </button>
                  <span className="text-[10px] text-[#71717A]/50 ml-2 hidden sm:inline">
                    Shift+Enter for newline
                  </span>
                </div>
                {/* Stop button when running, Run button when idle */}
                {isRunning ? (
                  <button
                    onClick={handleStop}
                    disabled={stopping}
                    aria-label={stopping ? 'Stopping...' : 'Stop execution'}
                    className={cn(
                      'flex items-center gap-1.5 px-3.5 py-1.5 rounded-[10px] text-[11px] font-semibold transition-all duration-200 cursor-pointer',
                      stopping
                        ? 'bg-[#F87171]/20 text-[#F87171]/60 cursor-not-allowed'
                        : 'bg-[#F87171]/10 hover:bg-[#F87171]/20 text-[#F87171] border border-[#F87171]/20'
                    )}
                  >
                    {stopping ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <Square size={11} className="fill-current" />
                    )}
                    <span>{stopping ? 'Stopping...' : 'Stop'}</span>
                  </button>
                ) : (
                  <button
                    onClick={handleSubmit}
                    disabled={!connected || !prompt.trim()}
                    aria-label="Run command"
                    className={cn(
                      'flex items-center gap-1.5 px-3.5 py-1.5 rounded-[10px] text-[11px] font-semibold transition-all duration-200',
                      prompt.trim() && connected
                        ? 'bg-[#7C3AED] hover:bg-[#6D28D9] text-white cursor-pointer'
                        : 'bg-white/[0.04] text-[#71717A] cursor-not-allowed'
                    )}
                  >
                    <span>Run</span>
                    <Play size={11} className="fill-current" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel - Console + Timeline (shown when executing) */}
      {isRunning && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 380, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: 'easeInOut' }}
          className="border-l border-white/[0.07] flex flex-col shrink-0 bg-[#0D0F12] overflow-hidden"
        >
          <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.07]">
            <Terminal size={12} className="text-[#7C3AED]" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#71717A]">Execution Log</span>
            {wsUp && (
              <div className="ml-auto flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-[#ADFF2F] animate-pulse" />
                <span className="text-[9px] text-[#ADFF2F]/70 font-medium">WS</span>
              </div>
            )}
          </div>
          <div className="flex-1 p-3 min-h-0">
            <LiveConsole logs={logs} wsConnected={wsUp} />
          </div>
          {logs.length > 0 && (
            <div className="max-h-[200px] border-t border-white/[0.07] p-3 overflow-y-auto">
              <ExecutionTimeline logs={logs} stateMachineStatus={status} />
            </div>
          )}
        </motion.div>
      )}

      {/* Modals */}
      <PermissionModal permission={perm} onDecision={handlePerm} />
      <EmailDraftModal draft={emailDraft} editedSubject={editedSubj} editedBody={editedBody}
        onSubjectChange={setEditedSubj} onBodyChange={setEditedBody} onConfirm={confirmEmail}
        onReject={() => { setEmailDraft(null); setStatus('Cancelled'); }} />
    </div>
  );
}
