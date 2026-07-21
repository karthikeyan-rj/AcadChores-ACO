'use client';

import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AIProvider {
  id: string;
  name: string;
  available: boolean;
  latency_ms: number;
  error: string | null;
  capabilities: {
    supports_streaming: boolean;
    supports_embeddings: boolean;
    supports_model_discovery: boolean;
    supports_structured_output: boolean;
    supports_reasoning: boolean;
    supports_tools: boolean;
    supports_vision: boolean;
  };
}

export interface AIModel {
  id: string;
  provider: string;
  name: string;
  context_length: number | null;
  supports_structured_output: boolean;
  supports_reasoning: boolean;
  supports_vision: boolean;
  supports_tools: boolean;
  supports_embeddings: boolean;
  source: 'static' | 'dynamic';
}

export interface AICredential {
  id: string;
  provider: string;
  label: string;
  key_hint: string;
  is_active: boolean;
  is_default: boolean;
  validated_at: string | null;
  created_at: string | null;
}

export interface AISettings {
  ai_local_only: boolean;
  fallback_to_local: boolean;
  default_provider: string;
  default_model: string;
  default_credential_id: string | null;
  default_reasoning_level: string;
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useAIProviders() {
  const { token } = useAuth();
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.getAIProviders(token);
      setProviders(data.providers || []);
    } catch {
      setProviders([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);
  return { providers, loading, refresh: load };
}

export function useAIModels(providerId?: string) {
  const { token } = useAuth();
  const [models, setModels] = useState<Record<string, AIModel[]>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.getAIModels(token, providerId);
      setModels(data.models || {});
    } catch {
      setModels({});
    } finally {
      setLoading(false);
    }
  }, [token, providerId]);

  useEffect(() => { load(); }, [load]);
  return { models, loading, refresh: load };
}

export function useAICredentials() {
  const { token } = useAuth();
  const [credentials, setCredentials] = useState<AICredential[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.getAICredentials(token);
      setCredentials(data.credentials || []);
    } catch {
      setCredentials([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);
  return { credentials, loading, refresh: load };
}

export function useAISettings() {
  const { token } = useAuth();
  const [settings, setSettings] = useState<AISettings>({
    ai_local_only: true,
    fallback_to_local: true,
    default_provider: 'ollama',
    default_model: '',
    default_credential_id: null,
    default_reasoning_level: 'balanced',
  });
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await api.getAISettings(token);
      setSettings(data);
    } catch {
      // keep defaults
    } finally {
      setLoading(false);
    }
  }, [token]);

  const update = useCallback(async (patch: Partial<AISettings>) => {
    if (!token) return;
    const data = await api.updateAISettings(patch, token);
    setSettings(data);
  }, [token]);

  useEffect(() => { load(); }, [load]);
  return { settings, loading, update, refresh: load };
}
