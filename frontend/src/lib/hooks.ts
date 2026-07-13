'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

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

export function useWebSocket(executionId: string | null) {
  const { token } = useAuth();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!executionId) return;
    const ws = new WebSocket(api.wsUrl(executionId, token));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => setLastEvent(JSON.parse(e.data));
    return () => { ws.close(); wsRef.current = null; };
  }, [executionId, token]);

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

  const search = useCallback(async (q: string) => {
    setQuery(q);
    if (q.length < 2 || !token) { setResults([]); return; }
    setLoading(true);
    try { const r = await api.searchFiles(q, token); setResults(r.results || []); }
    catch { setResults([]); }
    finally { setLoading(false); }
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
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getDashboard(token);
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
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { metrics, loading, error, refresh };
}
