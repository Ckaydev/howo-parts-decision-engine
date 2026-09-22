const capture = $('Prepare Extraction Input').first().json;
const response = $input.first().json;

const message = Array.isArray(response.output) ? response.output[0] : null;
const content = message?.content?.find((entry) => entry.type === 'output_text');
let extraction = content?.text;

if (typeof extraction === 'string') {
  extraction = JSON.parse(extraction);
}
if (!extraction || typeof extraction !== 'object' || Array.isArray(extraction)) {
  throw new Error('OpenAI output did not contain a structured extraction object');
}

const sourceText = String(
  capture.capture_text || capture.transcript || capture.raw_text || '',
);
const sourceLower = sourceText.toLocaleLowerCase();
const issues = [];
const originalExtraction = JSON.parse(JSON.stringify(extraction));

const reference =
  extraction.product_reference && typeof extraction.product_reference === 'object'
    ? { ...extraction.product_reference }
    : { mentioned_name: null, mentioned_part_numbers: [] };

if (reference.mentioned_name) {
  const name = String(reference.mentioned_name);
  if (!sourceLower.includes(name.toLocaleLowerCase())) {
    issues.push({
      code: 'unsupported_product_name',
      value: name,
      message: 'Product name was not stated exactly in the capture text',
    });
    reference.mentioned_name = null;
  }
}

const statedNumbers = Array.isArray(reference.mentioned_part_numbers)
  ? reference.mentioned_part_numbers.map(String)
  : [];
reference.mentioned_part_numbers = statedNumbers.filter((number) => {
  if (sourceText.includes(number)) return true;
  issues.push({
    code: 'unsupported_part_number',
    value: number,
    message: 'Part number was not present exactly in the capture text',
  });
  return false;
});

const claims = Array.isArray(extraction.claims)
  ? extraction.claims.map((claim) => ({ ...claim }))
  : [];
for (const claim of claims) {
  if (claim.claim_type !== 'part_number') continue;
  if (
    claim.structured_value == null &&
    reference.mentioned_part_numbers.length === 1
  ) {
    claim.structured_value = reference.mentioned_part_numbers[0];
  }
  if (
    claim.structured_value != null &&
    !sourceText.includes(String(claim.structured_value))
  ) {
    issues.push({
      code: 'unsupported_claim_part_number',
      value: String(claim.structured_value),
      message: 'Part-number claim was not supported by the capture text',
    });
    claim.structured_value = null;
    claim.evidence_class = 'unresolved';
  }
}

const validatedExtraction = {
  ...extraction,
  product_reference: reference,
  claims,
};

return [
  {
    json: {
      ...capture,
      extraction_raw: originalExtraction,
      extraction: validatedExtraction,
      extraction_summary: validatedExtraction.summary || '',
      extraction_validation_status: issues.length ? 'needs_review' : 'passed',
      extraction_validation_issues: issues,
    },
  },
];
