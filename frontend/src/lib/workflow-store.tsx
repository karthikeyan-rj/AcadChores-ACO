'use client';

import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { mergeTimeline, TimelineItem } from '@/lib/timeline';

export interface TaskStep {
  step_id: string;
  name: string;
  agent_type: string;
  action: string;
  parameters?: any;
}

export interface LogMessage {
  time: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

export type { TimelineItem } from '@/lib/timeline';

const MAX_LOGS = 500;

interface WorkflowStoreValue {
  execId: string | null;
  status: string;
  plan: TaskStep[];
  stepIdx: number;
  logs: LogMessage[];
  result: string | null;
  selectedStep: number | null;
  startTime: number | null;
  stopping: boolean;
  hasActiveWorkflow: boolean;
  lastUserPrompt: string;
  chatHistory: TimelineItem[];
  conversationId: string | null;
  chatLoading: boolean;
  wsConnected: boolean;
  lastEvent: any;

  setExecId: (id: string | null) => void;
  setStatus: (s: string) => void;
  setPlan: (p: TaskStep[]) => void;
  setStepIdx: (i: number | ((prev: number) => number)) => void;
  addLog: (time: string, message: string, level?: LogMessage['level']) => void;
  setLogs: (l: LogMessage[] | ((prev: LogMessage[]) => LogMessage[])) => void;
  setResult: (r: string | null) => void;
  setSelectedStep: (s: number | null) => void;
  setStartTime: (t: number | null) => void;
  setStopping: (s: boolean) => void;
  setHasActiveWorkflow: (h: boolean) => void;
  setLastUserPrompt: (p: string) => void;
  setChatHistory: (h: TimelineItem[] | ((prev: TimelineItem[]) => TimelineItem[])) => void;
  setConversationId: (id: string | null) => void;
  setChatLoading: (l: boolean) => void;
  handleNewChat: () => void;
  restoreActiveWorkflow: () => Promise<void>;
  restoreConversation: () => Promise<void>;
}

const WorkflowStoreContext = createContext<WorkflowStoreValue | null>(null);

export function useWorkflowStore(): WorkflowStoreValue {
  const ctx = useContext(WorkflowStoreContext);
  if (!ctx) throw new Error('useWorkflowStore must be used within WorkflowProvider');
  return ctx;
}

export function WorkflowProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();

