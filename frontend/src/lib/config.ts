export function getBackendUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001';
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || `http://${window.location.hostname}:8001`;
}

export function getWsUrl(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_WS_BASE_URL || 'ws://localhost:8001';
  }
  return process.env.NEXT_PUBLIC_WS_BASE_URL || `ws://${window.location.hostname}:8001`;
}
