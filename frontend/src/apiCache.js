/**
 * Simple in-memory cache for API responses.
 * Data is served instantly from cache; refetched only if older than TTL.
 */

const TTL_MS = 2 * 60 * 1000; // 2 minutes
const cache = {};

export function getCache(key) {
  const entry = cache[key];
  if (!entry) return null;
  if (Date.now() - entry.ts > TTL_MS) {
    delete cache[key];
    return null;
  }
  return entry.data;
}

export function setCache(key, data) {
  cache[key] = { data, ts: Date.now() };
}

export function invalidateCache(...keys) {
  keys.forEach(k => delete cache[k]);
}
