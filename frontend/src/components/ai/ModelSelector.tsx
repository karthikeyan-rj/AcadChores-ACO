'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  ChevronDown, Cpu, Zap, Brain, AlertCircle, AlertTriangle,
  Check, Settings, Circle, CircleDot, Search, X, Link as LinkIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import type { AIProvider, AIModel, AICredential, AISettings } from '@/lib/ai-store';
import Link from 'next/link';

interface ModelSelectorProps {
  conversationId: string | null;
  aiSettings: AISettings | null;
  onModelChange?: (provider: string, model: string, credentialId: string | null, reasoningLevel: string) => void;
}

interface ResolvedModel {
  provider: string;
  model: string;
  modelLabel: string;
  providerLabel: string;
  credentialId: string | null;
  credentialLabel: string | null;
  reasoningLevel: string;
  isLocal: boolean;
  hasCredential: boolean;
}

const REASONING_LEVELS = [
  { id: 'fast', label: 'Fast', icon: Zap },
  { id: 'balanced', label: 'Balanced', icon: Cpu },
  { id: 'deep', label: 'Deep', icon: Brain },
];

function getLocalModels(models: Record<string, AIModel[]>): AIModel[] {
  return (models['ollama'] || []).map(m => ({ ...m, provider: 'ollama' }));
}

function getCloudProviders(providers: AIProvider[]): AIProvider[] {
  return providers.filter(p => p.id !== 'ollama');
}

function findDefaultLocalModel(models: Record<string, AIModel[]>): AIModel | null {
  const local = getLocalModels(models);
  if (local.length === 0) return null;
  return local.find(m => m.id.includes('qwen')) || local[0];
}

function resolveDefaultModel(
  aiSettings: AISettings | null,
  models: Record<string, AIModel[]>,
  credentials: AICredential[],
): ResolvedModel {
  const localOnly = aiSettings?.ai_local_only ?? true;

  if (localOnly) {
    const lm = findDefaultLocalModel(models);
    return {
      provider: 'ollama',
      model: lm?.id || '',
      modelLabel: lm?.name || 'Ollama',
      providerLabel: 'Local',
      credentialId: null,
      credentialLabel: null,
      reasoningLevel: aiSettings?.default_reasoning_level || 'balanced',
      isLocal: true,
      hasCredential: true,
    };
  }

  const defProvider = aiSettings?.default_provider || 'ollama';
  const defModel = aiSettings?.default_model || '';
  const defCred = aiSettings?.default_credential_id || null;

  if (defProvider !== 'ollama' && defModel) {
    const provModels = models[defProvider] || [];
    const m = provModels.find(mod => mod.id === defModel);
    const cred = credentials.find(c => c.id === defCred && c.is_active) || null;
    const anyCred = credentials.find(c => c.provider === defProvider && c.is_active) || null;
    return {
      provider: defProvider,
      model: defModel,
      modelLabel: m?.name || defModel,
      providerLabel: defProvider,
      credentialId: cred?.id || anyCred?.id || null,
      credentialLabel: cred?.label || anyCred?.label || null,
      reasoningLevel: aiSettings?.default_reasoning_level || 'balanced',
      isLocal: false,
      hasCredential: !!(cred || anyCred),
    };
  }

  const lm = findDefaultLocalModel(models);
  return {
    provider: 'ollama',
    model: lm?.id || '',
    modelLabel: lm?.name || 'Ollama',
    providerLabel: 'Local',
    credentialId: null,
    credentialLabel: null,
    reasoningLevel: aiSettings?.default_reasoning_level || 'balanced',
    isLocal: true,
    hasCredential: true,
  };
}

function resolveFromConversation(
  conversationId: string | null,
  allProviders: AIProvider[],
  models: Record<string, AIModel[]>,
  credentials: AICredential[],
  aiSettings: AISettings | null,
  conversationSelection: any,
): ResolvedModel | null {
  if (!conversationSelection) return null;
  const localOnly = aiSettings?.ai_local_only ?? true;
  const cp = conversationSelection.preferred_provider || 'ollama';
  const cm = conversationSelection.preferred_model || '';
  const ccId = conversationSelection.preferred_credential_id || null;
  const cr = conversationSelection.reasoning_level || 'balanced';

  if (localOnly && cp !== 'ollama') return null;

  const provModels = models[cp] || [];
  const m = provModels.find(mod => mod.id === cm);
  const cred = ccId ? credentials.find(c => c.id === ccId && c.is_active) : null;
  const anyCred = credentials.find(c => c.provider === cp && c.is_active) || null;

  return {
    provider: cp,
    model: cm,
    modelLabel: m?.name || cm || 'Local model',
    providerLabel: cp === 'ollama' ? 'Local' : cp,
    credentialId: cred?.id || anyCred?.id || null,
    credentialLabel: cred?.label || anyCred?.label || null,
    reasoningLevel: cr,
    isLocal: cp === 'ollama',
    hasCredential: cp === 'ollama' || !!(cred || anyCred),
  };
}

