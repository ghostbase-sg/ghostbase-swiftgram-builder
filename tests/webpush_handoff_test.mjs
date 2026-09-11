import assert from 'node:assert/strict';
import './webpush_tap_fallback_test.mjs';
import {
  buildJerkgramHandoffData,
  buildJerkgramLandingUrl,
  buildJerkgramNativeUrl
} from '../webpush-companion/handoff.js';
import {buildJerkgramPushPresentation} from '../webpush-companion/presentation.js';

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

// Telegram documents MESSAGE_TEXT loc_args as [sender, message body].
assert.deepEqual(
  buildJerkgramPushPresentation({
    loc_key: 'MESSAGE_TEXT',
    loc_args: ['Masha', 'Привет, как дела?'],
    title: 'Telegram',
    description: 'sent you a message',
    custom: {from_id: '100', msg_id: '11'}
  }),
  {title: 'Masha', body: 'Привет, как дела?'}
);

// Group text: [author, group title, message body].
assert.deepEqual(
  buildJerkgramPushPresentation({
    loc_key: 'CHAT_MESSAGE_TEXT',
    loc_args: ['Alice', 'AR чаты', 'Тест'],
    title: 'Telegram',
    description: 'sent a message',
    custom: {channel_id: '200', msg_id: '12'}
  }),
  {title: 'AR чаты', body: 'Alice: Тест'}
);

// Channel text: [channel title, message body].
assert.deepEqual(
  buildJerkgramPushPresentation({
    loc_key: 'CHANNEL_MESSAGE_TEXT',
    loc_args: ['Jerkgram News', 'Build 141 released'],
    title: 'Telegram',
    description: 'posted a message',
    custom: {channel_id: '300', msg_id: '13'}
  }),
  {title: 'Jerkgram News', body: 'Build 141 released'}
);

// Other private-message types should at least identify the sender, while
// retaining Telegram's supplied description for the body.
assert.deepEqual(
  buildJerkgramPushPresentation({
    loc_key: 'MESSAGE_PHOTO',
    loc_args: ['Masha'],
    title: 'Telegram',
    description: 'sent you a photo',
    custom: {from_id: '100', msg_id: '14'}
  }),
  {title: 'Masha', body: 'sent you a photo'}
);

console.log('webpush handoff tests: PASS');
