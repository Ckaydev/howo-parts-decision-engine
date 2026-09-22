const validated = $('Validate Visual Extraction').first().json;

const catalogue = $input.first().json;
if (!Array.isArray(catalogue.products) || !Array.isArray(catalogue.evidence_profiles)) {
  throw new Error('Catalogue context is missing products or evidence_profiles');
}

const capture = {
  capture_id: validated.capture_id,
  channel: validated.channel,
  channel_message_id: validated.channel_message_id,
  captured_at: validated.captured_at,
  ingested_at: validated.ingested_at,
  sender_id: validated.sender_id,
  raw_text: validated.raw_text || '',
  media_type: validated.media_type,
  media_original_ref: validated.media_original_ref || '',
  media_archive_url: validated.media_archive_url || '',
  transcript: validated.transcript || '',
  processing_status: validated.processing_status || 'received',
  processing_error: '',
};

return [{
  json: {
    capture_id: validated.capture_id,
    attachment_id: validated.attachment_id,
    captured_at: validated.captured_at,
    text_reference: {
      mentioned_name: null,
      confirmed_part_numbers: [],
    },
    visual_extraction: validated.visual_extraction,
    products: catalogue.products,
    evidence_profiles: catalogue.evidence_profiles,
    catalogue_diagnostics: catalogue.diagnostics || {},
    capture,
  },
}];
