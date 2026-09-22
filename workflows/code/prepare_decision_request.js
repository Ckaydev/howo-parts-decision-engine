const validated = $('Validate Extraction Evidence').first().json;
const catalogue = $input.first().json;
if (!Array.isArray(catalogue.products)) {
  throw new Error('Catalogue context is missing products');
}

return [
  {
    json: {
      capture: {
        capture_id: validated.capture_id,
        channel: validated.channel,
        channel_message_id: validated.channel_message_id,
        captured_at: validated.captured_at,
        ingested_at: validated.ingested_at,
        sender_id: validated.sender_id,
        raw_text: validated.raw_text || null,
        media_type: validated.media_type || 'none',
        media_original_ref: validated.media_original_ref || null,
        media_archive_url: validated.media_archive_url || null,
        transcript: validated.transcript || null,
        processing_status: validated.processing_status || 'received',
        processing_error: validated.processing_error || null,
      },
      extraction: validated.extraction,
      products: catalogue.products,
      catalogue_diagnostics: catalogue.diagnostics || {},
    },
  },
];
