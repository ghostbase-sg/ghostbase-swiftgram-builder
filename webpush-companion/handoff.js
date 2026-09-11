// @ts-nocheck

function positiveIntegerString(value, max) {
  if (value === undefined || value === null) return null;
  const text = String(value);
  if (!/^[1-9]\d*$/.test(text)) return null;
  const n = Number(text);
  if (!Number.isSafeInteger(n) || n <= 0) return null;
  if (max !== undefined && n > max) return null;
  return text;
}

export function buildJerkgramHandoffData(push) {
  const data = push && typeof push === 'object' && push.data && typeof push.data === 'object'
    ? push.data
    : push;
  if (!data || typeof data !== 'object') return null;

  const custom = data.custom && typeof data.custom === 'object' ? data.custom : {};
  let kind = null;
  let peer = null;

  const channel = positiveIntegerString(custom.channel_id);
  const chat = positiveIntegerString(custom.chat_id);
  const user = positiveIntegerString(custom.from_id);

  if (channel) {
    kind = 'channel';
    peer = channel;
  } else if (chat) {
    kind = 'chat';
    peer = chat;
  } else if (user) {
    kind = 'user';
    peer = user;
  } else {
    return null;
  }

  const out = {kind, peer};
  const receiver = positiveIntegerString(data.user_id);
  const msg = positiveIntegerString(custom.msg_id, 2147483647);
  const thread = positiveIntegerString(custom.top_msg_id, 2147483647);

  if (receiver) out.user = receiver;
  if (msg) out.msg = msg;
  if (thread) out.thread = thread;
  return out;
}

function appendHandoffParams(url, data) {
  if (data.user) url.searchParams.set('user', data.user);
  url.searchParams.set('kind', data.kind);
  url.searchParams.set('peer', data.peer);
  if (data.msg) url.searchParams.set('msg', data.msg);
  if (data.thread) url.searchParams.set('thread', data.thread);
}

export function buildJerkgramLandingUrl(scope, push) {
  const data = buildJerkgramHandoffData(push);
  if (!data) return null;
  const url = new URL('open.html', scope);
  appendHandoffParams(url, data);
  return url.href;
}

export function buildJerkgramNativeUrl(search) {
  const source = search instanceof URLSearchParams ? search : new URLSearchParams(search);
  const kind = source.get('kind');
  const peer = positiveIntegerString(source.get('peer'));
  if (!peer || !['user', 'chat', 'channel'].includes(kind)) return null;

  const url = new URL('jerkgram://push/open');
  url.searchParams.set('kind', kind);
  url.searchParams.set('peer', peer);

  const receiver = positiveIntegerString(source.get('user'));
  const msg = positiveIntegerString(source.get('msg'), 2147483647);
  const thread = positiveIntegerString(source.get('thread'), 2147483647);
  if (receiver) url.searchParams.set('user', receiver);
  if (msg) url.searchParams.set('msg', msg);
  if (thread) url.searchParams.set('thread', thread);
  return url.href;
}

export function buildJerkgramNativeUrlFromPush(push) {
  const data = buildJerkgramHandoffData(push);
  if (!data) return null;

  const params = new URLSearchParams();
  if (data.user) params.set('user', data.user);
  params.set('kind', data.kind);
  params.set('peer', data.peer);
  if (data.msg) params.set('msg', data.msg);
  if (data.thread) params.set('thread', data.thread);
  return buildJerkgramNativeUrl(params);
}
