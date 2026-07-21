'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Paperclip, Mic, Camera, Play, Loader2, CheckCircle2,
  XCircle, Terminal, FileText, AlertTriangle,
  Send, ArrowRight, Square, Activity,
  ChevronUp, ChevronDown, Trash2, AlertCircle, Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { useWorkflowStore, TaskStep } from '@/lib/workflow-store';
import { TimelineItem, TimelineMessage, TimelineWorkflow } from '@/lib/timeline';
import { LiveConsole } from '@/components/execution/LiveConsole';
import { ExecutionTimeline } from '@/components/execution/ExecutionTimeline';
import { PermissionModal } from '@/components/modals/PermissionModal';
import { EmailDraftModal } from '@/components/modals/EmailDraftModal';
import { DeleteConfirmDialog } from '@/components/modals/DeleteConfirmDialog';
import { ResultDisplay } from '@/components/ui/ResultDisplay';
import ModelSelector from '@/components/ai/ModelSelector';
import type { AISettings } from '@/lib/ai-store';
import Link from 'next/link';

const starterActions = [
  { text: 'Find PDF files on my desktop', icon: '📄', label: 'Find files' },
  { text: 'Open an application', icon: '🖥', label: 'Open app' },
  { text: 'Check a network port', icon: '🔌', label: 'Check port' },
  { text: 'Create a new file', icon: '📝', label: 'Create file' },
];

