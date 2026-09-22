const update = $json;
const message = update.message ?? update.edited_message ?? update.channel_post;
if (!message) {
  throw new Error('This workflow only accepts Telegram message updates.');
}

const selectMedia = (source) => {
  if (!source || typeof source !== 'object') {
    return { mediaType: 'none', media: null };
  }
  const photos = Array.isArray(source.photo) ? source.photo : [];
  const candidates = [
    ['voice', source.voice],
    ['audio', source.audio],
    ['image', photos.length ? photos[photos.length - 1] : null],
    ['document', source.document],
    ['video', source.video],
  ];
  const selected = candidates.find(([, candidate]) => candidate?.file_id);
  return selected
    ? { mediaType: selected[0], media: selected[1] }
    : { mediaType: 'none', media: null };
};

const chatId = String(message.chat?.id ?? '');
const messageId = String(message.message_id ?? '');
if (!chatId || !messageId) {
  throw new Error('Telegram update is missing chat.id or message_id.');
}

const directSelection = selectMedia(message);
const repliedMessage = message.reply_to_message;
const replySelection = selectMedia(repliedMessage);
const usesReplyMedia =
  directSelection.mediaType === 'none' && replySelection.mediaType !== 'none';
const selected = usesReplyMedia ? replySelection : directSelection;
const mediaSourceMessageId = usesReplyMedia
  ? String(repliedMessage.message_id ?? '')
  : messageId;

const capture = {
  capture_id: `cap_telegram_${chatId}_${messageId}`,
  channel: 'telegram',
  channel_message_id: messageId,
  captured_at: new Date(Number(message.date) * 1000).toISOString(),
  ingested_at: new Date().toISOString(),
  sender_id: String(message.from?.id ?? ''),
  raw_text: message.text ?? message.caption ?? '',
  media_type: selected.mediaType,
  media_original_ref: selected.media?.file_id ?? '',
  media_archive_url: '',
  transcript: '',
  processing_status: 'received',
  processing_error: '',
  extraction_summary: '',
  match_status: '',
  matched_product_id: '',
  match_confidence: '',
  chat_id: chatId,
  original_file_unique_id: selected.media?.file_unique_id ?? '',
  original_filename: selected.media?.file_name ?? '',
  mime_type: selected.media?.mime_type ?? '',
  media_source_message_id: mediaSourceMessageId,
  related_capture_id: usesReplyMedia
    ? `cap_telegram_${chatId}_${mediaSourceMessageId}`
    : '',
  relation_type: usesReplyMedia ? 'reply_to_media' : '',
};

return [{
  json: capture,
  binary: $input.item.binary ?? {},
  pairedItem: { item: 0 },
}];
