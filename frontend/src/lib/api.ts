import { getBackendUrl } from '@/lib/config';

const BACKEND = getBackendUrl();

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
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetch(`${BACKEND}/health`).then(r => r.ok),

  generatePlan: (prompt: string) =>
    apiFetch('/api/v1/workflows/generate-plan', {
      method: 'POST', body: JSON.stringify({ prompt }),
    }),

  chat: (message: string) =>
    apiFetch('/api/v1/workflows/chat', {
      method: 'POST', body: JSON.stringify({ message }),
    }),

  createWorkflow: (title: string, description: string, steps: any[], token: string) =>
    apiFetch('/api/v1/workflows', { method: 'POST', body: JSON.stringify({ title, description, steps }) }, token),

  executeWorkflow: (workflowId: string, token: string) =>
    apiFetch(`/api/v1/workflows/${workflowId}/execute`, { method: 'POST' }, token),

  getExecutions: (token: string) =>
    apiFetch('/api/v1/executions', {}, token),

  getExecutionLogs: (executionId: string, token: string) =>
    apiFetch(`/api/v1/executions/${executionId}/logs`, {}, token),

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

  respondPermission: (requestId: string, approved: boolean, token: string) =>
    apiFetch('/api/v1/permissions/response', {
      method: 'POST', body: JSON.stringify({ request_id: requestId, approved }),
    }, token),

  getDashboard: (token: string) =>
    apiFetch('/api/v1/dashboard', {}, token),

  wsUrl: (executionId: string, token: string | null) =>
    `${BACKEND.replace('http', 'ws')}/ws/executions/${executionId}${token ? `?token=${token}` : ''}`,
};
