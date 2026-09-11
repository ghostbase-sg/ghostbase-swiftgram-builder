import assert from 'node:assert/strict';
import {
  buildJerkgramTapIdentity,
  findUniqueDisappearedTap,
  normalizeJerkgramOpenUrl
} from '../webpush-companion/tap-fallback.js';

const privatePush = {
  user_id: 42,
  title: 'Masha',
  description: 'TOP SECRET MESSAGE',
  loc_args: ['Masha', 'TOP SECRET MESSAGE'],
  custom: {from_id: '100', msg_id: '7'}
};

assert.equal(
  buildJerkgramTapIdentity(privatePush),
  'v1:42:user:100:7:0'
);
assert.equal(
  buildJerkgramTapIdentity({
    data: {user_id: '42', custom: {chat_id: '200', msg_id: '8', top_msg_id: '77'}}
  }),
  'v1:42:chat:200:8:77'
);
assert.equal(
  buildJerkgramTapIdentity({
    user_id: '42',
    random_id: 12345,
    custom: {channel_id: '300', msg_id: ''}
  }),
  'v1:42:channel:300:r12345:0'
);
assert.equal(buildJerkgramTapIdentity({custom: {msg_id: '1'}}), null);
assert.equal(buildJerkgramTapIdentity({custom: {from_id: '1'}}), null);

const validUrl = 'jerkgram://push/open?kind=user&peer=100&user=42&msg=7';
assert.equal(normalizeJerkgramOpenUrl(validUrl), validUrl);
assert.equal(normalizeJerkgramOpenUrl('jerkgram://push/open?kind=user'), null);
assert.equal(normalizeJerkgramOpenUrl('jerkgram://push/open?kind=evil&peer=100'), null);
assert.equal(normalizeJerkgramOpenUrl('jerkgram://push/open?kind=user&peer=100&x=1'), null);
assert.equal(normalizeJerkgramOpenUrl('https://example.com/'), null);

const now = 1_000_000;
const records = [
  {id: 'a', url: validUrl, expiresAt: now + 60_000},
  {id: 'b', url: 'jerkgram://push/open?kind=chat&peer=200&user=42&msg=8', expiresAt: now + 60_000}
];

assert.deepEqual(
  findUniqueDisappearedTap(['a', 'b'], ['b'], records, now),
  {id: 'a', url: validUrl}
);
assert.equal(findUniqueDisappearedTap(['a', 'b'], ['a', 'b'], records, now), null);
assert.equal(findUniqueDisappearedTap(['a', 'b'], [], records, now), null);
assert.equal(
  findUniqueDisappearedTap(
    ['a'],
    [],
    [{id: 'a', url: validUrl, expiresAt: now - 1}],
    now
  ),
  null
);
assert.equal(
  findUniqueDisappearedTap(
    ['a'],
    [],
    [{id: 'a', url: 'https://example.com/', expiresAt: now + 60_000}],
    now
  ),
  null
);

// Tap records are intentionally metadata-only: no sender/title/body/caption.
assert.deepEqual(Object.keys(records[0]).sort(), ['expiresAt', 'id', 'url']);
assert.ok(!JSON.stringify(records).includes('Masha'));
assert.ok(!JSON.stringify(records).includes('SECRET'));

console.log('webpush tap fallback tests: PASS');
