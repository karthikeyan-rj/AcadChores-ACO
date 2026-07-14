'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings, Cpu, Info, Save, Check, Loader2, Eye, EyeOff, Trash2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

type SettingsTab = 'ai' | 'about';

const tabs: { id: SettingsTab; label: string; icon: any }[] = [
  { id: 'ai', label: 'AI Model', icon: Cpu },
  { id: 'about', label: 'About', icon: Info },
];

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

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
];

const MODELS: Record<string, { value: string; label: string }[]> = {
  openai: [
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
  ],
  anthropic: [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  gemini: [
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
  ],
};

export default function SettingsPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<SettingsTab>('ai');
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [dirty, setDirty] = useState(false);

  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const [deletingKey, setDeletingKey] = useState(false);
  const [keySaveSuccess, setKeySaveSuccess] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);

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
      const data = await api.updateSettings(payload, token);
      setSettings(prev => ({
        ...prev,
        api_key_configured: data.api_key_configured,
        api_key_hint: data.api_key_hint,
      }));
      setDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e: any) {
      setError(e.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKey = async () => {
    if (!token || !apiKeyInput.trim()) return;
    setSavingKey(true);
    setKeyError(null);
    setKeySaveSuccess(false);
    try {
      await api.saveSettingsApiKey(settings.cloud_provider, apiKeyInput.trim(), token);
      setApiKeyInput('');
      setKeySaveSuccess(true);
      setTimeout(() => setKeySaveSuccess(false), 2000);
      await loadSettings();
    } catch (e: any) {
      setKeyError(e.message || 'Failed to save API key');
    } finally {
      setSavingKey(false);
    }
  };

  const handleDeleteApiKey = async () => {
    if (!token) return;
    setDeletingKey(true);
    setKeyError(null);
    try {
      await api.deleteSettingsApiKey(settings.cloud_provider, token);
      setKeySaveSuccess(false);
      await loadSettings();
    } catch (e: any) {
      setKeyError(e.message || 'Failed to delete API key');
    } finally {
      setDeletingKey(false);
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
          <h1 className="text-xl font-bold text-foreground">Settings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Configure your ACO environment</p>
        </div>
        {tab === 'ai' && (
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition cursor-pointer',
              dirty && !saving
                ? 'bg-primary text-white hover:bg-primary-hover'
                : 'bg-surface-2 text-gray-500 cursor-not-allowed'
            )}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : saveSuccess ? <Check size={14} /> : <Save size={14} />}
            {saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save Changes'}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 px-4 py-3 rounded-lg bg-danger/10 border border-danger/20 text-danger text-xs">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      <div className="flex gap-5">
        <div className="w-[180px] shrink-0 space-y-0.5">
          {tabs.map(t => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition cursor-pointer',
                  tab === t.id ? 'bg-primary/10 text-primary' : 'text-gray-400 hover:text-foreground hover:bg-surface-2'
                )}>
                <Icon size={14} />{t.label}
              </button>
            );
          })}
        </div>

        <div className="flex-1 rounded-xl border border-border bg-card p-6 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.15 }}>

              {tab === 'ai' && (
                <div className="space-y-6">
                  {loading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 size={24} className="animate-spin text-gray-500" />
                    </div>
                  ) : (
                    <>
                      <Section title="Cloud Fallback">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs text-gray-400">Enable cloud fallback when local planner quality is low</span>
                            <p className="text-[10px] text-gray-500 mt-0.5">Falls back to cloud API if Ollama output quality is below threshold</p>
                          </div>
                          <button onClick={() => updateField('cloud_fallback_enabled', !settings.cloud_fallback_enabled)}
                            className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative',
                              settings.cloud_fallback_enabled ? 'bg-primary' : 'bg-surface-3')}>
                            <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform',
                              settings.cloud_fallback_enabled ? 'left-[18px]' : 'left-0.5')} />
                          </button>
                        </div>
                      </Section>

                      <Section title="Cloud Provider">
                        <Field label="Provider">
                          <select value={settings.cloud_provider}
                            onChange={(e) => {
                              updateField('cloud_provider', e.target.value);
                              const models = MODELS[e.target.value];
                              if (models && models.length > 0) {
                                updateField('cloud_model', models[0].value);
                              }
                            }}
                            className="w-full px-3 py-2 text-xs bg-surface-2 border border-border rounded-lg outline-none focus:border-primary transition">
                            {PROVIDERS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                          </select>
                        </Field>
                        <Field label="Model">
                          <select value={settings.cloud_model}
                            onChange={(e) => updateField('cloud_model', e.target.value)}
                            className="w-full px-3 py-2 text-xs bg-surface-2 border border-border rounded-lg outline-none focus:border-primary transition">
                            {(MODELS[settings.cloud_provider] || MODELS.openai).map(m =>
                              <option key={m.value} value={m.value}>{m.label}</option>
                            )}
                          </select>
                        </Field>
                      </Section>

                      <Section title="API Key">
                        <p className="text-[10px] text-gray-500 mb-3">
                          {settings.api_key_configured
                            ? `Configured for ${settings.cloud_provider} — ${settings.api_key_hint || '••••••••'}`
                            : `No API key configured for ${settings.cloud_provider}`
                          }
                        </p>
                        <div className="flex gap-2">
                          <div className="flex-1 relative">
                            <input
                              type={showApiKey ? 'text' : 'password'}
                              value={apiKeyInput}
                              onChange={(e) => setApiKeyInput(e.target.value)}
                              placeholder={settings.api_key_configured ? 'Enter new key to replace' : 'Enter API key'}
                              className="w-full px-3 py-2 pr-10 text-xs font-mono bg-surface-2 border border-border rounded-lg outline-none focus:border-primary transition"
                            />
                            <button onClick={() => setShowApiKey(p => !p)}
                              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-foreground transition cursor-pointer">
                              {showApiKey ? <EyeOff size={13} /> : <Eye size={13} />}
                            </button>
                          </div>
                          <button onClick={handleSaveApiKey}
                            disabled={!apiKeyInput.trim() || savingKey}
                            className={cn(
                              'px-3 py-2 text-xs font-medium rounded-lg transition cursor-pointer',
                              apiKeyInput.trim() && !savingKey
                                ? 'bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20'
                                : 'bg-surface-2 text-gray-500 border border-border cursor-not-allowed'
                            )}>
                            {savingKey ? <Loader2 size={13} className="animate-spin" /> : keySaveSuccess ? <Check size={13} /> : 'Save Key'}
                          </button>
                          {settings.api_key_configured && (
                            <button onClick={handleDeleteApiKey}
                              disabled={deletingKey}
                              className="px-3 py-2 text-xs font-medium text-danger hover:bg-danger/10 rounded-lg transition cursor-pointer border border-danger/20">
                              {deletingKey ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                            </button>
                          )}
                        </div>
                        {keyError && <p className="text-[10px] text-danger mt-2">{keyError}</p>}
                      </Section>

                      <Section title="Planning">
                        <Field label={`Quality Threshold (${settings.workflow_quality_threshold})`}>
                          <div className="flex items-center gap-3">
                            <input type="range" min={50} max={100} value={settings.workflow_quality_threshold}
                              onChange={(e) => updateField('workflow_quality_threshold', parseInt(e.target.value))}
                              className="flex-1 accent-primary" />
                            <span className="text-xs text-gray-400 w-8 text-right">{settings.workflow_quality_threshold}</span>
                          </div>
                          <p className="text-[10px] text-gray-500 mt-1">Minimum quality score (50–100) for local planner output before cloud fallback triggers</p>
                        </Field>
                        <Field label={`Local Retry Count (${settings.local_planner_retry_count})`}>
                          <div className="flex items-center gap-3">
                            <input type="range" min={0} max={3} value={settings.local_planner_retry_count}
                              onChange={(e) => updateField('local_planner_retry_count', parseInt(e.target.value))}
                              className="flex-1 accent-primary" />
                            <span className="text-xs text-gray-400 w-8 text-right">{settings.local_planner_retry_count}</span>
                          </div>
                          <p className="text-[10px] text-gray-500 mt-1">Number of times to retry local Ollama planner before considering fallback (0–3)</p>
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
                      <InfoRow label="Name" value="ACO — Autonomous Computer Operator" />
                      <InfoRow label="Version" value="1.0.0" />
                      <InfoRow label="Build" value="2026.07.11-stable" />
                      <InfoRow label="License" value="MIT" />
                    </div>
                  </Section>
                  <Section title="Tech Stack">
                    <div className="space-y-3">
                      <InfoRow label="Frontend" value="Next.js 14 + React 18 + Tailwind" />
                      <InfoRow label="Backend" value="FastAPI + Playwright + LangGraph" />
                      <InfoRow label="AI Provider" value="Ollama (Local LLM)" />
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
                  <Section title="Credits">
                    <p className="text-xs text-gray-400 leading-relaxed">
                      Built with Next.js, Tailwind CSS, Framer Motion, Lucide Icons, and Recharts.
                      Powered by Ollama for local AI inference.
                    </p>
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
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-3">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[10px] text-gray-500 mb-1 block">{label}</label>
      {children}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-xs font-mono text-foreground">{value}</span>
    </div>
  );
}
