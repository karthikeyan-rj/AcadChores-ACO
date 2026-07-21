'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings, Cpu, Info, Save, Check, Loader2, Eye, EyeOff, Trash2,
  AlertCircle, Monitor, Moon, Sun, Shield, Plus, RefreshCw, Key,
  Circle, CircleDot, AlertTriangle, ChevronDown, X, Pencil, CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { useTheme } from '@/lib/theme';
import { api } from '@/lib/api';
import type { AIProvider, AIModel, AICredential, AISettings } from '@/lib/ai-store';

type SettingsTab = 'providers' | 'ai' | 'about';

const tabs: { id: SettingsTab; label: string; icon: any }[] = [
  { id: 'providers', label: 'AI Providers', icon: Shield },
  { id: 'ai', label: 'Cloud Fallback', icon: Cpu },
  { id: 'about', label: 'About', icon: Info },
];

const THEME_OPTIONS = [
  {
    id: 'dark' as const,
    label: 'Dark Professional',
    description: 'Deep neutral surfaces with restrained contrast',
    icon: Moon,
    previewBg: '#0B0D11',
    previewSurface: '#141820',
    previewAccent: '#F2F4F7',
    previewBorder: '#272E39',
  },
  {
    id: 'light' as const,
    label: 'Nordic Alabaster',
    description: 'Warm light surfaces with minimal contrast',
    icon: Sun,
    previewBg: '#F9F9F6',
    previewSurface: '#FFFFFF',
    previewAccent: '#1A1A1A',
    previewBorder: '#E5E5E0',
  },
  {
    id: 'system' as const,
    label: 'System Theme',
    description: 'Follows your operating system preference',
    icon: Monitor,
    previewBg: null,
    previewSurface: null,
    previewAccent: null,
    previewBorder: null,
  },
];

const CLOUD_PROVIDERS = ['openai', 'groq', 'mistral', 'openrouter', 'cohere'];
const CLOUD_PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI', groq: 'Groq', mistral: 'Mistral', openrouter: 'OpenRouter', cohere: 'Cohere',
};

interface UserSettings {
  cloud_fallback_enabled: boolean;
  cloud_provider: string;
  cloud_model: string;
  api_key_configured: boolean;
  api_key_hint: string | null;
  workflow_quality_threshold: number;
  local_planner_retry_count: number;
}

const DEFAULT_SETTINGS: UserSettings = {
  cloud_fallback_enabled: false,
  cloud_provider: 'openai',
  cloud_model: 'gpt-4o-mini',
  api_key_configured: false,
  api_key_hint: null,
  workflow_quality_threshold: 70,
  local_planner_retry_count: 1,
};

