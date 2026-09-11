// @ts-nocheck

function positiveIntegerString(value, max) {
  if(value === undefined || value === null) return null;
  const text = String(value);
  if(!/^[1-9]\d*$/.test(text)) return null;
  const n = Number(text);
  if(!Number.isSafeInteger(n) || n <= 0) return null;
  if(max !== undefined && n > max) return null;
  return text;
}

function randomIdentity(value) {
  if(value === undefined || value === null) return null;
  const text = String(value);
  return /^\d+$/.test(text) && text !== '0' ? `r${text}` : null;
}

export function buildJerkgramTapIdentity(push) {
  const data = push && typeof push === 'object' && push.data && typeof push.data === 'object'
    ? push.data
    : push;
  if(!data || typeof data !== 'object') return null;

  const custom = data.custom && typeof data.custom === 'object' ? data.custom : {};
  let kind = null;
  let peer = null;

  const channel = positiveIntegerString(custom.channel_id);
  const chat = positiveIntegerString(custom.chat_id);
  const user = positiveIntegerString(custom.from_id);
  if(channel) {
    kind = 'channel';
    peer = channel;
  } else if(chat) {
    kind = 'chat';
    peer = chat;
  } else if(user) {
    kind = 'user';
    peer = user;
  } else {
    return null;
  }

  const receiver = positiveIntegerString(data.user_id) || '0';
  const msg = positiveIntegerString(custom.msg_id, 2147483647) || randomIdentity(data.random_id);
  if(!msg) return null;
  const thread = positiveIntegerString(custom.top_msg_id, 2147483647) || '0';

  return `v1:${receiver}:${kind}:${peer}:${msg}:${thread}`;
}

export function normalizeJerkgramOpenUrl(value) {
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
  if(!positiveIntegerString(url.searchParams.get('peer'))) return null;

  const optionalPositive = (name, max) => {
    const value = url.searchParams.get(name);
    return value === null || !!positiveIntegerString(value, max);
  };
  if(!optionalPositive('user')) return null;
  if(!optionalPositive('msg', 2147483647)) return null;
  if(!optionalPositive('thread', 2147483647)) return null;

  return url.href;
}

export function findUniqueDisappearedTap(previousIds, currentIds, records, now = Date.now()) {
  if(!Array.isArray(previousIds) || !Array.isArray(currentIds) || !Array.isArray(records)) {
    return null;
  }

  const previous = [...new Set(previousIds.filter((value) => typeof value === 'string' && value))];
  const current = new Set(currentIds.filter((value) => typeof value === 'string' && value));
  const disappeared = previous.filter((id) => !current.has(id));
  if(disappeared.length !== 1) return null;

  const id = disappeared[0];
  const matches = records.filter((record) => {
    if(!record || record.id !== id) return false;
    if(typeof record.expiresAt !== 'number' || record.expiresAt <= now) return false;
    return !!normalizeJerkgramOpenUrl(record.url);
  });
  if(matches.length !== 1) return null;

  return {id, url: normalizeJerkgramOpenUrl(matches[0].url)};
}
