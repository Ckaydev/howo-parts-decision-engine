const capture = $('Prepare Archived Capture').first().json;
const response = $input.first().json;

const message = Array.isArray(response.output) ? response.output[0] : null;
const content = message?.content?.find((entry) => entry.type === 'output_text');
let extraction = content?.text;

if (typeof extraction === 'string') {
  extraction = extraction.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  extraction = JSON.parse(extraction);
}
if (!extraction || typeof extraction !== 'object' || Array.isArray(extraction)) {
  throw new Error('OpenAI output did not contain a visual extraction object');
}

const allowedQuality = new Set(['insufficient', 'limited', 'usable', 'clear']);
const allowedViews = new Set([
  'full_item', 'label', 'connector', 'mounting_points', 'packaging', 'unknown',
]);
const allowedFeatureTypes = new Set([
  'shape', 'mounting', 'connector', 'dimension', 'material', 'color', 'marking', 'fitment',
]);
const requireArray = (key) => {
  if (!Array.isArray(extraction[key])) throw new Error(`${key} must be an array`);
};
const requireConfidence = (value, key) => {
  if (typeof value !== 'number' || value < 0 || value > 1) {
    throw new Error(`${key} confidence must be between 0 and 1`);
  }
};

if (typeof extraction.summary !== 'string' || !extraction.summary.trim()) {
  throw new Error('Visual extraction summary is required');
}
if (!allowedQuality.has(extraction.image_quality)) {
  throw new Error('Visual extraction returned an unsupported image_quality');
}
if (!allowedViews.has(extraction.view_type)) {
  throw new Error('Visual extraction returned an unsupported view_type');
}
for (const key of [
  'observed_part_numbers', 'label_texts', 'visual_features', 'fitment_terms', 'questions_needed',
]) requireArray(key);

for (const key of ['observed_part_numbers', 'label_texts']) {
  for (const [index, item] of extraction[key].entries()) {
    if (!item || typeof item.raw_text !== 'string' || !item.raw_text.trim()) {
      throw new Error(`${key}[${index}].raw_text is required`);
    }
    if (typeof item.region !== 'string' || !item.region.trim()) {
      throw new Error(`${key}[${index}].region is required`);
    }
    requireConfidence(item.confidence, `${key}[${index}]`);
  }
}
for (const [index, item] of extraction.visual_features.entries()) {
  if (!item || !allowedFeatureTypes.has(item.feature_type)) {
    throw new Error(`visual_features[${index}].feature_type is unsupported`);
  }
  if (typeof item.feature_name !== 'string' || !item.feature_name.trim()) {
    throw new Error(`visual_features[${index}].feature_name is required`);
  }
  if (typeof item.feature_value !== 'string' || !item.feature_value.trim()) {
    throw new Error(`visual_features[${index}].feature_value is required`);
  }
  requireConfidence(item.confidence, `visual_features[${index}]`);
}
for (const [index, item] of extraction.fitment_terms.entries()) {
  if (!item || typeof item.term !== 'string' || !item.term.trim()) {
    throw new Error(`fitment_terms[${index}].term is required`);
  }
  requireConfidence(item.confidence, `fitment_terms[${index}]`);
}
if (!extraction.questions_needed.every((item) => typeof item === 'string' && item.trim())) {
  throw new Error('questions_needed must contain only non-empty strings');
}

return [{ json: { ...capture, visual_extraction: extraction } }];