export default function SettingsPage() {
  const { token } = useAuth();
  const { theme, setTheme } = useTheme();
  const [tab, setTab] = useState<SettingsTab>('providers');
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [dirty, setDirty] = useState(false);

  const loadSettings = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSettings(token);
      setSettings({
        cloud_fallback_enabled: data.cloud_fallback_enabled,
        cloud_provider: data.cloud_provider,
        cloud_model: data.cloud_model,
        api_key_configured: data.api_key_configured,
        api_key_hint: data.api_key_hint,
        workflow_quality_threshold: data.workflow_quality_threshold,
        local_planner_retry_count: data.local_planner_retry_count,
      });
      setDirty(false);
    } catch (e: any) {
      setError(e.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const handleSave = async () => {
    if (!token || !dirty) return;
    setSaving(true);
    setSaveSuccess(false);
    setError(null);
    try {
      const payload: Record<string, any> = {
        cloud_fallback_enabled: settings.cloud_fallback_enabled,
        cloud_provider: settings.cloud_provider,
        cloud_model: settings.cloud_model,
        workflow_quality_threshold: settings.workflow_quality_threshold,
        local_planner_retry_count: settings.local_planner_retry_count,
      };
      await api.updateSettings(payload, token);
      setDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e: any) {
      setError(e.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateField = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  return (
    <div className="p-6 max-w-[1000px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-theme">Settings</h1>
          <p className="text-xs text-theme-tertiary mt-0.5">Configure your ACO environment</p>
        </div>
        {tab === 'ai' && (
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition cursor-pointer',
              dirty && !saving
                ? 'bg-theme text-theme-inverse hover:bg-surface-elevated'
                : 'bg-surface-2 text-theme-tertiary cursor-not-allowed'
            )}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : saveSuccess ? <Check size={14} /> : <Save size={14} />}
            {saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save Changes'}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 px-4 py-3 rounded-lg bg-status-error-soft border border-status-error text-status-error text-xs">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      <div className="flex gap-5">
        <div className="w-[180px] shrink-0 bg-surface-2 border border-theme rounded-lg p-0.5 space-y-0.5">
          {tabs.map(t => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition cursor-pointer',
                  tab === t.id ? 'bg-surface-hover text-theme' : 'text-theme-secondary hover:text-theme hover:bg-surface-hover'
                )}>
                <Icon size={14} />{t.label}
              </button>
            );
          })}
        </div>

        <div className="flex-1 rounded-[14px] border border-theme bg-surface p-6 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.15 }}>

              {tab === 'providers' && (
                <ProvidersTab />
              )}

              {tab === 'ai' && (
                <div className="space-y-6">
                  <Section title="Appearance">
                    <p className="text-xs text-theme-secondary mb-3">Choose how ACO looks on this device.</p>
                    <div className="grid grid-cols-3 gap-3">
                      {THEME_OPTIONS.map((opt) => {
                        const isSelected = theme === opt.id;
                        const Icon = opt.icon;
                        return (
                          <button
                            key={opt.id}
                            onClick={() => setTheme(opt.id)}
                            className={cn(
                              'relative flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all duration-150 cursor-pointer text-center',
                              isSelected
                                ? 'border-theme-strong bg-surface-hover'
                                : 'border-theme bg-surface-2 hover:bg-surface-hover hover:border-theme-strong'
                            )}
                          >
                            {opt.previewBg ? (
                              <div className="w-full h-14 rounded-lg overflow-hidden relative" style={{ backgroundColor: opt.previewBg }}>
                                <div className="absolute top-0 left-0 right-0 h-3" style={{ backgroundColor: opt.previewSurface }} />
                                <div className="absolute bottom-0 left-2 right-2 h-2 rounded-sm" style={{ backgroundColor: opt.previewBorder }} />
                                <div className="absolute top-4 left-1/2 -translate-x-1/2 w-6 h-1 rounded-full" style={{ backgroundColor: opt.previewAccent }} />
                              </div>
                            ) : (
                              <div className="w-full h-14 rounded-lg overflow-hidden relative bg-gradient-to-br from-[#0B0D11] to-[#F9F9F6] flex items-center justify-center">
                                <div className="w-5 h-5 rounded-full border-2 border-theme overflow-hidden flex">
                                  <div className="w-1/2 h-full bg-[#0B0D11]" />
                                  <div className="w-1/2 h-full bg-[#F9F9F6]" />
                                </div>
                              </div>
                            )}
                            <div className="flex flex-col items-center gap-0.5">
                              <span className="text-[11px] font-medium text-theme">{opt.label}</span>
                              <span className="text-[9px] text-theme-tertiary leading-tight">{opt.description}</span>
                            </div>
                            {isSelected && (
                              <div className="absolute top-2.5 right-2.5 w-5 h-5 rounded-full bg-theme flex items-center justify-center">
                                <Check size={11} className="text-theme-inverse" />
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </Section>

                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 size={24} className="animate-spin text-theme-tertiary" />
                    </div>
                  ) : (
                    <>
                      <Section title="Cloud Fallback">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs text-theme-secondary">Enable cloud fallback when local planner quality is low</span>
                            <p className="text-[10px] text-theme-tertiary mt-0.5">Falls back to cloud API if Ollama output quality is below threshold</p>
                          </div>
                          <button onClick={() => updateField('cloud_fallback_enabled', !settings.cloud_fallback_enabled)}
                            className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative',
                              settings.cloud_fallback_enabled ? 'bg-theme' : 'bg-surface-2')}>
                            <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-surface transition-transform',
                              settings.cloud_fallback_enabled ? 'left-[18px]' : 'left-0.5')} />
                          </button>
                        </div>
                      </Section>

                      <Section title="Planning">
                        <Field label={`Quality Threshold (${settings.workflow_quality_threshold})`}>
                          <div className="flex items-center gap-3">
                            <input type="range" min={50} max={100} value={settings.workflow_quality_threshold}
                              onChange={(e) => updateField('workflow_quality_threshold', parseInt(e.target.value))}
                              className="flex-1 accent-[var(--text-primary)]" />
                            <span className="text-xs text-theme-secondary w-8 text-right">{settings.workflow_quality_threshold}</span>
                          </div>
                          <p className="text-[10px] text-theme-tertiary mt-1">Minimum quality score (50\u2013100) for local planner output before cloud fallback triggers</p>
                        </Field>
                        <Field label={`Local Retry Count (${settings.local_planner_retry_count})`}>
                          <div className="flex items-center gap-3">
                            <input type="range" min={0} max={3} value={settings.local_planner_retry_count}
                              onChange={(e) => updateField('local_planner_retry_count', parseInt(e.target.value))}
                              className="flex-1 accent-[var(--text-primary)]" />
                            <span className="text-xs text-theme-secondary w-8 text-right">{settings.local_planner_retry_count}</span>
                          </div>
                          <p className="text-[10px] text-theme-tertiary mt-1">Number of times to retry local Ollama planner before considering fallback (0\u20133)</p>
                        </Field>
                      </Section>
                    </>
                  )}
                </div>
              )}

              {tab === 'about' && (
                <div className="space-y-5">
                  <Section title="Application">
                    <div className="space-y-3">
                      <InfoRow label="Name" value="ACO \u2014 Autonomous Computer Operator" />
                      <InfoRow label="Version" value="1.0.0" />
                      <InfoRow label="Build" value="2026.07.11-stable" />
                      <InfoRow label="License" value="MIT" />
                    </div>
                  </Section>
                  <Section title="Tech Stack">
                    <div className="space-y-3">
                      <InfoRow label="Frontend" value="Next.js 14 + React 18 + Tailwind" />
                      <InfoRow label="Backend" value="FastAPI + Playwright + LangGraph" />
                      <InfoRow label="AI Providers" value="Ollama + OpenAI + Groq + Mistral + OpenRouter + Cohere" />
                      <InfoRow label="Database" value="MongoDB" />
                      <InfoRow label="Animations" value="Framer Motion" />
                    </div>
                  </Section>
                  <Section title="System">
                    <div className="space-y-3">
                      <InfoRow label="Platform" value="Windows Native" />
                      <InfoRow label="Python" value="3.12" />
                      <InfoRow label="Node.js" value="20.x" />
                      <InfoRow label="Workers" value="3" />
                      <InfoRow label="Browser" value="Chromium (Playwright)" />
                    </div>
                  </Section>
                </div>
              )}

            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-theme-tertiary mb-3">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] text-theme-tertiary mb-1 block">{label}</label>
      {children}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-theme-tertiary">{label}</span>
      <span className="text-xs font-mono text-theme">{value}</span>
    </div>
  );
}