export default function ChatPage() {
  const { token } = useAuth();
  const {
    execId, setExecId, status, setStatus, plan, setPlan, stepIdx, setStepIdx,
    logs, setLogs, addLog, result, setResult, selectedStep, setSelectedStep,
    startTime, setStartTime, stopping, setStopping, hasActiveWorkflow, setHasActiveWorkflow,
    lastUserPrompt, setLastUserPrompt, chatHistory, setChatHistory,
    conversationId, setConversationId, chatLoading, setChatLoading,
    wsConnected, lastEvent, handleNewChat,
  } = useWorkflowStore();

  const [prompt, setPrompt] = useState('');
  const [perm, setPerm] = useState<any>(null);
  const [emailDraft, setEmailDraft] = useState<any>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<any>(null);
  const [editedSubj, setEditedSubj] = useState('');
  const [editedBody, setEditedBody] = useState('');
  const [pendingPrompt, setPendingPrompt] = useState('');
  const [showActivityDrawer, setShowActivityDrawer] = useState(false);
  const [aiSettings, setAISettings] = useState<AISettings | null>(null);
  const [composerProvider, setComposerProvider] = useState('ollama');
  const [composerModel, setComposerModel] = useState('');
  const [composerReasoning, setComposerReasoning] = useState('balanced');

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load AI settings
  useEffect(() => {
    if (!token) return;
    api.getAISettings(token).then(data => setAISettings(data)).catch(() => {});
  }, [token]);

  const addChatMessage = useCallback((content: string, opts: { role?: 'user' | 'assistant'; type?: string; executionId?: string; id?: string } = {}) => {
    const now = new Date();
    const item: TimelineMessage = {
      kind: 'message',
      id: opts.id || `ws-${opts.executionId || ''}-${now.getTime()}-${Math.random().toString(36).slice(2, 8)}`,
      sortKey: now.toISOString(),
      role: opts.role || 'assistant',
      content,
      type: opts.type,
      executionId: opts.executionId,
    };
    setChatHistory(prev => [...prev, item]);
  }, [setChatHistory]);

  useEffect(() => {
    if (!lastEvent) return;
    const { topic, payload } = lastEvent;
    const t = new Date().toLocaleTimeString();

    if (topic === 'workflow.state_change') {
      const newState = payload.new_state;
      setStatus(newState);
      const errMsg = payload.error_message || '';
      addLog(t, `Workflow state: ${newState}${errMsg ? ` \u2014 ${errMsg}` : ''}`, payload.error_message ? 'error' : 'info');
      if (['Completed', 'Failed', 'Cancelled'].includes(newState)) {
        setStepIdx(-1);
        setStopping(false);
        setHasActiveWorkflow(false);
        if (newState === 'Failed') {
          const errorDetail = payload.metadata?.error_details;
          const suggestion = errorDetail?.suggestion || 'Try rephrasing your request or breaking it into smaller steps.';
          addChatMessage(`Workflow failed: ${errMsg || 'An error occurred during execution.'}\n\nSuggestion: ${suggestion}`, {
            type: 'error',
            executionId: payload.execution_id,
          });
        }
      }
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
          msg = `Found ${count} file(s) in ${r.path || 'directory'}`;
          setResult(r.entries.map((e: any, i: number) => `${i + 1}. ${e.name}${e.size ? ` (${(e.size / 1024).toFixed(1)} KB)` : ''}`).join('\n'));
        }
        else if (r.links) { msg = `Found ${r.links.length} links`; setResult(r.links.map((l: any, i: number) => `${i + 1}. ${l.title} \u2192 ${l.url}`).join('\n')); }
        else if (r.summary) { msg = r.summary; setResult(r.summary); }
        else if (r.text) { msg = r.text; setResult(r.text); }
        else if (r.stdout) { msg = r.stdout; setResult(r.stdout); }
        else if (r.content) { msg = r.content; setResult(r.content); }
        else if (r.path && r.success) { msg = `File saved: ${r.path}`; setResult(msg); }
        else if (r.moved) { msg = `Moved: ${r.source} \u2192 ${r.destination}`; setResult(msg); }
        else if (r.renamed) { msg = `Renamed: ${r.old_path} \u2192 ${r.new_path}`; setResult(msg); }
        else if (r.copied) { msg = `Copied: ${r.source} \u2192 ${r.destination}`; setResult(msg); }
        else if (r.deleted) {
          if (r.verified) {
            msg = `Deleted successfully:\n${r.path}`;
            if (r.size != null) msg += `\nSize was: ${r.size < 1024 ? r.size + ' B' : (r.size / 1024).toFixed(1) + ' KB'}`;
          } else {
            msg = `Deletion failed: the file may still exist at ${r.path}`;
          }
          setResult(msg);
        }
        else if (r.moved_count !== undefined) { msg = `Moved ${r.moved_count} of ${r.matched_count} matched files. Skipped: ${r.skipped?.length || 0}`; setResult(msg); }
        else { msg = JSON.stringify(r).substring(0, 200); }
      }
      addLog(t, msg, 'info');
      setStepIdx(p => p + 1);
    } else if (topic === 'task.failed') {
      const details = payload.error_details;
      if (details) {
        const errMsg = `[${details.agent_type}/${details.action}] ${details.message}`;
        addLog(t, errMsg, 'error');
        if (details.suggestion) {
          addLog(t, `Suggestion: ${details.suggestion}`, 'warn');
        }
        addChatMessage(`Step failed: ${details.step_name || details.action}\n\nError: ${details.message}\n\n${details.suggestion || ''}`, {
          type: 'error',
        });
      } else {
        addLog(t, `Failed: ${payload.error}`, 'error');
        addChatMessage(`Error: ${payload.error}`, {
          type: 'error',
        });
      }
    } else if (topic === 'permission.request') {
      setPerm(payload);
      addLog(t, `Permission requested: ${payload.action}`, 'warn');
    }
  }, [lastEvent, addLog, addChatMessage, setStatus, setStepIdx, setStopping, setHasActiveWorkflow, setResult]);

  const isChatMessage = (text: string): boolean => {
    const lower = text.toLowerCase().trim();
    const greetings = /^(hi|hello|hey|howdy|yo|hola|good\s*(morning|afternoon|evening)|namaste|vanakkam)\b/;
    const casual = /^(thanks|thank you|thx|bye|goodbye|see you|ok|okay|sure|cool|nice|great|awesome|lol|haha|yes|no|yep|nope|np|welcome|please|sorry)\b/;
    const chitchat = /(how are you|what('?s| is) (your name|up|going on)|who (are|r) you|what can you do|help me|what do you know)/;
    const systemQuery = /\b(disk\s*space|ipconfig|hostname|tasklist|running\s*process|system\s*(info|information)|memory|cpu|ram|whoami|date|time|path|environment|env\s*var|network|wifi|bluetooth|driver|service|port|firewall|registry|process|disk|drive|volume|partition|boot|startup|shutdown|restart|sleep|hibernate|lock|log\s*out|suspend|resume|cancel|abort|kill|terminate|force|format|del|delete|remove|erase|wipe|clean|purge|clear|empty|destroy|nuke|rm\s*-rf|rmdir|rd\s|move|rename|copy|xcopy|robocopy|mklink|junction|hardlink|symbolic|shortcut)\b/;
    const noActionWords = !/\b(open|send|search|create|write|run|execute|navigate|click|fill|delete|find|list|show|get|download|upload|install|compress|extract|summarize|read|play|pause|stop|close|copy|move|rename)\b/.test(lower);
    return (greetings.test(lower) || casual.test(lower) || chitchat.test(lower) || noActionWords) && !systemQuery.test(lower);
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) return;
    if (hasActiveWorkflow) return;

    // Block if cloud model selected but no credential
    const localOnly = aiSettings?.ai_local_only ?? true;
    if (!localOnly && composerProvider !== 'ollama' && !composerModel) return;

    const userMsg = prompt.trim();
    const t = new Date().toLocaleTimeString();

    if (isChatMessage(userMsg)) {
      addChatMessage(userMsg, { role: 'user' });
      setPrompt('');
      setChatLoading(true);
      try {
        const res = await api.chat(userMsg, token, conversationId || undefined);
        if (res.conversation_id && !conversationId) {
          setConversationId(res.conversation_id);
        }
        addChatMessage(res.reply, { type: 'assistant' });
      } catch (e: any) {
        addChatMessage(`Sorry, I encountered an error: ${e.message}`);
      }
      setChatLoading(false);
      return;
    }

    addChatMessage(userMsg, { role: 'user' });
    setLogs([]); setPerm(null); setEmailDraft(null); setDeleteConfirm(null); setPlan([]); setStepIdx(-1); setResult(null); setSelectedStep(null);
    setStatus('Planning'); setStartTime(Date.now()); setPrompt(''); setLastUserPrompt(userMsg);
    addLog(t, `Analyzing: "${userMsg.substring(0, 40)}..."`, 'info');

    try {
      const planData = await api.generatePlan(userMsg, token!);
      if (planData.conversation_id && !conversationId) {
        setConversationId(planData.conversation_id);
      }

      if (!planData.success || !planData.steps || planData.steps.length === 0) {
        const replyText = planData.reply || 'Could not generate a plan for that request.';
        addChatMessage(replyText, { type: 'assistant' });
        setStatus('Idle');
        return;
      }

      setPlan(planData.steps);
      const planMsg = `Generated ${planData.steps.length} step(s). Review the steps before execution.`;
      addChatMessage(planMsg, { type: 'workflow_plan' });
      addLog(t, `Generated ${planData.steps.length} steps.`, 'info');

      if (planData.pending_confirmation?.type === 'email_draft') {
        setEmailDraft(planData.pending_confirmation);
        setPendingPrompt(userMsg);
        setEditedSubj(planData.pending_confirmation.subject);
        setEditedBody(planData.pending_confirmation.body);
        setStatus('Waiting');
        return;
      }
      const confirmTypes = ['file_write', 'file_delete', 'file_move', 'file_rename', 'file_move_matching', 'terminal_command'];
      if (planData.pending_confirmation && confirmTypes.includes(planData.pending_confirmation.type)) {
        if (planData.pending_confirmation.type === 'file_delete') {
          setDeleteConfirm(planData.pending_confirmation);
          setPendingPrompt(userMsg);
          setStatus('Waiting');
          return;
        }
        if (planData.pending_confirmation.type === 'terminal_command') {
          const cmd = (planData.pending_confirmation.command || '').toLowerCase();
          const isDeleteCmd = /remove-item|del\s|rm\s|rm\s+-|rmdir|erase\s/i.test(cmd);
          if (isDeleteCmd) {
            setDeleteConfirm({
              type: 'file_delete',
              path: planData.pending_confirmation.command,
              filename: planData.pending_confirmation.command,
              message: planData.pending_confirmation.message || 'ACO wants to run a delete command. Allow?',
            });
            setPendingPrompt(userMsg);
            setStatus('Waiting');
            return;
          }
        }
        const msg = planData.pending_confirmation.message || 'ACO requires your confirmation.';
        const allowed = window.confirm(msg);
        if (!allowed) {
          const cancelMsg = `${planData.pending_confirmation.type.replace(/_/g, ' ')} cancelled by user.`;
          addChatMessage(cancelMsg);
          setStatus('Idle');
          return;
        }
      }
      await executeSteps(planData.steps, userMsg);
    } catch (e: any) {
      addLog(t, `Error: ${e.message}`, 'error');
      addChatMessage(`Error: ${e.message}`, { type: 'error' });
      setStatus('Failed');
    }
  };

  const executeSteps = async (steps: any[], originalPrompt?: string) => {
    const t = new Date().toLocaleTimeString();
    const desc = originalPrompt || prompt;
    try {
      const wf = await api.createWorkflow(`NLP: ${desc.substring(0, 30)}`, desc, steps, token!);
      const ex = await api.executeWorkflow(wf._id, token!, conversationId || undefined);
      setExecId(ex.execution_id); setStepIdx(0); setStatus('Executing');
      setHasActiveWorkflow(true);
      setStartTime(Date.now());
    } catch (e: any) {
      if (e.message && e.message.includes('active workflow already exists')) {
        addLog(t, 'A task is already running. Stop or wait for it to finish.', 'warn');
        addChatMessage('A task is already running. Stop or wait for it to finish.');
        setStatus('Idle');
      } else {
        addLog(t, `Error: ${e.message}`, 'error');
        setStatus('Failed');
      }
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

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm || !plan.length) return;
    const savedPlan = [...plan];
    const savedPrompt = pendingPrompt;
    setDeleteConfirm(null);
    setStatus('Deleting');
    addLog(new Date().toLocaleTimeString(), `Deleting: ${deleteConfirm.path}`, 'info');
    await executeSteps(savedPlan, savedPrompt);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirm(null);
    addChatMessage('File delete cancelled by user.');
    setStatus('Idle');
  };

  const handlePerm = async (ok: boolean) => {
    if (!perm) return;
    try {
      await api.respondPermission(perm.request_id, ok, token!);
      setPerm(null);
      addLog(new Date().toLocaleTimeString(), `Permission ${ok ? 'granted' : 'denied'} for ${perm.action}`, 'info');
    } catch (e: any) {
      addLog(new Date().toLocaleTimeString(), `Permission failed: ${e.message}`, 'error');
    }
  };

  const handleStop = async () => {
    if (!execId || !token) return;
    setStopping(true);
    try {
      await api.abortExecution(execId, token);
      addLog(new Date().toLocaleTimeString(), 'Cancellation requested...', 'info');
      setStatus('Stopping');
    } catch (e: any) {
      addLog(new Date().toLocaleTimeString(), `Stop failed: ${e.message}`, 'error');
      setStopping(false);
    }
  };

  const handleModelChange = useCallback((provider: string, model: string, _credentialId: string | null, reasoning: string) => {
    setComposerProvider(provider);
    setComposerModel(model);
    setComposerReasoning(reasoning);
  }, []);

  const currentStep = stepIdx >= 0 && stepIdx < plan.length ? plan[stepIdx] : null;
  const isRunning = status === 'Planning' || status === 'Executing' || status === 'Waiting' || status === 'Stopping';

  const statusDotColor = status === 'Idle' ? 'bg-theme-tertiary'
    : status === 'Planning' ? 'bg-text-primary'
    : status === 'Executing' ? 'bg-status-active'
    : status === 'Completed' ? 'bg-status-active'
    : status === 'Failed' ? 'bg-status-error'
    : status === 'Stopping' ? 'bg-status-error'
    : status === 'Cancelled' ? 'bg-theme-tertiary'
    : 'bg-theme-tertiary';

  const statusLabel = status === 'Planning' ? 'Generating plan...'
    : status === 'Executing' ? 'Executing workflow'
    : status === 'Completed' ? 'Task completed'
    : status === 'Failed' ? 'Task failed'
    : status === 'Waiting' ? 'Awaiting permission'
    : status === 'Deleting' ? 'Deleting file...'
    : status === 'Stopping' ? 'Stopping...'
    : status === 'Cancelled' ? 'Cancelled'
    : 'Ready';

  const showEmptyState = plan.length === 0 && status === 'Idle' && chatHistory.length === 0;
  const localOnly = aiSettings?.ai_local_only ?? true;

  return (
    <div className="h-full flex flex-col lg:flex-row overflow-hidden bg-app">

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 relative">

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 pt-5 pb-6 relative z-10">

        {/* Empty state */}
        {showEmptyState && (
          <div className="max-w-lg mx-auto mt-8 mb-6 text-center">
            <div className="mb-6">
              <h2 className="text-base font-bold text-theme mb-1">What would you like ACO to do?</h2>
              <p className="text-[11px] text-theme-tertiary">Describe a task or choose a starting point</p>
            </div>

            {/* Model summary */}
            <div className="mb-5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-theme text-[10px] text-theme-secondary">
              <span className="w-1.5 h-1.5 rounded-full bg-status-active" />
              <span>Using {localOnly ? 'Local' : 'Cloud'} model</span>
              <span className="text-theme-tertiary">{'\u00b7'}</span>
              <Link href="/settings" className="text-theme hover:underline">Configure</Link>
            </div>

            {/* Compact starter chips */}
            <div className="flex flex-wrap justify-center gap-2">
              {starterActions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setPrompt(s.text)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-theme bg-surface hover:border-theme-strong hover:bg-surface-hover transition-all duration-150 text-[11px] text-theme-secondary hover:text-theme cursor-pointer"
                >
                  <span>{s.icon}</span>
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat History */}
        {chatHistory.length > 0 && (
          <div className="max-w-2xl mx-auto space-y-3 mb-5">
            {chatHistory.map((item) => {
              if (item.kind === 'message') {
                const msg = item;
                const timeStr = msg.sortKey ? new Date(msg.sortKey).toLocaleTimeString() : '';
                return (
                  <div key={item.id}
                    className={cn('flex animate-[fadeIn_0.2s_ease-out]', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                    <div className={cn('max-w-[85%] rounded-xl px-4 py-3 text-[13px] leading-relaxed',
                      msg.role === 'user'
                        ? 'bg-surface-2 text-theme border border-theme'
                        : msg.type === 'workflow_plan'
                          ? 'bg-surface-2 border border-theme text-theme'
                          : msg.type === 'error'
                            ? 'bg-status-error-soft border border-status-error text-theme'
                            : 'bg-surface border border-theme text-theme')}>
                      {msg.type === 'workflow_plan' && (
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-text-primary" />
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-theme-secondary">Workflow</span>
                        </div>
                      )}
                      {msg.type === 'error' && (
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-status-error" />
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-status-error">Error</span>
                        </div>
                      )}
                      {msg.type === 'fallback_notice' && (
                        <div className="flex items-center gap-1.5 mb-1.5">
                          <AlertTriangle size={10} className="text-status-warning" />
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-status-warning">Cloud fallback</span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      <p className="text-[9px] text-theme-tertiary mt-1.5">{timeStr}</p>
                    </div>
                  </div>
                );
              }

              if (item.kind === 'workflow') {
                const wf = item;
                const startedStr = wf.startedAt ? new Date(wf.startedAt).toLocaleTimeString() : '';
                const isActive = ['Planning', 'Executing', 'Waiting', 'Retry', 'Stopping'].includes(wf.status);
                const isTerminal = ['Completed', 'Failed', 'Cancelled'].includes(wf.status);
                const statusBadgeClass = wf.displayStatus === 'completed'
                  ? 'bg-status-active-soft border-status-active text-status-active'
                  : wf.displayStatus === 'stopped'
                    ? 'bg-status-error-soft border-status-error text-status-error'
                    : isActive
                      ? 'bg-status-active-soft border-status-active text-status-active'
                      : 'bg-surface-2 border-theme text-theme-secondary';
                const statusLabel = wf.displayStatus === 'completed' ? 'Completed'
                  : wf.displayStatus === 'stopped' ? (wf.status === 'Cancelled' ? 'Stopped' : 'Failed')
                  : wf.status;
                return (
                  <div key={item.id} className="animate-[fadeIn_0.2s_ease-out]">
                    <div className="rounded-xl border border-theme bg-surface overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-3 border-b border-theme">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-lg bg-surface-2 flex items-center justify-center shrink-0">
                            <FileText size={14} className="text-theme-secondary" />
                          </div>
                          <div>
                            <p className="text-[13px] font-semibold text-theme">{wf.title || 'Workflow'}</p>
                            <p className="text-[10px] text-theme-tertiary mt-0.5">
                              {wf.totalSteps} step(s){startedStr ? ` \u00b7 ${startedStr}` : ''}
                            </p>
                          </div>
                        </div>
                        <span className={cn('px-2 py-0.5 rounded-full border text-[10px] font-semibold', statusBadgeClass)}>
                          {isActive && <Activity size={9} className="inline mr-1 animate-pulse" />}
                          {wf.displayStatus === 'completed' && <CheckCircle2 size={9} className="inline mr-1" />}
                          {wf.displayStatus === 'stopped' && <XCircle size={9} className="inline mr-1" />}
                          {statusLabel}
                        </span>
                      </div>
                      {wf.steps.length > 0 && (
                        <div className="divide-y divide-theme max-h-48 overflow-y-auto">
                          {wf.steps.map((step: any, i: number) => (
                            <div key={step.step_id || i} className="px-4 py-2 flex items-center gap-3">
                              <span className="w-5 text-center text-[11px] text-theme-tertiary font-medium">{i + 1}</span>
                              <div className="flex-1 min-w-0">
                                <p className="text-[12px] text-theme truncate">{step.name || step.step_id || `Step ${i + 1}`}</p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-surface-2 text-theme-secondary">{step.agent_type}</span>
                                  <span className="text-[10px] text-theme-tertiary">{step.action}</span>
                                </div>
                              </div>
                              <div className={cn('w-5 h-5 rounded-full flex items-center justify-center shrink-0',
                                i < wf.currentStepIndex ? 'bg-status-active' :
                                i === wf.currentStepIndex && isActive ? 'bg-text-primary animate-pulse' :
                                'bg-surface-2')}>
                                {i < wf.currentStepIndex ? (
                                  <CheckCircle2 size={10} className="text-text-inverse" />
                                ) : i === wf.currentStepIndex && isActive ? (
                                  <Activity size={10} className="text-text-inverse" />
                                ) : (
                                  <span className="text-[10px] text-theme-tertiary">{i + 1}</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {wf.errorMessage && (
                        <div className="px-4 py-2 border-t border-theme bg-status-error-soft">
                          <p className="text-[11px] text-status-error">{wf.errorMessage}</p>
                        </div>
                      )}
                      {wf.partialResult && (
                        <div className="px-4 py-2 border-t border-theme">
                          <p className="text-[11px] text-theme-secondary whitespace-pre-wrap">{wf.partialResult}</p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }

              return null;
            })}
            {chatLoading && (
              <div className="flex justify-start animate-[fadeIn_0.15s_ease-out]">
                <div className="bg-surface border border-theme rounded-xl px-4 py-3 text-[13px] text-theme-tertiary">
                  <Loader2 size={13} className="animate-spin inline mr-2 text-theme" />Thinking...
                </div>
              </div>
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

        {/* Compact Workflow Summary */}
        {plan.length > 0 && (
          <div className="max-w-2xl mx-auto mb-5">
            <div className="rounded-xl border border-theme bg-surface overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-theme">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-surface-2 flex items-center justify-center shrink-0">
                    <FileText size={14} className="text-theme-secondary" />
                  </div>
                  <div>
                    <p className="text-[13px] font-semibold text-theme">Workflow: {lastUserPrompt || 'Task'}</p>
                    <p className="text-[10px] text-theme-tertiary mt-0.5">{plan.length} step(s) \u00b7 {statusLabel}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {status === 'Waiting' && (
                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-status-error-soft border border-status-error text-[10px] font-semibold text-status-error">
                      <AlertTriangle size={9} /> Awaiting approval
                    </span>
                  )}
                  {status === 'Executing' && (
                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-status-active-soft border border-status-active text-[10px] font-semibold text-status-active">
                      <Activity size={9} /> Live
                    </span>
                  )}
                  {status === 'Completed' && (
                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-status-active-soft border border-status-active text-[10px] font-semibold text-status-active">
                      <CheckCircle2 size={9} /> Completed
                    </span>
                  )}
                  {status === 'Failed' && (
                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-status-error-soft border border-status-error text-[10px] font-semibold text-status-error">
                      <XCircle size={9} /> Failed
                    </span>
                  )}
                  {status === 'Cancelled' && (
                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-surface-2 border border-theme text-[10px] font-semibold text-theme-secondary">
                      <Square size={9} /> Cancelled
                    </span>
                  )}
                </div>
              </div>

              {/* Steps list */}
              <div className="divide-y divide-theme max-h-60 overflow-y-auto">
                {plan.map((step, i) => (
                  <div key={step.step_id} className="px-4 py-2.5 flex items-center gap-3 hover:bg-app transition-colors">
                    <span className="w-5 text-center text-[11px] text-theme-tertiary font-medium">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-theme truncate">{step.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-surface-2 text-theme-secondary">{step.agent_type}</span>
                        <span className="text-[10px] text-theme-tertiary">{step.action}</span>
                        {step.parameters?.path && (
                          <span className="text-[10px] text-theme-tertiary truncate max-w-[200px]">{step.parameters.path}</span>
                        )}
                      </div>
                    </div>
                    <div className={cn('w-5 h-5 rounded-full flex items-center justify-center shrink-0',
                      i < stepIdx ? 'bg-status-active' :
                      i === stepIdx && isRunning ? 'bg-text-primary animate-pulse' :
                      'bg-surface-2')}>
                      {i < stepIdx ? (
                        <CheckCircle2 size={10} className="text-text-inverse" />
                      ) : i === stepIdx && isRunning ? (
                        <Activity size={10} className="text-text-inverse" />
                      ) : (
                        <span className="text-[10px] text-theme-tertiary">{i + 1}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Approval actions for waiting state */}
              {(status === 'Waiting' && (deleteConfirm || emailDraft)) && (
                <div className="px-4 py-3 border-t border-theme bg-app">
                  {deleteConfirm && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-status-error-soft border border-status-error">
                        <Trash2 size={14} className="text-status-error shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-[12px] font-medium text-theme">Delete {deleteConfirm.filename}</p>
                          <p className="text-[10px] text-theme-tertiary mt-0.5 break-all">{deleteConfirm.path}</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={handleDeleteCancel}
                          className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-surface hover:bg-surface-hover text-theme-secondary border border-theme-strong transition cursor-pointer">
                          Cancel
                        </button>
                        <button onClick={handleDeleteConfirm}
                          className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-status-error hover:opacity-90 text-text-inverse transition cursor-pointer flex items-center justify-center gap-1.5">
                          <Trash2 size={12} /> Delete file
                        </button>
                      </div>
                    </div>
                  )}
                  {emailDraft && (
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-app border border-theme">
                        <p className="text-[12px] font-medium text-theme">Review email</p>
                        <p className="text-[10px] text-theme-secondary mt-0.5">To: {emailDraft.to}</p>
                        <p className="text-[10px] text-theme-secondary mt-0.5">Subject: {emailDraft.subject}</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => { setEmailDraft(null); setStatus('Cancelled'); }}
                          className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-surface hover:bg-surface-hover text-theme-secondary border border-theme-strong transition cursor-pointer">
                          Cancel
                        </button>
                        <button onClick={confirmEmail}
                          className="flex-1 text-[12px] font-semibold py-2 rounded-lg bg-text-primary hover:opacity-90 text-text-inverse transition cursor-pointer flex items-center justify-center gap-1.5">
                          <Send size={12} /> Send email
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Activity Drawer Trigger (mobile) */}
        <div className="lg:hidden mb-4">
          <button
            onClick={() => setShowActivityDrawer(!showActivityDrawer)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-theme bg-surface hover:border-theme-strong hover:bg-surface-2 transition-all duration-200 cursor-pointer"
          >
            <Activity size={14} className="text-theme-tertiary" />
            <span className="text-[12px] text-theme-secondary font-medium">
              {showActivityDrawer ? 'Hide activity' : `Show activity (${logs.length})`}
            </span>
            {showActivityDrawer ? <ChevronUp size={14} className="text-theme-tertiary" /> : <ChevronDown size={14} className="text-theme-tertiary" />}
          </button>
        </div>

        </div>

        {/* Command Composer */}
        <div className="relative z-10 px-4 sm:px-6 pb-4 pt-2">
          <div className="max-w-2xl mx-auto">
            <div className={cn(
              'rounded-[14px] border transition-all duration-200',
              'bg-[#121620] dark:bg-[#121620]',
              prompt ? 'border-[#363F4C]' : 'border-[#272E39]'
            )} style={{
              backgroundColor: 'var(--composer-bg)',
              borderColor: prompt ? 'var(--border-strong)' : 'var(--border-primary)',
              boxShadow: prompt ? '0 2px 12px rgba(0,0,0,0.2)' : 'none',
            }}>
              {/* Status row */}
              <div className="flex items-center gap-2 px-4 pt-3 pb-0">
                <div className="flex items-center gap-2">
                  <div className={cn('w-1.5 h-1.5 rounded-full shrink-0', statusDotColor, isRunning && 'animate-pulse')} />
                  <span className="text-[10px] text-theme-tertiary font-medium uppercase tracking-wider">
                    {statusLabel}
                  </span>
                </div>
                {(chatHistory.length > 0 || hasActiveWorkflow) && (
                  <button
                    onClick={handleNewChat}
                    disabled={isRunning}
                    className={cn(
                      'ml-auto flex items-center gap-1 px-2 py-0.5 rounded-md text-[9px] font-medium transition-colors',
                      isRunning
                        ? 'text-theme-tertiary/50 cursor-not-allowed'
                        : 'text-theme-tertiary hover:text-theme-secondary hover:bg-surface-2 cursor-pointer'
                    )}
                  >
                    New Chat
                  </button>
                )}
                {status === 'Planning' && (
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-2 border border-theme">
                    <Loader2 size={9} className="text-theme animate-spin" />
                    <span className="text-[9px] font-semibold text-theme-secondary">PLAN</span>
                  </span>
                )}
                {status === 'Executing' && (
                  <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-status-active-soft border border-status-active">
                    <div className="w-1 h-1 rounded-full bg-status-active animate-pulse" />
                    <span className="text-[9px] font-semibold text-status-active">LIVE</span>
                  </span>
                )}
              </div>

              {/* Textarea */}
              <div className="px-4 py-3">
                {hasActiveWorkflow ? (
                  <div className="flex items-center gap-2 py-2 text-[12px] text-theme-tertiary">
                    <Loader2 size={12} className="animate-spin text-theme-secondary" />
                    <span>A task is already running. Stop or wait for it to finish.</span>
                  </div>
                ) : (
                <textarea
                  ref={textareaRef}
                  placeholder="Describe a task for ACO..."
                  value={prompt}
                  onChange={(e) => {
                    setPrompt(e.target.value);
                    const el = e.target;
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
                  }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !hasActiveWorkflow) { e.preventDefault(); handleSubmit(); } }}
                  rows={2}
                  aria-label="Task instruction"
                  className="w-full bg-transparent outline-none resize-none text-[13px] placeholder:text-theme-tertiary text-theme leading-relaxed min-h-[44px] max-h-[160px]"
                />
                )}
              </div>

              {/* Footer bar: model selector + reasoning + run */}
              <div className="flex items-center justify-between px-4 pb-3 pt-1">
                <div className="flex items-center gap-2">
                  <ModelSelector
                    conversationId={conversationId}
                    aiSettings={aiSettings}
                    onModelChange={handleModelChange}
                  />
                </div>
                {isRunning ? (
                  <button
                    onClick={handleStop}
                    disabled={stopping}
                    aria-label={stopping ? 'Stopping...' : 'Stop execution'}
                    className={cn(
                      'flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all duration-200 cursor-pointer',
                      stopping
                        ? 'bg-status-error-soft text-status-error/60 cursor-not-allowed'
                        : 'bg-status-error-soft hover:bg-status-error-soft text-status-error border border-status-error'
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
                    disabled={!prompt.trim() || hasActiveWorkflow}
                    aria-label="Run command"
                    className={cn(
                      'flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all duration-200',
                      prompt.trim()
                        ? 'bg-text-primary hover:opacity-90 text-text-inverse cursor-pointer'
                        : 'bg-surface-2 text-theme-tertiary cursor-not-allowed'
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

      {/* Right panel - Activity Drawer (desktop) */}
      {(isRunning || showActivityDrawer) && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 380, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: 'easeInOut' }}
          className="border-l border-theme flex flex-col shrink-0 bg-surface overflow-hidden lg:flex"
        >
          <div className="flex items-center gap-2 px-4 py-3 border-b border-theme">
            <Terminal size={12} className="text-theme-secondary" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">Execution Log</span>
            {wsConnected && (
              <div className="ml-auto flex items-center gap-1.5">
                <div className="w-1 h-1 rounded-full bg-status-active animate-pulse" />
                <span className="text-[9px] text-status-active font-medium">WS</span>
              </div>
            )}
          </div>
          <div className="flex-1 p-3 min-h-0">
            <LiveConsole logs={logs} wsConnected={wsConnected} />
          </div>
          {logs.length > 0 && (
            <div className="max-h-[200px] border-t border-theme p-3 overflow-y-auto">
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
      <DeleteConfirmDialog confirmation={deleteConfirm} onConfirm={handleDeleteConfirm} onCancel={handleDeleteCancel} />
    </div>
  );
}
