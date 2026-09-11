(() => {
  const CACHE_NAME = 'jerkgram-push-handoff-v1';
  const PENDING_NAME = '__jerkgram_pending_push__';

  function normalizeNativeUrl(value) {
    if(typeof value !== 'string' || !value) return null;

    let url;
    try {
      url = new URL(value);
    } catch(_) {
      return null;
    }

    if(url.protocol !== 'jerkgram:' || url.hostname !== 'push' || url.pathname !== '/open') {
      return null;
    }

    const allowed = new Set(['kind', 'peer', 'user', 'msg', 'thread']);
    for(const key of url.searchParams.keys()) {
      if(!allowed.has(key)) return null;
    }

    const kind = url.searchParams.get('kind');
    if(!['user', 'chat', 'channel'].includes(kind)) return null;

    const positive = (name, max) => {
      const value = url.searchParams.get(name);
      if(value === null) return true;
      if(!/^[1-9]\d*$/.test(value)) return false;
      const n = Number(value);
      return Number.isSafeInteger(n) && n > 0 && (max === undefined || n <= max);
    };

    if(!positive('peer')) return null;
    if(!positive('user')) return null;
    if(!positive('msg', 2147483647)) return null;
    if(!positive('thread', 2147483647)) return null;

    return url.href;
  }

  function openNative(value) {
    const nativeUrl = normalizeNativeUrl(value);
    if(!nativeUrl) return false;
    window.location.href = nativeUrl;
    return true;
  }

  async function consumePending() {
    if(!('caches' in window)) return false;

    try {
      const cache = await caches.open(CACHE_NAME);
      const key = new URL(PENDING_NAME, document.baseURI).href;
      const response = await cache.match(key);
      if(!response) return false;

      await cache.delete(key);
      const payload = await response.json();
      if(!payload || typeof payload.expiresAt !== 'number' || payload.expiresAt < Date.now()) {
        return false;
      }

      return openNative(payload.url);
    } catch(_) {
      return false;
    }
  }

  if('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      const data = event.data;
      if(data && data.type === 'jerkgram-push-open') {
        openNative(data.url);
      }
    });
  }

  consumePending();
  window.setTimeout(consumePending, 200);
})();
