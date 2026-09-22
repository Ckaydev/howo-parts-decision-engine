const capture = $('Normalize Telegram Capture').item.json;
const downloaded = $('Download Telegram File').item;
const driveFileId = $json.id;
const binaryData = downloaded.binary?.data;

if (!binaryData) {
  throw new Error('Downloaded Telegram file is missing binary data.');
}

const extensionByMime = {
  'audio/ogg': '.ogg',
  'audio/mpeg': '.mp3',
  'audio/mp4': '.m4a',
  'audio/wav': '.wav',
  'audio/webm': '.webm',
  'image/jpeg': '.jpg',
  'image/png': '.png',
  'image/webp': '.webp',
};
const mimeType = String(capture.mime_type || binaryData.mimeType || '').trim();
const receivedName = String(
  capture.original_filename || binaryData.fileName || 'attachment',
).trim() || 'attachment';
const hasExtension = /\.[A-Za-z0-9]{2,5}$/.test(receivedName);
const normalizedFilename = hasExtension
  ? receivedName
  : `${receivedName}${extensionByMime[mimeType] || ''}`;
const normalizedBinary = {
  ...binaryData,
  fileName: normalizedFilename,
  mimeType,
};

return [{
  json: {
    ...capture,
    attachment_id: `att_${capture.capture_id}`,
    original_filename: normalizedFilename,
    mime_type: mimeType,
    drive_url: `https://drive.google.com/file/d/${driveFileId}/view`,
    media_archive_url:
      `https://drive.google.com/file/d/${driveFileId}/view`,
  },
  binary: {
    data: normalizedBinary,
  },
}];
