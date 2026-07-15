import { getBackendUrl, getWsUrl } from '@/lib/config';

const BACKEND = getBackendUrl();

let _onAuthFailure: (() => void) | null = null;

export function setAuthFailureHandler(handler: () => void) {
  _onAuthFailure = handler;
}

function headers(token: string | null): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function apiFetch(path: string, opts: RequestInit = {}, token?: string | null) {
  const res = await fetch(`${BACKEND}${path}`, {
    ...opts,
    headers: { ...headers(token), ...(opts.headers as Record<string, string> || {}) },
  });
  if (res.status === 401) {
    if (_onAuthFailure) _onAuthFailure();
    throw new Error('Session expired. Please log in again.');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetch(`${BACKEND}/health`).then(r => r.ok),

  me: (token: string) =>
    apiFetch('/api/v1/auth/me', {}, token),

  generatePlan: (prompt: string, token: string) =>
    apiFetch('/api/v1/workflows/generate-plan', {
      method: 'POST', body: JSON.stringify({ prompt }),
    }, token),

  chat: (message: string, token: string) =>
    apiFetch('/api/v1/workflows/chat', {
      method: 'POST', body: JSON.stringify({ message }),
    }, token),

  createWorkflow: (title: string, description: string, steps: any[], token: string) =>
    apiFetch('/api/v1/workflows', { method: 'POST', body: JSON.stringify({ title, description, steps }) }, token),

  executeWorkflow: (workflowId: string, token: string) =>
    apiFetch(`/api/v1/workflows/${workflowId}/execute`, { method: 'POST' }, token),

  getExecutions: (token: string) =>
    apiFetch('/api/v1/executions', {}, token),

  getExecutionLogs: (executionId: string, token: string) =>
    apiFetch(`/api/v1/executions/${executionId}/logs`, {}, token),

  getExecution: (executionId: string, token: string) =>
    apiFetch(`/api/v1/executions/${executionId}`, {}, token),

  abortExecution: (executionId: string, token: string) =>
    apiFetch(`/api/v1/executions/${executionId}/abort`, { method: 'POST' }, token),

  searchFiles: (query: string, token: string) =>
    apiFetch(`/api/v1/search/files?query=${encodeURIComponent(query)}`, {}, token),

  getIndexConfig: (token: string) =>
    apiFetch('/api/v1/search/index/config', {}, token),

  updateIndexConfig: (config: any, token: string) =>
    apiFetch('/api/v1/search/index/config', {
      method: 'POST', body: JSON.stringify(config),
    }, token),

  triggerIndex: (token: string) =>
    apiFetch('/api/v1/search/index/trigger', { method: 'POST' }, token),

  getIndexJobs: (token: string) =>
    apiFetch('/api/v1/search/index/jobs', {}, token),

  getIndexStats: (token: string) =>
    apiFetch('/api/v1/search/index/stats', {}, token),

  deleteFile: (filePath: string, token: string) =>
    apiFetch('/api/v1/search/files/delete', {
      method: 'POST', body: JSON.stringify({ path: filePath }),
    }, token),

  respondPermission: (requestId: string, approved: boolean, token: string) =>
    apiFetch('/api/v1/permissions/response', {
      method: 'POST', body: JSON.stringify({ request_id: requestId, approved }),
    }, token),

  getDashboard: (token: string) =>
    apiFetch('/api/v1/dashboard', {}, token),

  getCloudSettings: (token: string) =>
    apiFetch('/api/v1/cloud/cloud-settings', {}, token),

  getApiKeys: (token: string) =>
    apiFetch('/api/v1/cloud/api-keys', {}, token),

  saveApiKey: (provider: string, apiKey: string, token: string) =>
    apiFetch('/api/v1/cloud/api-keys', {
      method: 'POST', body: JSON.stringify({ provider, api_key: apiKey }),
    }, token),

  deleteApiKey: (provider: string, token: string) =>
    apiFetch(`/api/v1/cloud/api-keys/${provider}`, { method: 'DELETE' }, token),

  validateWorkflow: (workflow: any, prompt: string, token: string) =>
    apiFetch('/api/v1/cloud/validate-workflow', {
      method: 'POST', body: JSON.stringify({ workflow, prompt }),
    }, token),

  getSettings: (token: string) =>
    apiFetch('/api/v1/settings', {}, token),

  updateSettings: (settings: Record<string, any>, token: string) =>
    apiFetch('/api/v1/settings', {
      method: 'PATCH', body: JSON.stringify(settings),
    }, token),

  saveSettingsApiKey: (provider: string, apiKey: string, token: string) =>
    apiFetch('/api/v1/settings/api-keys', {
      method: 'POST', body: JSON.stringify({ provider, api_key: apiKey }),
    }, token),

  deleteSettingsApiKey: (provider: string, token: string) =>
    apiFetch(`/api/v1/settings/api-keys/${provider}`, { method: 'DELETE' }, token),

  getSettingsApiKeys: (token: string) =>
    apiFetch('/api/v1/settings/api-keys', {}, token),

  wsUrl: (executionId: string, token: string | null) =>
    `${getWsUrl()}/ws/executions/${executionId}${token ? `?token=${encodeURIComponent(token)}` : ''}`,
};