export default function ModelSelector({ conversationId, aiSettings, onModelChange }: ModelSelectorProps) {
  const { token } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [models, setModels] = useState<Record<string, AIModel[]>>({});
  const [credentials, setCredentials] = useState<AICredential[]>([]);
  const [selected, setSelected] = useState<ResolvedModel | null>(null);
  const [conversationSelection, setConversationSelection] = useState<any>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const localOnly = aiSettings?.ai_local_only ?? true;

  const loadData = useCallback(async () => {
    if (!token) return;
    try {
      const [provData, modelData, credData] = await Promise.all([
        api.getAIProviders(token),
        api.getAIModels(token),
        api.getAICredentials(token),
      ]);
      setProviders(provData.providers || []);
      setModels(modelData.models || {});
      setCredentials(credData.credentials || []);

      if (conversationId) {
        try {
          const conv = await api.getConversation(conversationId, token);
          setConversationSelection({
            preferred_provider: conv.preferred_provider,
            preferred_model: conv.preferred_model,
            preferred_credential_id: conv.preferred_credential_id,
            reasoning_level: conv.reasoning_level,
          });
        } catch {
          setConversationSelection(null);
        }
      } else {
        setConversationSelection(null);
      }
    } catch {}
  }, [token, conversationId]);

  useEffect(() => { loadData(); }, [loadData]);

  // Resolve selected model whenever data changes
  useEffect(() => {
    const conv = resolveFromConversation(conversationId, providers, models, credentials, aiSettings, conversationSelection);
    if (conv) {
      setSelected(conv);
    } else {
      setSelected(resolveDefaultModel(aiSettings, models, credentials));
    }
  }, [conversationId, providers, models, credentials, aiSettings, conversationSelection]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = useCallback(async (provider: string, model: string, credentialId: string | null, reasoning: string) => {
    const providerLabel = provider === 'ollama' ? 'Local' : provider;
    const provModels = models[provider] || [];
    const m = provModels.find(mod => mod.id === model);
    const cred = credentialId ? credentials.find(c => c.id === credentialId && c.is_active) : null;

    const newSel: ResolvedModel = {
      provider,
      model,
      modelLabel: m?.name || model || 'Local model',
      providerLabel,
      credentialId: cred?.id || credentialId,
      credentialLabel: cred?.label || null,
      reasoningLevel: reasoning,
      isLocal: provider === 'ollama',
      hasCredential: provider === 'ollama' || !!cred,
    };
    setSelected(newSel);
    setIsOpen(false);
    setSearch('');

    if (conversationId && token) {
      try {
        await api.setConversationModel(conversationId, {
          preferred_provider: provider,
          preferred_model: model || undefined,
          preferred_credential_id: credentialId || undefined,
          reasoning_level: reasoning,
        }, token);
      } catch {}
    }
    onModelChange?.(provider, model, credentialId, reasoning);
  }, [conversationId, models, credentials, token, onModelChange]);

  // Handle selecting cloud model when no credential
  const handleSelectCloudNoCred = useCallback((provider: string, model: string, reasoning: string) => {
    const providerLabel = provider;
    const provModels = models[provider] || [];
    const m = provModels.find(mod => mod.id === model);
    const newSel: ResolvedModel = {
      provider,
      model,
      modelLabel: m?.name || model,
      providerLabel,
      credentialId: null,
      credentialLabel: null,
      reasoningLevel: reasoning,
      isLocal: false,
      hasCredential: false,
    };
    setSelected(newSel);
    setIsOpen(false);
    setSearch('');
    onModelChange?.(provider, model, null, reasoning);
  }, [models, onModelChange]);

  // Group models by provider for dropdown
  const groupedModels = useMemo(() => {
    const groups: Record<string, { provider: AIProvider; models: AIModel[]; credential: AICredential | null }> = {};
    const allProviders = localOnly
      ? providers.filter(p => p.id === 'ollama')
      : providers;

    for (const prov of allProviders) {
      const provModels = (models[prov.id] || []).filter(m => {
        if (!search) return true;
        const q = search.toLowerCase();
        return m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q) || prov.id.includes(q);
      });
      if (provModels.length === 0 && search) continue;
      const cred = credentials.find(c => c.provider === prov.id && c.is_active) || null;
      groups[prov.id] = { provider: prov, models: provModels, credential: cred };
    }
    return groups;
  }, [providers, models, credentials, localOnly, search]);

  const formatLabel = (m: AIModel) => {
    if (m.context_length) {
      const k = Math.round(m.context_length / 1000);
      return `${k}k`;
    }
    return '';
  };

  if (!selected) return null;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] rounded-lg border transition cursor-pointer max-w-[260px]',
          !selected.hasCredential && !selected.isLocal
            ? 'border-status-error bg-status-error-soft text-status-error'
            : 'border-theme bg-surface-2 text-theme-secondary hover:bg-surface-hover hover:text-theme'
        )}
      >
        {selected.isLocal ? (
          <CircleDot size={11} className="text-status-active shrink-0" />
        ) : selected.hasCredential ? (
          <Circle size={11} className="text-theme-tertiary shrink-0" />
        ) : (
          <AlertTriangle size={11} className="text-status-error shrink-0" />
        )}
        <span className="font-medium truncate">{selected.providerLabel}</span>
        <span className="text-theme-tertiary">{'\u00b7'}</span>
        <span className="truncate">{selected.modelLabel}</span>
        <ChevronDown size={11} className={cn('shrink-0 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-[400px] bg-surface border border-theme rounded-xl shadow-theme-dropdown overflow-hidden z-50">
          {/* Search */}
          <div className="p-2 border-b border-theme">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-theme-tertiary" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search models\u2026"
                className="w-full pl-8 pr-8 py-1.5 text-[11px] bg-input border border-theme rounded-lg outline-none text-theme placeholder:text-theme-tertiary focus:border-theme-strong"
                autoFocus
              />
              {search && (
                <button onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-theme-tertiary hover:text-theme cursor-pointer">
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Model groups */}
          <div className="max-h-[280px] overflow-y-auto">
            {Object.entries(groupedModels).length === 0 ? (
              <div className="p-4 text-center text-[11px] text-theme-tertiary">No models found</div>
            ) : (
              Object.entries(groupedModels).map(([provId, { provider, models: provModels, credential }]) => (
                <div key={provId} className="border-b border-theme last:border-b-0">
                  {/* Provider header */}
                  <div className="flex items-center justify-between px-3 py-1.5 bg-surface-2/50">
                    <div className="flex items-center gap-1.5">
                      {provId === 'ollama' ? (
                        <CircleDot size={10} className="text-status-active" />
                      ) : provider.available ? (
                        <Circle size={10} className="text-status-active" />
                      ) : (
                        <Circle size={10} className="text-theme-tertiary" />
                      )}
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-theme-secondary">
                        {provId === 'ollama' ? 'Local' : provider.name}
                      </span>
                    </div>
                    {credential && (
                      <span className="text-[9px] text-theme-tertiary px-1.5 py-0.5 rounded bg-surface-2">
                        {credential.label || credential.key_hint}
                      </span>
                    )}
                    {!credential && provId !== 'ollama' && (
                      <span className="text-[9px] text-status-error px-1.5 py-0.5 rounded bg-status-error-soft">
                        No key
                      </span>
                    )}
                  </div>

                  {/* Models */}
                  {provModels.map(m => {
                    const isSelected = selected.provider === provId && selected.model === m.id;
                    const needsCred = provId !== 'ollama' && !credential;
                    return (
                      <button
                        key={m.id}
                        onClick={() => {
                          if (needsCred) {
                            handleSelectCloudNoCred(provId, m.id, selected.reasoningLevel);
                          } else {
                            handleSelect(provId, m.id, credential?.id || null, selected.reasoningLevel);
                          }
                        }}
                        className={cn(
                          'w-full flex items-center justify-between px-3 py-2 text-[11px] transition cursor-pointer text-left',
                          isSelected
                            ? 'bg-surface-hover text-theme'
                            : 'text-theme-secondary hover:bg-surface-hover hover:text-theme'
                        )}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          {isSelected && <Check size={11} className="text-theme shrink-0" />}
                          <span className="truncate font-medium">{m.name}</span>
                          {needsCred && (
                            <span className="text-[9px] text-status-error shrink-0">API key required</span>
                          )}
                        </div>
                        <span className="text-[9px] text-theme-tertiary shrink-0 ml-2">
                          {formatLabel(m)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ))
            )}

            {/* Local-only cloud disabled hint */}
            {localOnly && getCloudProviders(providers).length > 0 && (
              <div className="px-3 py-2 bg-surface-2/30 border-t border-theme">
                <p className="text-[10px] text-theme-tertiary flex items-center gap-1.5">
                  <AlertCircle size={11} />
                  Cloud providers disabled by Local-only mode
                  <Link href="/settings" className="text-theme underline ml-auto">Manage in Settings</Link>
                </p>
              </div>
            )}
          </div>

          {/* Reasoning level */}
          <div className="p-2 border-t border-theme">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary px-1">Reasoning</span>
            </div>
            <div className="flex gap-1">
              {REASONING_LEVELS.map(level => {
                const Icon = level.icon;
                return (
                  <button
                    key={level.id}
                    onClick={() => {
                      if (selected) {
                        handleSelect(selected.provider, selected.model, selected.credentialId, level.id);
                      }
                    }}
                    className={cn(
                      'flex items-center gap-1 px-2.5 py-1.5 text-[11px] rounded-lg border transition cursor-pointer',
                      selected?.reasoningLevel === level.id
                        ? 'border-theme-strong bg-surface-hover text-theme font-medium'
                        : 'border-theme bg-surface-2 text-theme-secondary hover:bg-surface-hover'
                    )}
                  >
                    <Icon size={11} />
                    {level.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Missing key CTA */}
          {!selected.hasCredential && !selected.isLocal && (
            <div className="p-2 border-t border-theme bg-status-error-soft/50">
              <div className="flex items-center gap-2">
                <AlertCircle size={12} className="text-status-error shrink-0" />
                <span className="text-[10px] text-status-error">No API key configured for {selected.providerLabel}</span>
                <Link href="/settings" className="text-[10px] text-theme underline ml-auto shrink-0">Add key</Link>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