  const [execId, setExecId] = useState<string | null>(null);
  const [status, setStatus] = useState('Idle');
  const [plan, setPlan] = useState<TaskStep[]>([]);
  const [stepIdx, setStepIdx] = useState(-1);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [result, setResult] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const [hasActiveWorkflow, setHasActiveWorkflow] = useState(false);
  const [lastUserPrompt, setLastUserPrompt] = useState('');
  const [chatHistory, setChatHistory] = useState<TimelineItem[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const execIdRef = useRef(execId);
  const tokenRef = useRef(token);
  const restoredRef = useRef(false);

  execIdRef.current = execId;
  tokenRef.current = token;

  const addLog = useCallback((time: string, message: string, level: LogMessage['level'] = 'info') => {
    setLogs(prev => {
      const next = [...prev, { time, message, level }];
      return next.length > MAX_LOGS ? next.slice(next.length - MAX_LOGS) : next;
    });
  }, []);

  // Persist active exec to localStorage
  useEffect(() => {
    if (execId && (status === 'Planning' || status === 'Executing' || status === 'Waiting' || status === 'Stopping')) {
      try { localStorage.setItem('aco_active_exec', execId); } catch {}
    } else if (['Completed', 'Failed', 'Cancelled'].includes(status) || status === 'Idle') {
      try { localStorage.removeItem('aco_active_exec'); } catch {}
      setHasActiveWorkflow(false);
    }
  }, [execId, status]);

  // Persist conversationId to localStorage
  useEffect(() => {
    if (conversationId) {
      try { localStorage.setItem('aco_chat_conv_id', conversationId); } catch {}
    } else {
      try { localStorage.removeItem('aco_chat_conv_id'); } catch {}
    }
  }, [conversationId]);

  // WebSocket connection
  const connectWs = useCallback((id: string | null) => {
    if (wsRef.current) {
      const old = wsRef.current;
      wsRef.current = null;
      old.onclose = null;
      old.onerror = null;
      old.onopen = null;
      old.onmessage = null;
      if (old.readyState === WebSocket.OPEN || old.readyState === WebSocket.CONNECTING) {
        old.close(1000, 'reconnect');
      }
    }
    setWsConnected(false);

    if (!id || !token) return;

    const ws = new WebSocket(api.wsUrl(id, token));
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onclose = (event) => {
      setWsConnected(false);
      wsRef.current = null;
      if (!token || event.code === 1000 || event.code === 4001 || event.code === 4003) return;
      if (reconnectAttempts.current >= 5) return;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;
      reconnectTimer.current = setTimeout(() => connectWs(execIdRef.current), delay);
    };

    ws.onerror = () => {};

    ws.onmessage = (e) => {
      try { setLastEvent(JSON.parse(e.data)); } catch {}
    };
  }, [token]);

  // Connect/disconnect WS when execId changes
  useEffect(() => {
    reconnectAttempts.current = 0;
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    connectWs(execId);
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.onopen = null;
        ws.onmessage = null;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close(1000, 'cleanup');
        }
      }
    };
  }, [execId, connectWs]);

  // Restore active workflow on mount
  const restoreActiveWorkflow = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getActiveWorkflow(token);
      if (data.success && data.active) {
        const exec = data.active;
        const id = exec._id;
        setExecId(id);
        setStatus(exec.status);
        setHasActiveWorkflow(true);
        if (exec.total_steps) setStepIdx(exec.current_step_index ?? 0);
        if (exec.title) setLastUserPrompt(exec.description || exec.title);
        if (exec.steps && Array.isArray(exec.steps)) {
          setPlan(exec.steps.map((s: any) => ({
            step_id: s.step_id || s.id || '',
            name: s.name || s.step_id || '',
            agent_type: s.agent_type || '',
            action: s.action || '',
            parameters: s.parameters,
          })));
        }
        try { localStorage.setItem('aco_active_exec', id); } catch {}

        // Restore logs
        try {
          const logsData = await api.getExecutionLogs(id, token);
          if (Array.isArray(logsData)) {
            setLogs(logsData.map((l: any) => ({
              time: l.created_at || '',
              message: l.logs || `${l.action}: ${l.status}`,
              level: l.status === 'failure' ? 'error' as const : 'info' as const,
            })));
          }
        } catch {}
        return;
      }

      // No active workflow from backend; try localStorage
      const savedExecId = (() => { try { return localStorage.getItem('aco_active_exec'); } catch { return null; } })();
      if (savedExecId) {
        try {
          const exec = await api.getExecution(savedExecId, token);
          if (exec && ['Executing', 'Planning', 'Waiting'].includes(exec.status)) {
            setExecId(savedExecId);
            setStatus(exec.status);
            setHasActiveWorkflow(true);
            if (exec.total_steps) setStepIdx(exec.current_step_index ?? 0);
            if (exec.title) setLastUserPrompt(exec.description || exec.title);

            try {
              const logsData = await api.getExecutionLogs(savedExecId, token);
              if (Array.isArray(logsData)) {
                setLogs(logsData.map((l: any) => ({
                  time: l.created_at || '',
                  message: l.logs || `${l.action}: ${l.status}`,
                  level: l.status === 'failure' ? 'error' as const : 'info' as const,
                })));
              }
            } catch {}
            return;
          }
        } catch {}
        try { localStorage.removeItem('aco_active_exec'); } catch {}
      }
    } catch {
      const savedExecId = (() => { try { return localStorage.getItem('aco_active_exec'); } catch { return null; } })();
      if (savedExecId) {
        try {
          const exec = await api.getExecution(savedExecId, token);
          if (exec && ['Executing', 'Planning', 'Waiting'].includes(exec.status)) {
            setExecId(savedExecId);
            setStatus(exec.status);
            setHasActiveWorkflow(true);
            if (exec.total_steps) setStepIdx(exec.current_step_index ?? 0);
            if (exec.title) setLastUserPrompt(exec.description || exec.title);
          } else {
            try { localStorage.removeItem('aco_active_exec'); } catch {}
          }
        } catch {
          try { localStorage.removeItem('aco_active_exec'); } catch {}
        }
      }
    }
  }, [token]);

  // Restore conversation on mount — fetches messages AND workflow executions, merges chronologically
  const restoreConversation = useCallback(async () => {
    if (!token) return;
    const savedConvId = (() => { try { return localStorage.getItem('aco_chat_conv_id'); } catch { return null; } })();
    if (savedConvId) {
      setConversationId(savedConvId);
      try {
        const [convData, wfData]: any[] = await Promise.all([
          api.getConversation(savedConvId, token).catch(() => ({ messages: [] })),
          api.getConversationWorkflows(savedConvId, token).catch(() => ({ workflows: [] })),
        ]);

        const messages = convData.messages || [];
        const workflows = wfData.workflows || [];
        const merged = mergeTimeline(messages, workflows);
        if (merged.length > 0) {
          setChatHistory(merged);
        }
      } catch {}
    }
  }, [token]);

  // Single restoration on mount
  useEffect(() => {
    if (!token || restoredRef.current) return;
    restoredRef.current = true;
    restoreActiveWorkflow();
    restoreConversation();
  }, [token, restoreActiveWorkflow, restoreConversation]);

  const handleNewChat = useCallback(() => {
    setConversationId(null);
    setChatHistory([]);
    setPlan([]);
    setStepIdx(-1);
    setLogs([]);
    setResult(null);
    setSelectedStep(null);
    setStatus('Idle');
    setExecId(null);
    setHasActiveWorkflow(false);
    setStopping(false);
    setLastUserPrompt('');
    try { localStorage.removeItem('aco_chat_conv_id'); } catch {}
    try { localStorage.removeItem('aco_active_exec'); } catch {}
  }, []);

  const value = useMemo<WorkflowStoreValue>(() => ({
    execId, status, plan, stepIdx, logs, result, selectedStep, startTime,
    stopping, hasActiveWorkflow, lastUserPrompt, chatHistory, conversationId,
    chatLoading, wsConnected, lastEvent,
    setExecId, setStatus, setPlan, setStepIdx, addLog, setLogs, setResult,
    setSelectedStep, setStartTime, setStopping, setHasActiveWorkflow,
    setLastUserPrompt, setChatHistory, setConversationId, setChatLoading,
    handleNewChat, restoreActiveWorkflow, restoreConversation,
  }), [
    execId, status, plan, stepIdx, logs, result, selectedStep, startTime,
    stopping, hasActiveWorkflow, lastUserPrompt, chatHistory, conversationId,
    chatLoading, wsConnected, lastEvent, addLog, handleNewChat,
    restoreActiveWorkflow, restoreConversation,
  ]);

  return (
    <WorkflowStoreContext.Provider value={value}>
      {children}
    </WorkflowStoreContext.Provider>
  );
}
