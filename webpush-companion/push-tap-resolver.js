(async() => {
  const {
    buildJerkgramTapIdentity,
    findUniqueDisappearedTap,
    normalizeJerkgramOpenUrl
  } = await import('./tap-fallback.js');

  const CACHE_NAME = 'jerkgram-push-tap-v1';
  const SNAPSHOT_NAME = '__jerkgram_tap_snapshot__';
  const RECORD_PREFIX = '__jerkgram_tap_record__/';
  const SNAPSHOT_MAX_AGE_MS = 6 * 60 * 60 * 1000;

  let running = false;
  let opened = false;
  let lastRun = 0;

  function keyFor(scope, name) {
    return new URL(name, scope).href;
  }

  async function readJson(cache, key) {
    const response = await cache.match(key);
    if(!response) return null;
    try {
      return await response.json();
    } catch(_) {
      return null;
    }
  }

  async function writeSnapshot(cache, scope, ids) {
    const uniqueIds = [...new Set(ids.filter((value) => typeof value === 'string' && value))];
    const key = keyFor(scope, SNAPSHOT_NAME);
    await cache.put(key, new Response(JSON.stringify({ids: uniqueIds, savedAt: Date.now()}), {
      headers: {'content-type': 'application/json', 'cache-control': 'no-store'}
    }));
  }

  async function resolveTappedNotification() {
    if(opened || running || document.visibilityState !== 'visible') return false;
    const now = Date.now();
    if(now - lastRun < 120) return false;
    lastRun = now;
    running = true;

    try {
      if(!('serviceWorker' in navigator) || !('caches' in window)) return false;
      const registration = await navigator.serviceWorker.ready;
      if(typeof registration.getNotifications !== 'function') return false;

      const cache = await caches.open(CACHE_NAME);
      const scope = registration.scope;
      const snapshot = await readJson(cache, keyFor(scope, SNAPSHOT_NAME));
      const notifications = await registration.getNotifications();
      const currentIds = notifications
        .map((notification) => buildJerkgramTapIdentity(notification.data))
        .filter(Boolean);

      if(!snapshot || !Array.isArray(snapshot.ids) || typeof snapshot.savedAt !== 'number' ||
         snapshot.savedAt < now - SNAPSHOT_MAX_AGE_MS) {
        await writeSnapshot(cache, scope, currentIds);
        return false;
      }

      const current = new Set(currentIds);
      const disappeared = [...new Set(snapshot.ids)].filter((id) => !current.has(id));
      let records = [];
      if(disappeared.length === 1) {
        const id = disappeared[0];
        const record = await readJson(cache, keyFor(scope, RECORD_PREFIX + encodeURIComponent(id)));
        if(record) records = [record];
      }

      const match = findUniqueDisappearedTap(snapshot.ids, currentIds, records, now);
      await writeSnapshot(cache, scope, currentIds);
      if(!match) return false;

      const nativeUrl = normalizeJerkgramOpenUrl(match.url);
      if(!nativeUrl) return false;

      await cache.delete(keyFor(scope, RECORD_PREFIX + encodeURIComponent(match.id)));
      opened = true;
      window.location.href = nativeUrl;
      return true;
    } catch(_) {
      return false;
    } finally {
      running = false;
    }
  }

  resolveTappedNotification();
  window.setTimeout(resolveTappedNotification, 180);
  window.setTimeout(resolveTappedNotification, 650);
  window.addEventListener('pageshow', resolveTappedNotification);
  window.addEventListener('focus', resolveTappedNotification);
  document.addEventListener('visibilitychange', () => {
    if(document.visibilityState === 'visible') resolveTappedNotification();
  });
})().catch(() => {
  // Root-screen fallback is best-effort. Normal companion startup must continue.
});
