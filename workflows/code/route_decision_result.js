const result = $input.first().json;

if (!result.capture || !result.match || !result.rows) {
  throw new Error('Decision engine response is missing capture, match, or rows');
}

const routed = [
  {
    route: 'capture_inbox',
    match_key: 'capture_id',
    row: {
      ...result.capture,
      extraction_summary: result.extraction_summary || '',
      match_status: result.match.status || '',
      matched_product_id: result.match.product_id || '',
      match_confidence: result.match.confidence ?? '',
    },
  },
];

for (const row of result.rows.observations || []) {
  routed.push({ route: 'observation', match_key: 'observation_id', row });
}
for (const row of result.rows.part_numbers || []) {
  routed.push({ route: 'part_number', match_key: 'part_number_id', row });
}
for (const row of result.rows.review_queue || []) {
  routed.push({ route: 'review_queue', match_key: 'review_id', row });
}

return routed.map((item) => ({ json: item }));
