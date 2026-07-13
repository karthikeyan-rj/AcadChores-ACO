'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings, User, Palette, Cpu, Globe, Shield, Code, Info,
  Save, RotateCcw, Bell, Puzzle, Key, Database, Terminal,
  Check, Moon, Sun, Monitor, Eye, EyeOff
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth';

type SettingsTab = 'general' | 'appearance' | 'ai' | 'browser' | 'permissions' | 'notifications' | 'plugins' | 'developer' | 'about';

const tabs: { id: SettingsTab; label: string; icon: any }[] = [
  { id: 'general', label: 'General', icon: User },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'ai', label: 'AI Model', icon: Cpu },
  { id: 'browser', label: 'Browser', icon: Globe },
  { id: 'permissions', label: 'Permissions', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'plugins', label: 'Plugins', icon: Puzzle },
  { id: 'developer', label: 'Developer', icon: Code },
  { id: 'about', label: 'About', icon: Info },
];

export default function SettingsPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<SettingsTab>('general');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-6 max-w-[1000px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">Settings</h1>
          <p className="text-xs text-gray-500 mt-0.5">Configure your ACO environment</p>
        </div>
        <button onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-xl shadow-lg shadow-primary/20 transition cursor-pointer">
          {saved ? <><Check size={14} />Saved!</> : <><Save size={14} />Save Changes</>}
        </button>
      </div>

      <div className="flex gap-5">
        {/* Tab sidebar */}
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

        {/* Tab content */}
        <div className="flex-1 rounded-xl border border-border bg-card/80 p-6 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div key={tab} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.15 }}>

              {tab === 'general' && (
                <div className="space-y-5">
                  <Section title="Profile">
                    <Field label="Display Name">
                      <input type="text" defaultValue={user?.name || ''} className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                    <Field label="Email">
                      <input type="email" defaultValue={user?.email || ''} className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                  </Section>
                  <Section title="Language & Region">
                    <Field label="Language">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>English</option><option>Hindi</option><option>Spanish</option>
                      </select>
                    </Field>
                    <Field label="Timezone">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>Asia/Kolkata (IST)</option><option>UTC</option><option>US/Pacific (PST)</option>
                      </select>
                    </Field>
                  </Section>
                  <Section title="Data & Privacy">
                    <Toggle label="Allow anonymous usage analytics" />
                    <Toggle label="Store conversation history" defaultOn />
                    <Toggle label="Auto-save workflow drafts" defaultOn />
                  </Section>
                </div>
              )}

              {tab === 'appearance' && (
                <div className="space-y-5">
                  <Section title="Theme">
                    <div className="grid grid-cols-3 gap-3">
                      {['Dark', 'Midnight', 'OLED'].map(theme => (
                        <div key={theme} className={cn(
                          'p-3 rounded-lg border cursor-pointer text-center transition',
                          theme === 'Dark' ? 'border-primary/40 bg-primary/5' : 'border-border hover:border-border-light'
                        )}>
                          <div className="w-full h-16 rounded bg-background border border-border mb-2 flex items-center justify-center">
                            {theme === 'OLED' && <div className="w-6 h-6 rounded-full bg-black border border-gray-800" />}
                            {theme === 'Midnight' && <div className="w-6 h-6 rounded-full bg-blue-950 border border-blue-800" />}
                            {theme === 'Dark' && <div className="w-6 h-6 rounded-full bg-gray-900 border border-gray-700" />}
                          </div>
                          <span className="text-[11px] font-medium">{theme}</span>
                        </div>
                      ))}
                    </div>
                  </Section>
                  <Section title="Accent Color">
                    <div className="flex gap-2">
                      {['#7c5bf5', '#3b82f6', '#34d399', '#f59e0b', '#f43f5e', '#8b5cf6', '#06b6d4', '#ec4899'].map(color => (
                        <button key={color} className="w-7 h-7 rounded-full border-2 border-transparent hover:border-white/20 transition cursor-pointer"
                          style={{ background: color }} title={color} />
                      ))}
                    </div>
                  </Section>
                  <Section title="Layout">
                    <Toggle label="Compact mode" />
                    <Toggle label="Show status bar" defaultOn />
                    <Toggle label="Animate page transitions" defaultOn />
                    <Toggle label="Show sidebar tooltips" defaultOn />
                    <Toggle label="Reduce motion" />
                  </Section>
                </div>
              )}

              {tab === 'ai' && (
                <div className="space-y-5">
                  <Section title="Model Configuration">
                    <Field label="LLM Provider">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>Ollama (Local)</option><option>OpenAI</option><option>Anthropic</option><option>Custom Endpoint</option>
                      </select>
                    </Field>
                    <Field label="Model">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>llama3.1</option><option>mistral</option><option>codellama</option><option>gpt-4o</option>
                      </select>
                    </Field>
                    <Field label="Temperature">
                      <div className="flex items-center gap-3">
                        <input type="range" min="0" max="100" defaultValue="30" className="flex-1 accent-primary" />
                        <span className="text-xs text-gray-400 w-8 text-right">0.3</span>
                      </div>
                    </Field>
                    <Field label="Max Tokens">
                      <input type="number" defaultValue={4096} className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                    <Field label="Top P">
                      <div className="flex items-center gap-3">
                        <input type="range" min="0" max="100" defaultValue="90" className="flex-1 accent-primary" />
                        <span className="text-xs text-gray-400 w-8 text-right">0.9</span>
                      </div>
                    </Field>
                  </Section>
                  <Section title="Planning">
                    <Toggle label="Auto-generate workflow plans" defaultOn />
                    <Toggle label="Require confirmation before execution" defaultOn />
                    <Toggle label="Email draft confirmation" defaultOn />
                    <Toggle label="Use vision model for screenshots" />
                    <Toggle label="Enable step recovery on failure" defaultOn />
                  </Section>
                </div>
              )}

              {tab === 'browser' && (
                <div className="space-y-5">
                  <Section title="Browser Settings">
                    <Field label="Browser Engine">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>Chromium (Playwright)</option><option>Firefox</option><option>WebKit</option>
                      </select>
                    </Field>
                    <Toggle label="Run browser in headless mode" defaultOn />
                    <Field label="Default Timeout (ms)">
                      <input type="number" defaultValue={30000} className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                    <Field label="Viewport Size">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>1280 x 720</option><option>1920 x 1080</option><option>1440 x 900</option><option>Custom</option>
                      </select>
                    </Field>
                  </Section>
                  <Section title="Screenshot & Recording">
                    <Toggle label="Auto-capture screenshots on steps" defaultOn />
                    <Toggle label="Record browser sessions" />
                    <Field label="Screenshot Quality">
                      <select className="w-full px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition">
                        <option>High (PNG)</option><option>Medium (JPEG 80%)</option><option>Low (JPEG 50%)</option>
                      </select>
                    </Field>
                  </Section>
                  <Section title="User Agent">
                    <Field label="Custom User Agent">
                      <input type="text" placeholder="Leave empty for default" className="w-full px-3 py-2 text-xs font-mono bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                  </Section>
                </div>
              )}

              {tab === 'permissions' && (
                <div className="space-y-5">
                  <Section title="Auto-Approval">
                    <Toggle label="Auto-approve file operations" />
                    <Toggle label="Auto-approve web navigation" defaultOn />
                    <Toggle label="Auto-approve terminal commands" />
                    <Toggle label="Auto-approve email sending" />
                    <Toggle label="Auto-approve browser clicks" />
                  </Section>
                  <Section title="Safety">
                    <Toggle label="Block destructive commands" defaultOn />
                    <Toggle label="Sandbox file operations" defaultOn />
                    <Toggle label="Log all actions" defaultOn />
                    <Toggle label="Require confirmation for external URLs" defaultOn />
                    <Toggle label="Block file deletion without confirmation" defaultOn />
                  </Section>
                  <Section title="API Keys">
                    <Field label="Gmail OAuth Token">
                      <div className="flex gap-2">
                        <input type="password" placeholder="••••••••" className="flex-1 px-3 py-2 text-xs bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                        <button className="px-3 py-2 text-xs text-gray-400 hover:text-foreground bg-surface border border-border rounded-lg transition cursor-pointer"><Eye size={13} /></button>
                      </div>
                    </Field>
                  </Section>
                </div>
              )}

              {tab === 'notifications' && (
                <div className="space-y-5">
                  <Section title="Notification Types">
                    <Toggle label="Workflow completed" defaultOn />
                    <Toggle label="Workflow failed" defaultOn />
                    <Toggle label="Permission required" defaultOn />
                    <Toggle label="Recovery started" defaultOn />
                    <Toggle label="Recovery completed" defaultOn />
                    <Toggle label="Browser opened/closed" />
                    <Toggle label="Plugin installed" defaultOn />
                    <Toggle label="System updates" defaultOn />
                  </Section>
                  <Section title="Delivery">
                    <Toggle label="Desktop notifications" defaultOn />
                    <Toggle label="Sound alerts" />
                    <Toggle label="Email notifications" />
                    <Toggle label="In-app only" defaultOn />
                  </Section>
                </div>
              )}

              {tab === 'plugins' && (
                <div className="space-y-5">
                  <Section title="Installed Plugins">
                    <div className="space-y-2">
                      {['Gmail Enhanced', 'YouTube Scraper', 'Shell Commander', 'MongoDB Connector', 'Workflow Templates'].map(p => (
                        <div key={p} className="flex items-center justify-between p-3 rounded-lg bg-surface border border-border">
                          <span className="text-xs font-medium">{p}</span>
                          <div className="flex items-center gap-2">
                            <Toggle label="" defaultOn />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Section>
                  <Section title="Plugin Settings">
                    <Toggle label="Auto-update plugins" defaultOn />
                    <Toggle label="Allow community plugins" defaultOn />
                    <Toggle label="Sandbox plugin execution" defaultOn />
                  </Section>
                </div>
              )}

              {tab === 'developer' && (
                <div className="space-y-5">
                  <Section title="API Configuration">
                    <Field label="Backend URL">
                      <input type="text" defaultValue="http://localhost:8001" className="w-full px-3 py-2 text-xs font-mono bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                    <Field label="WebSocket URL">
                      <input type="text" defaultValue="ws://localhost:8001/ws" className="w-full px-3 py-2 text-xs font-mono bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                    </Field>
                    <Field label="API Key">
                      <div className="flex gap-2">
                        <input type="password" placeholder="Optional API key" className="flex-1 px-3 py-2 text-xs font-mono bg-surface border border-border rounded-lg outline-none focus:border-primary transition" />
                        <button className="px-3 py-2 text-xs text-gray-400 hover:text-foreground bg-surface border border-border rounded-lg transition cursor-pointer"><Eye size={13} /></button>
                      </div>
                    </Field>
                  </Section>
                  <Section title="Debug">
                    <Toggle label="Enable debug logging" />
                    <Toggle label="Show WebSocket events" />
                    <Toggle label="Verbose API responses" />
                    <Toggle label="Log LLM prompts" />
                    <Toggle label="Show performance metrics" />
                  </Section>
                  <Section title="Data Management">
                    <div className="flex gap-2">
                      <button className="flex items-center gap-2 px-3 py-2 text-xs text-warning hover:bg-warning/5 rounded-lg transition cursor-pointer border border-warning/20">
                        <RotateCcw size={13} />Reset Settings
                      </button>
                      <button className="flex items-center gap-2 px-3 py-2 text-xs text-danger hover:bg-danger/5 rounded-lg transition cursor-pointer border border-danger/20">
                        <RotateCcw size={13} />Clear All Data
                      </button>
                    </div>
                  </Section>
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
                      <InfoRow label="Cache" value="Redis" />
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
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">{title}</h3>
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

function Toggle({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <div className="flex items-center justify-between">
      {label && <span className="text-xs text-gray-300">{label}</span>}
      <button onClick={() => setOn(p => !p)}
        className={cn('w-9 h-5 rounded-full transition-colors cursor-pointer relative', on ? 'bg-primary' : 'bg-surface-3')}>
        <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform', on ? 'left-[18px]' : 'left-0.5')} />
      </button>
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