/* ========================================================================
   PROVIDERS TAB — Full provider overview + multi-credential management
   ======================================================================== */
function ProvidersTab() {
  const { token } = useAuth();
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [models, setModels] = useState<Record<string, AIModel[]>>({});
  const [credentials, setCredentials] = useState<AICredential[]>([]);
  const [aiSettings, setAISettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);

  // Add credential form state
  const [addProvider, setAddProvider] = useState('openai');
  const [addLabel, setAddLabel] = useState('');
  const [addKey, setAddKey] = useState('');
  const [addSaving, setAddSaving] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState(false);

  // Credential action states
  const [validating, setValidating] = useState<Record<string, boolean>>({});
  const [validResult, setValidResult] = useState<Record<string, 'valid' | 'invalid' | 'error'>>({});
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});

  // Default model selection
  const [defProvider, setDefProvider] = useState('ollama');
  const [defModel, setDefModel] = useState('');

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [provData, modelData, credData, settingsData] = await Promise.all([
        api.getAIProviders(token),
        api.getAIModels(token),
        api.getAICredentials(token),
        api.getAISettings(token),
      ]);
      setProviders(provData.providers || []);
      setModels(modelData.models || {});
      setCredentials(credData.credentials || []);
      setAISettings(settingsData);
      setDefProvider(settingsData.default_provider || 'ollama');
      setDefModel(settingsData.default_model || '');
    } catch {
      setProviders([]);
      setModels({});
      setCredentials([]);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  // Group credentials by provider
  const credByProvider = useCallback((provId: string) =>
    credentials.filter(c => c.provider === provId), [credentials]);

  const handleAddKey = async () => {
    if (!token || !addKey.trim()) return;
    setAddSaving(true);
    setAddError(null);
    setAddSuccess(false);
    try {
      await api.saveAICredential(addProvider, addKey.trim(), addLabel.trim(), false, token);
      setAddKey('');
      setAddLabel('');
      setAddSuccess(true);
      setTimeout(() => setAddSuccess(false), 2000);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to save key');
    } finally {
      setAddSaving(false);
    }
  };

  const handleDeleteKey = async (credId: string) => {
    if (!token) return;
    setDeleting(prev => ({ ...prev, [credId]: true }));
    try {
      await api.deleteAICredential(credId, token);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to delete key');
    } finally {
      setDeleting(prev => ({ ...prev, [credId]: false }));
    }
  };

  const handleValidateKey = async (credId: string) => {
    if (!token) return;
    setValidating(prev => ({ ...prev, [credId]: true }));
    setValidResult(prev => ({ ...prev, [credId]: undefined as any }));
    try {
      const result = await api.validateAICredential(credId, token);
      setValidResult(prev => ({ ...prev, [credId]: result.valid ? 'valid' : 'invalid' }));
    } catch {
      setValidResult(prev => ({ ...prev, [credId]: 'error' }));
    } finally {
      setValidating(prev => ({ ...prev, [credId]: false }));
    }
  };

  const handleSetDefault = async (credId: string, provider: string) => {
    if (!token) return;
    try {
      await api.updateAICredential(credId, { is_default: true }, token);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to set default');
    }
  };

  const handleToggleLocalOnly = async () => {
    if (!token || !aiSettings) return;
    try {
      await api.updateAISettings({ ai_local_only: !aiSettings.ai_local_only }, token);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to update setting');
    }
  };

  const handleSetDefaultReasoning = async (level: string) => {
    if (!token) return;
    try {
      await api.updateAISettings({ default_reasoning_level: level }, token);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to update setting');
    }
  };

  const handleSaveDefaultModel = async () => {
    if (!token) return;
    try {
      await api.updateAISettings({
        default_provider: defProvider,
        default_model: defModel || undefined,
      }, token);
      await load();
    } catch (e: any) {
      setAddError(e.message || 'Failed to save default model');
    }
  };

  const allCloudProviders = CLOUD_PROVIDERS.filter(pId => providers.some(p => p.id === pId));
  const availableCloudProviders = CLOUD_PROVIDERS.filter(pId => {
    const p = providers.find(pr => pr.id === pId);
    return p && p.available;
  });

  const provModels = models[defProvider] || [];
  const localModels = models['ollama'] || [];

  return (
    <div className="space-y-6">
      {/* AI Preferences */}
      <Section title="AI Preferences">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs text-theme-secondary">Use local AI only</span>
              <p className="text-[10px] text-theme-tertiary mt-0.5">When enabled, cloud providers are blocked. No API keys will be used.</p>
            </div>
            <button onClick={handleToggleLocalOnly}
              className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative',
                aiSettings?.ai_local_only ? 'bg-theme' : 'bg-surface-2')}>
              <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-surface transition-transform',
                aiSettings?.ai_local_only ? 'left-[18px]' : 'left-0.5')} />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs text-theme-secondary">Fall back to local AI</span>
              <p className="text-[10px] text-theme-tertiary mt-0.5">If cloud provider fails, retry with local Ollama model</p>
            </div>
            <button onClick={() => api.updateAISettings({ fallback_to_local: !(aiSettings?.fallback_to_local ?? true) }, token!).then(load)}
              className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative',
                aiSettings?.fallback_to_local ? 'bg-theme' : 'bg-surface-2')}>
              <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-surface transition-transform',
                aiSettings?.fallback_to_local ? 'left-[18px]' : 'left-0.5')} />
            </button>
          </div>

          <div>
            <span className="text-[10px] text-theme-tertiary mb-1.5 block">Default reasoning level</span>
            <div className="flex gap-1.5">
              {['fast', 'balanced', 'deep'].map(level => (
                <button key={level} onClick={() => handleSetDefaultReasoning(level)}
                  className={cn(
                    'px-3 py-1.5 text-[11px] rounded-lg border transition cursor-pointer capitalize',
                    aiSettings?.default_reasoning_level === level
                      ? 'border-theme-strong bg-surface-hover text-theme font-medium'
                      : 'border-theme bg-surface-2 text-theme-secondary hover:bg-surface-hover'
                  )}>
                  {level}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Default Model */}
      <Section title="Default Model">
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="text-[10px] text-theme-tertiary mb-1 block">Provider</label>
            <select value={defProvider} onChange={e => { setDefProvider(e.target.value); setDefModel(''); }}
              className="w-full px-3 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition">
              <option value="ollama">Local (Ollama)</option>
              {allCloudProviders.map(pId => (
                <option key={pId} value={pId} disabled={aiSettings?.ai_local_only}>
                  {CLOUD_PROVIDER_LABELS[pId] || pId}{aiSettings?.ai_local_only ? ' (local-only)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-[10px] text-theme-tertiary mb-1 block">Model</label>
            <select value={defModel} onChange={e => setDefModel(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-input border border-theme rounded-lg outline-none focus:border-theme-strong transition">
              <option value="">Default</option>
              {(defProvider === 'ollama' ? localModels : provModels).map(m => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <button onClick={handleSaveDefaultModel}
            className="px-4 py-2 text-xs font-medium rounded-lg bg-theme text-theme-inverse hover:opacity-90 transition cursor-pointer">
            Save
          </button>
        </div>
      </Section>

      {/* Provider Availability Overview */}
      <Section title="Provider Availability">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={18} className="animate-spin text-theme-tertiary" />
          </div>
        ) : (
          <div className="rounded-lg border border-theme overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-2">
                  <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">Provider</th>
                  <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">Credentials</th>
                  <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">Default</th>
                  <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-theme">
                {providers.map(p => {
                  const provCreds = credByProvider(p.id);
                  const defaultCred = provCreds.find(c => c.is_default);
                  return (
                    <tr key={p.id} className="hover:bg-surface-hover transition-colors">
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          {p.id === 'ollama' ? (
                            <CircleDot size={10} className={cn(p.available ? 'text-status-active' : 'text-theme-tertiary')} />
                          ) : (
                            <Circle size={10} className={cn(p.available ? 'text-status-active' : 'text-theme-tertiary')} />
                          )}
                          <span className="font-medium text-theme">{p.name}</span>
                          <span className="text-[10px] text-theme-tertiary">({p.id})</span>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-theme-secondary">
                          {p.id === 'ollama' ? '\u2014' : `${provCreds.length} key(s)`}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-theme-secondary">
                          {defaultCred?.label || (p.id === 'ollama' ? 'built-in' : '\u2014')}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-medium border',
                          p.available
                            ? 'bg-status-active-soft border-status-active text-status-active'
                            : 'bg-surface-2 border-theme text-theme-tertiary'
                        )}>
                          {p.available ? 'Available' : 'Unavailable'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* API Credentials */}
      <Section title="API Credentials">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={18} className="animate-spin text-theme-tertiary" />
          </div>
        ) : (
          <>
            {/* Existing credentials grouped by provider */}
            <div className="space-y-4">
              {allCloudProviders.map(provId => {
                const provCreds = credByProvider(provId);
                return (
                  <div key={provId} className="rounded-lg border border-theme">
                    <div className="px-3 py-2 bg-surface-2 flex items-center gap-2">
                      <Circle size={10} className="text-theme-tertiary" />
                      <span className="text-[11px] font-semibold text-theme">{CLOUD_PROVIDER_LABELS[provId] || provId}</span>
                      <span className="text-[10px] text-theme-tertiary">{provCreds.length} key(s)</span>
                    </div>
                    <div className="divide-y divide-theme">
                      {provCreds.length === 0 ? (
                        <div className="px-3 py-3 text-[10px] text-theme-tertiary italic">No keys configured</div>
                      ) : (
                        provCreds.map(cred => (
                          <div key={cred.id} className="px-3 py-2.5 flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <Key size={11} className="text-theme-tertiary shrink-0" />
                              <span className="text-[11px] font-medium text-theme truncate">{cred.label || 'Unnamed'}</span>
                              <span className="text-[10px] text-theme-tertiary font-mono shrink-0">{cred.key_hint}</span>
                              {cred.is_default && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-status-active-soft text-status-active border border-status-active shrink-0">default</span>
                              )}
                              {validResult[cred.id] === 'valid' && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-status-active-soft text-status-active shrink-0">valid</span>
                              )}
                              {validResult[cred.id] === 'invalid' && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-status-error-soft text-status-error shrink-0">invalid</span>
                              )}
                              {cred.validated_at && validResult[cred.id] !== 'invalid' && validResult[cred.id] !== 'error' && (
                                <span className="text-[9px] text-theme-tertiary shrink-0 hidden sm:inline">
                                  validated {new Date(cred.validated_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              {!cred.is_default && (
                                <button onClick={() => handleSetDefault(cred.id, provId)}
                                  className="p-1 text-theme-tertiary hover:text-status-active transition cursor-pointer"
                                  title="Set as default">
                                  <CheckCircle2 size={12} />
                                </button>
                              )}
                              <button onClick={() => handleValidateKey(cred.id)}
                                disabled={validating[cred.id]}
                                className="p-1 text-theme-tertiary hover:text-status-info transition cursor-pointer"
                                title="Validate key">
                                {validating[cred.id] ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                              </button>
                              <button onClick={() => handleDeleteKey(cred.id)}
                                disabled={deleting[cred.id]}
                                className="p-1 text-theme-tertiary hover:text-status-error transition cursor-pointer"
                                title="Delete key">
                                {deleting[cred.id] ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Add new credential */}
            <div className="rounded-lg border border-theme bg-surface-2/50 p-3 mt-4 space-y-2">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-theme-tertiary mb-2">Add credential</div>
              <div className="flex gap-2">
                <select value={addProvider} onChange={e => setAddProvider(e.target.value)}
                  className="px-2 py-1.5 text-[11px] bg-input border border-theme rounded-lg outline-none shrink-0">
                  {allCloudProviders.map(pId => (
                    <option key={pId} value={pId}>{CLOUD_PROVIDER_LABELS[pId] || pId}</option>
                  ))}
                </select>
                <input type="text" value={addLabel} onChange={e => setAddLabel(e.target.value)}
                  placeholder="Label (optional)" className="flex-1 px-2 py-1.5 text-[11px] bg-input border border-theme rounded-lg outline-none min-w-0" />
              </div>
              <div className="flex gap-2">
                <input type="password" value={addKey} onChange={e => setAddKey(e.target.value)}
                  placeholder="Enter API key" className="flex-1 px-2 py-1.5 text-[11px] font-mono bg-input border border-theme rounded-lg outline-none min-w-0" />
                <button onClick={handleAddKey} disabled={!addKey.trim() || addSaving}
                  className={cn(
                    'flex items-center gap-1 px-3 py-1.5 text-[11px] font-medium rounded-lg transition cursor-pointer shrink-0',
                    addKey.trim() && !addSaving
                      ? 'bg-theme text-theme-inverse hover:bg-surface-elevated'
                      : 'bg-surface-2 text-theme-tertiary cursor-not-allowed'
                  )}>
                  {addSaving ? <Loader2 size={11} className="animate-spin" /> : addSuccess ? <Check size={11} /> : <Plus size={11} />}
                  {addSaving ? 'Saving...' : addSuccess ? 'Saved!' : 'Add'}
                </button>
              </div>
              {addError && <p className="text-[10px] text-status-error">{addError}</p>}
            </div>
          </>
        )}
      </Section>
    </div>
  );
}
