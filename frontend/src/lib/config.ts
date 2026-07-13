export function getBackendUrl(): string {
  if (typeof window === 'undefined') return 'http://localhost:8001';
  return `http://${window.location.hostname}:8001`;
}
