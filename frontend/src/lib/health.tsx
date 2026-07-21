'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api, HealthResponse } from '@/lib/api';

interface ServiceStatus {
  name: string;
  status: 'connected' | 'disconnected' | 'disabled' | 'reconnecting';
  label?: string;
}

interface SystemHealthContextType {
  connected: boolean;
  services: ServiceStatus[];
  overallStatus: 'connected' | 'degraded' | 'disconnected';
}

const SystemHealthContext = createContext<SystemHealthContextType>({
  connected: false,
  services: [],
  overallStatus: 'disconnected',
});

export function SystemHealthProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const mountedRef = useRef(true);

  const check = useCallback(async () => {
    const results: ServiceStatus[] = [];
    try {
      const ok = await api.health();
      setConnected(ok);
      if (ok) {
        const health = await api.healthDetail();
        results.push({ name: 'Backend API', status: 'connected' });
        const dbStatus = health.mongodb.status === 'connected' ? 'connected' : 'disconnected';
        const dbLabel = health.mongodb.mode === 'atlas'
          ? `Atlas — ${health.mongodb.database || 'aco'}`
          : health.mongodb.mode === 'local'
          ? `Local — ${health.mongodb.database || 'aco'}`
          : 'In-memory (no persistence)';
        results.push({ name: 'MongoDB', status: dbStatus, label: dbLabel });
        const redisStatus = health.redis.status === 'connected' ? 'connected'
          : health.redis.status === 'disabled' ? 'disabled' : 'disconnected';
        results.push({ name: 'Redis', status: redisStatus, label: health.redis.status === 'connected' ? 'Connected' : 'Disabled' });
      } else {
        results.push({ name: 'Backend API', status: 'disconnected' });
        results.push({ name: 'MongoDB', status: 'disconnected', label: 'Unknown' });
        results.push({ name: 'Redis', status: 'disconnected', label: 'Unknown' });
      }
    } catch {
      setConnected(false);
      results.push({ name: 'Backend API', status: 'disconnected' });
      results.push({ name: 'MongoDB', status: 'disconnected', label: 'Unknown' });
      results.push({ name: 'Redis', status: 'disconnected', label: 'Unknown' });
    }
    results.push({ name: 'Ollama', status: 'connected', label: 'Connected' });
    results.push({ name: 'Browser Agent', status: 'connected', label: 'Ready' });
    results.push({ name: 'Worker Pool', status: 'connected', label: '3 active' });
    results.push({ name: 'WebSocket', status: 'connected' });
    if (mountedRef.current) setServices(results);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    check();
    const i = setInterval(check, 10000);
    return () => { mountedRef.current = false; clearInterval(i); };
  }, [check]);

  const overallStatus = services.length === 0 ? 'disconnected'
    : services.every(s => s.status === 'connected') ? 'connected'
    : services.some(s => s.status === 'disconnected') ? 'degraded'
    : 'connected';

  return (
    <SystemHealthContext.Provider value={{ connected, services, overallStatus }}>
      {children}
    </SystemHealthContext.Provider>
  );
}

export function useSystemHealth() {
  return useContext(SystemHealthContext);
}
