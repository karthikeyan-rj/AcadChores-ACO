'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { getCached, setCache, STALE_TIMES } from '@/lib/cache';

export function useBackendHealth() {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const check = async () => setConnected(await api.health());
    check();
    const i = setInterval(check, 5000);
    return () => clearInterval(i);
  }, []);
  return connected;
}

const WS_MAX_RECONNECT_ATTEMPTS = 5;
const WS_BASE_DELAY_MS = 1000;
const WS_MAX_DELAY_MS = 30000;

export function useWebSocket(executionId: string | null) {
  const { token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const cleanup = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
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
  }, []);

  const connect = useCallback(() => {
    cleanup();
    if (!executionId || !token || unmountedRef.current) return;

    const ws = new WebSocket(api.wsUrl(executionId, token));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onclose = (event) => {
      setConnected(false);
      wsRef.current = null;
      if (unmountedRef.current) return;
      if (!token || event.code === 1000 || event.code === 4001 || event.code === 4003) return;
      if (reconnectAttempts.current >= WS_MAX_RECONNECT_ATTEMPTS) return;
      const delay = Math.min(
        WS_BASE_DELAY_MS * Math.pow(2, reconnectAttempts.current),
        WS_MAX_DELAY_MS
      );
      reconnectAttempts.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {};

    ws.onmessage = (e) => {
      try { setLastEvent(JSON.parse(e.data)); } catch {}
    };
  }, [executionId, token, cleanup]);

  useEffect(() => {
    unmountedRef.current = false;
    reconnectAttempts.current = 0;
    connect();
    return () => {
      unmountedRef.current = true;
      cleanup();
    };
  }, [connect, cleanup]);

  return { connected, lastEvent };
}

export function useExecutions() {
  const { token } = useAuth();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try { setData(await api.getExecutions(token)); }
    catch { setData([]); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);
  return { data, loading, refresh };
}

export function useFileSearch() {
  const { token } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(async (q: string) => {
    setQuery(q);
    if (q.length < 2 || !token) { setResults([]); return; }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      const r = await api.searchFiles(q, token);
      if (!controller.signal.aborted) setResults(r.results || []);
    } catch { if (!controller.signal.aborted) setResults([]); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [token]);

  return { query, results, loading, search };
}

export function useIndexConfig() {
  const { token } = useAuth();
  const [config, setConfig] = useState<any>(null);
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getIndexConfig(token);
      setConfig(data.config);
      setExists(data.exists);
    } catch { setConfig(null); setExists(false); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  const updateConfig = useCallback(async (update: any) => {
    if (!token) return;
    await api.updateIndexConfig(update, token);
    await refresh();
  }, [token, refresh]);

  return { config, exists, loading, refresh, updateConfig };
}

export function useIndexJobs() {
  const { token } = useAuth();
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getIndexJobs(token);
      setJobs(data.jobs || []);
    } catch { setJobs([]); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => {
    refresh();
    const i = setInterval(refresh, 5000);
    return () => clearInterval(i);
  }, [refresh]);

  const triggerIndex = useCallback(async () => {
    if (!token) return;
    await api.triggerIndex(token);
    await refresh();
  }, [token, refresh]);

  return { jobs, loading, refresh, triggerIndex };
}

export function useIndexStats() {
  const { token } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getIndexStats(token);
      setStats(data);
    } catch { setStats(null); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  return { stats, loading, refresh };
}

export function useDashboardMetrics() {
  const { token } = useAuth();
  const [metrics, setMetrics] = useState<any>(() => getCached('dashboard', STALE_TIMES.DASHBOARD));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    const cached = getCached('dashboard', STALE_TIMES.DASHBOARD);
    if (cached) { setMetrics(cached); setLoading(false); return; }
    try {
      const data = await api.getDashboard(token);
      setCache('dashboard', data, STALE_TIMES.DASHBOARD);
      setMetrics(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch dashboard metrics');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30_000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { metrics, loading, error, refresh };
}
