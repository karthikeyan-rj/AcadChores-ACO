interface CacheEntry<T> {
  data: T;
  timestamp: number;
  staleTime: number;
}

const cache = new Map<string, CacheEntry<any>>();

export function getCached<T>(key: string, staleTimeMs: number): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > staleTimeMs) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

export function setCache<T>(key: string, data: T, staleTimeMs: number): void {
  cache.set(key, { data, timestamp: Date.now(), staleTime: staleTimeMs });
}

export function invalidateCache(keyPrefix: string): void {
  Array.from(cache.keys()).forEach(key => {
    if (key.startsWith(keyPrefix)) cache.delete(key);
  });
}

export function clearCache(): void {
  cache.clear();
}

export const STALE_TIMES = {
  HEALTH: 30_000,
  USER_PROFILE: 300_000,
  DASHBOARD: 30_000,
  HISTORY_FIRST: 30_000,
  HISTORY_PAGE: 15_000,
  SETTINGS: 300_000,
  ACTIVE_WORKFLOW: 10_000,
  CONVERSATIONS: 15_000,
  FILES: 15_000,
  INDEX_CONFIG: 300_000,
} as const;
