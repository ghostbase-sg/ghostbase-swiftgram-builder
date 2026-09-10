import assert from 'node:assert/strict';
import {
  buildJerkgramHandoffData,
  buildJerkgramLandingUrl,
  buildJerkgramNativeUrl
} from '../webpush-companion/handoff.js';

assert.deepEqual(
  buildJerkgramHandoffData({
    user_id: 42,
    title: 'Alice',
    description: 'secret message text',
    custom: {from_id: '100', msg_id: '7'}
  }),
  {kind: 'user', peer: '100', user: '42', msg: '7'}
);

assert.deepEqual(
  buildJerkgramHandoffData({data: {user_id: '42', custom: {chat_id: '200', msg_id: '8'}}}),
  {kind: 'chat', peer: '200', user: '42', msg: '8'}
);

assert.deepEqual(
  buildJerkgramHandoffData({
    user_id: '42',
    custom: {channel_id: '300', msg_id: '9', top_msg_id: '77'}
  }),
  {kind: 'channel', peer: '300', user: '42', msg: '9', thread: '77'}
);

assert.equal(buildJerkgramHandoffData({custom: {msg_id: '1'}}), null);
assert.equal(buildJerkgramHandoffData({custom: {from_id: '-1', msg_id: '1'}}), null);
assert.equal(buildJerkgramHandoffData({custom: {from_id: '1', msg_id: '2147483648'}}).msg, undefined);

const landing = buildJerkgramLandingUrl('https://push.example/app/', {
  user_id: '42',
  title: 'Alice',
  description: 'TOP SECRET',
  message: 'TOP SECRET 2',
  custom: {from_id: '100', msg_id: '7'}
});
assert.equal(landing, 'https://push.example/app/open.html?user=42&kind=user&peer=100&msg=7');
assert.ok(!landing.includes('Alice'));
assert.ok(!landing.includes('SECRET'));

assert.equal(
  buildJerkgramNativeUrl('?user=42&kind=channel&peer=300&msg=9&thread=77'),
  'jerkgram://push/open?kind=channel&peer=300&user=42&msg=9&thread=77'
);
assert.equal(buildJerkgramNativeUrl('?kind=evil&peer=1'), null);
assert.equal(buildJerkgramNativeUrl('?kind=user&peer=-1'), null);

console.log('webpush handoff tests: PASS');
