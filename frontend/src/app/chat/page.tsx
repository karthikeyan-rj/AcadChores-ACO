'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Paperclip, Mic, Camera, Play, Loader2, CheckCircle2,
  XCircle, Globe, Terminal, Monitor, FileText, Eye, AlertTriangle,
  Shield, RefreshCw, Send, ArrowRight, X, Maximize2,
  Minimize2, MonitorPlay
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

  const addLog = useCallback((time: string, message: string, level: LogMessage['level'] = 'info') => {
    setLogs(p => [...p, { time, message, level }]);
  }, []);

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

  return (
    <div className="h-full flex flex-col lg:flex-row overflow-hidden">
      {/* Left: Prompt + Graph + Result */}
      <div className="flex-1 flex flex-col overflow-y-auto p-6 space-y-5 min-w-0">

        {/* Prompt Box */}
        <div className={cn(
          'rounded-xl border transition-colors duration-200 bg-card',
          prompt ? 'border-primary/30' : 'border-border'
        )}>
          <div className="flex items-start gap-3 p-4">
            <Sparkles size={18} className="text-primary mt-1 shrink-0" />
            <textarea
              ref={textareaRef}
              placeholder="Tell ACO what to do..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              rows={2}
              className="flex-1 bg-transparent outline-none resize-none text-sm placeholder-gray-500 text-foreground leading-relaxed"
            />
          </div>
          <div className="flex items-center justify-between px-4 pb-3">
            <div className="flex items-center gap-1">
              <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface transition-colors cursor-pointer" title="Attach file"><Paperclip size={14} /></button>
              <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface transition-colors cursor-pointer" title="Voice input"><Mic size={14} /></button>
              <button className="p-1.5 rounded-lg text-gray-500 hover:text-foreground hover:bg-surface transition-colors cursor-pointer" title="Screenshot"><Camera size={14} /></button>
            </div>
            <button onClick={handleSubmit} disabled={!connected || !prompt.trim() || isRunning}
              className={cn(
                'flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                prompt.trim() && !isRunning
                  ? 'bg-primary hover:bg-primary-hover text-white cursor-pointer'
                  : 'bg-surface text-gray-600 cursor-not-allowed'
              )}>
              {isRunning ? <Loader2 size={13} className="animate-spin" /> : <><span>Execute</span><Play size={12} className="fill-current" /></>}
            </button>
          </div>
        </div>

        {/* Chat History */}
        {chatHistory.length > 0 && (
          <div className="space-y-3">
            {chatHistory.map((msg, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
                className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div className={cn('max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-primary/10 text-foreground border border-primary/20'
                    : 'bg-card border border-border text-foreground')}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-[9px] text-gray-600 mt-1.5">{msg.time}</p>
                </div>
              </motion.div>
            ))}
            {chatLoading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                <div className="bg-card border border-border rounded-xl px-4 py-3 text-sm text-gray-500">
                  <Loader2 size={14} className="animate-spin inline mr-2" />Thinking...
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
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              <ResultDisplay result={result} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Suggestions (when idle) */}
        {plan.length === 0 && status === 'Idle' && (
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={12} className="text-gray-500" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-500">Example Prompts</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {suggestions.map((s, i) => (
                  <motion.button key={i} whileHover={{ x: 2 }} onClick={() => setPrompt(s.text)}
                    className="text-left text-xs text-gray-400 hover:text-foreground p-3 rounded-lg border border-border hover:border-border-light hover:bg-card transition-colors cursor-pointer flex items-center gap-2 group">
                    <span className="text-sm shrink-0">{s.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="truncate">{s.text}</p>
                      <p className="text-[9px] text-gray-600 mt-0.5">{s.category}</p>
                    </div>
                    <ArrowRight size={10} className="text-gray-600 group-hover:text-primary shrink-0 opacity-0 group-hover:opacity-100 transition" />
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Workflow Graph + Execution Panel */}
        {plan.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
            <div className="xl:col-span-2">
              <WorkflowGraph steps={plan} activeStepIndex={stepIdx} onStepClick={setSelectedStep} selectedStepIndex={selectedStep} onStepReplay={handleStepReplay} />
            </div>
            <div className="space-y-4">
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
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
              <div className="flex items-center gap-2">
                <MonitorPlay size={13} className="text-primary" />
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Browser Preview</span>
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1 rounded hover:bg-surface cursor-pointer" title="Fullscreen"><Maximize2 size={11} className="text-gray-500" /></button>
              </div>
            </div>
            <div className="h-[200px] flex items-center justify-center bg-surface">
              <div className="text-center text-gray-600">
                <Globe size={24} className="mx-auto mb-2 text-gray-700" />
                <p className="text-[11px]">Browser session will appear here</p>
                <p className="text-[10px] text-gray-700 mt-1">Connect a browser agent to see live preview</p>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Right: Console + Timeline */}
      <div className="w-full lg:w-[380px] border-t lg:border-t-0 lg:border-l border-border flex flex-col shrink-0 bg-surface">
        <div className="flex-1 p-3 min-h-0 min-h-[300px]">
          <LiveConsole logs={logs} wsConnected={wsUp} />
        </div>
        {logs.length > 0 && (
          <div className="max-h-[200px] border-t border-border p-3 overflow-y-auto">
            <ExecutionTimeline logs={logs} stateMachineStatus={status} />
          </div>
        )}
      </div>

      {/* Modals */}
      <PermissionModal permission={perm} onDecision={handlePerm} />
      <EmailDraftModal draft={emailDraft} editedSubject={editedSubj} editedBody={editedBody}
        onSubjectChange={setEditedSubj} onBodyChange={setEditedBody} onConfirm={confirmEmail}
        onReject={() => { setEmailDraft(null); setStatus('Cancelled'); }} />
    </div>
  );
}
