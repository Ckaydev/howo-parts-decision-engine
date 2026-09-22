const result = $input.first().json;
const request = $('Prepare Image Decision Request').first().json;
const capture = request.capture;

if (!result.match || !result.rows || !capture) {
  throw new Error('Image decision response is missing match, rows, or capture context');
}

const routed = [{
  route: 'capture_inbox',
  row: {
    ...capture,
    processing_status: result.match.status === 'matched' ? 'processed' : 'needs_review',
    extraction_summary: result.visual_summary || '',
    match_status: result.match.status || '',
    matched_product_id: result.match.product_id || '',
    match_confidence: result.match.confidence ?? '',
  },
}];

for (const row of result.rows.image_evidence || []) {
  routed.push({ route: 'image_evidence', row });
}
for (const row of result.rows.visual_features || []) {
  routed.push({ route: 'visual_feature', row });
}
for (const row of result.rows.review_queue || []) {
  routed.push({ route: 'review_queue', row });
}

return routed.map((item) => ({ json: item }));
