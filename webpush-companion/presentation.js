// @ts-nocheck

function cleanText(value) {
  return typeof value === 'string' && value.length ? value : '';
}

function arg(args, index) {
  if(!Array.isArray(args)) return '';
  return cleanText(args[index]);
}

/**
 * Build only the visible title/body for Jerkgram Notifications.
 *
 * Telegram documents loc_key + loc_args as the canonical push presentation
 * inputs. Keep this helper intentionally small and deterministic: it fixes the
 * common incoming-message cases without turning the companion into a second
 * localization engine. The service worker retains Telegram Web K's existing
 * no-preview/privacy fallback after this helper runs.
 */
export function buildJerkgramPushPresentation(push) {
  const fallbackTitle = cleanText(push?.title) || 'Telegram';
  const fallbackBody = cleanText(push?.description);
  const key = cleanText(push?.loc_key);
  const args = Array.isArray(push?.loc_args) ? push.loc_args : [];

  // Private text message: [message author, message body].
  if(key === 'MESSAGE_TEXT') {
    return {
      title: arg(args, 0) || fallbackTitle,
      body: arg(args, 1) || fallbackBody
    };
  }

  // Other private incoming-message types still identify the sender in the
  // title. Telegram's supplied description remains the media/service body.
  if(key === 'MESSAGES' || key.startsWith('MESSAGE_')) {
    return {
      title: arg(args, 0) || fallbackTitle,
      body: fallbackBody
    };
  }

  // Group text message: [message author, chat name, message body].
  if(key === 'CHAT_MESSAGE_TEXT') {
    const author = arg(args, 0);
    const message = arg(args, 2);
    return {
      title: arg(args, 1) || fallbackTitle,
      body: author && message ? `${author}: ${message}` : (message || fallbackBody)
    };
  }

  // Channel/supergroup broadcast text: [channel name, message body].
  if(key === 'CHANNEL_MESSAGE_TEXT') {
    return {
      title: arg(args, 0) || fallbackTitle,
      body: arg(args, 1) || fallbackBody
    };
  }

  return {title: fallbackTitle, body: fallbackBody};
}
