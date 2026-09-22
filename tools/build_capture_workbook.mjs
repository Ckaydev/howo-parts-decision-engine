import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("outputs/telegram-capture-v1");
await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const colors = {
  navy: "#16324F",
  blue: "#247BA0",
  paleBlue: "#EAF4F8",
  paleGold: "#FFF4D6",
  paleGreen: "#E7F5EC",
  paleRed: "#FDECEC",
  ink: "#17212B",
  muted: "#5F6B76",
  line: "#D7DEE5",
  white: "#FFFFFF",
};

const definitions = [
  {
    name: "Capture_Inbox",
    title: "Raw Capture Inbox",
    note: "Append one row per Telegram message before AI extraction. Never delete or rewrite the original text or source identifiers.",
    headers: [
      "capture_id", "channel", "channel_message_id", "captured_at", "ingested_at",
      "sender_id", "raw_text", "media_type", "media_original_ref", "media_archive_url",
      "transcript", "processing_status", "processing_error", "extraction_summary",
      "match_status", "matched_product_id", "match_confidence"
    ],
    widths: [24, 12, 20, 22, 22, 18, 48, 14, 28, 38, 48, 18, 34, 44, 20, 22, 18],
  },
  {
    name: "Products",
    title: "Product Master",
    note: "One row per canonical or provisional product. Use stable product_id values; do not identify a part from name similarity alone.",
    headers: [
      "product_id", "canonical_name", "primary_part_number", "aliases",
      "additional_part_numbers", "category", "system", "summary",
      "identity_status", "identity_confidence", "created_at", "updated_at"
    ],
    widths: [22, 34, 24, 36, 34, 22, 22, 46, 20, 20, 22, 22],
  },
  {
    name: "Part_Numbers",
    title: "Part Numbers and Cross-references",
    note: "Preserve raw values and place the deterministic comparison form in normalized_part_number.",
    headers: [
      "part_number_id", "product_id", "raw_part_number", "normalized_part_number",
      "number_type", "status", "confidence", "observation_id"
    ],
    widths: [24, 22, 26, 28, 20, 18, 16, 26],
  },
  {
    name: "Variants",
    title: "Product Variants",
    note: "Record distinguishable variants without assuming compatibility. Link every captured variant to its observation.",
    headers: [
      "variant_id", "product_id", "variant_name", "distinguishing_attribute",
      "attribute_value", "application_notes", "status", "confidence", "observation_id"
    ],
    widths: [22, 22, 30, 30, 28, 48, 18, 16, 26],
  },
  {
    name: "Observations",
    title: "Evidence Observations",
    note: "Append-only atomic claims. Facts, user reports, calculations, inferences, and unresolved information must stay distinguishable.",
    headers: [
      "observation_id", "capture_id", "product_id", "variant_id", "claim_type",
      "claim_text", "structured_value", "evidence_class", "confidence",
      "relationship", "review_status", "observed_at"
    ],
    widths: [26, 24, 22, 22, 20, 50, 44, 20, 16, 18, 18, 22],
  },
  {
    name: "Attachments",
    title: "Archived Attachments",
    note: "Store durable Google Drive links here. Telegram file references alone are not the long-term archive.",
    headers: [
      "attachment_id", "capture_id", "media_type", "drive_url", "media_original_ref",
      "original_filename", "mime_type", "transcript", "transcription_confidence"
    ],
    widths: [24, 24, 16, 42, 30, 32, 24, 52, 24],
  },
  {
    name: "Image_Evidence",
    title: "Image and Label Evidence",
    note: "Link each reviewed image interpretation to its archived attachment. OCR and visual descriptions are evidence proposals until a person accepts them.",
    headers: [
      "image_evidence_id", "attachment_id", "capture_id", "product_id", "variant_id",
      "view_type", "visible_label_text", "ocr_text", "evidence_class", "confidence",
      "review_status", "observed_at", "observation_id"
    ],
    widths: [26, 24, 24, 22, 22, 20, 42, 42, 20, 16, 20, 22, 26],
  },
  {
    name: "Visual_Features",
    title: "Visual Identification Features",
    note: "Store one distinguishing feature per row. Use reviewed, specific descriptions such as mounting count, connector layout, dimensions, or visible markings.",
    headers: [
      "feature_id", "image_evidence_id", "product_id", "variant_id", "feature_type",
      "feature_name", "feature_value", "units", "evidence_class", "confidence",
      "observation_id"
    ],
    widths: [24, 26, 22, 22, 20, 30, 38, 16, 20, 16, 26],
  },
  {
    name: "Suppliers",
    title: "Market Contacts and Suppliers",
    note: "One row per supplier or market contact. A supplier record identifies a contact; it does not prove that any item is currently available.",
    headers: [
      "supplier_id", "supplier_name", "market_area", "contact_name",
      "contact_ref", "notes", "status", "updated_at"
    ],
    widths: [22, 34, 28, 28, 34, 48, 18, 22],
  },
  {
    name: "Supplier_Reports",
    title: "Dated Supplier Availability Reports",
    note: "Append dated availability observations. Every report must be reconfirmed before quoting or purchasing; older reports remain as history.",
    headers: [
      "report_id", "supplier_id", "product_id", "variant_id", "raw_part_number",
      "availability_status", "quantity_text", "asking_price", "currency", "observed_at",
      "reconfirm_after", "source_capture_id", "source_reference", "evidence_class",
      "confidence", "notes"
    ],
    widths: [24, 22, 22, 22, 26, 24, 22, 18, 14, 22, 22, 24, 38, 20, 16, 44],
  },
  {
    name: "Review_Queue",
    title: "Human Review Queue",
    note: "Ambiguous identities, new products, and conflicting evidence belong here until a person resolves them.",
    headers: [
      "review_id", "capture_id", "proposed_product_id", "candidate_matches",
      "reason", "questions_needed", "status", "reviewed_at"
    ],
    widths: [24, 24, 24, 52, 34, 52, 18, 22],
  },
  {
    name: "Review_Decisions",
    title: "Human Review Decision Audit",
    note: "Append one immutable row per review decision. This records who accepted, rejected, linked, or provisionally created evidence and why.",
    headers: [
      "decision_id", "review_id", "capture_id", "action", "product_id",
      "canonical_name", "identity_confidence", "accepted_image_evidence_ids",
      "rejected_image_evidence_ids", "confirmed_part_numbers", "reviewer",
      "reviewed_at", "notes"
    ],
    widths: [26, 24, 24, 22, 22, 34, 20, 40, 40, 34, 22, 22, 48],
  },
];

const readMe = workbook.worksheets.add("Read_Me");
readMe.showGridLines = false;
readMe.mergeCells("A1:F1");
readMe.getRange("A1").values = [["HOWO Parts Capture Database"]];
readMe.getRange("A1:F1").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white, size: 18 },
  verticalAlignment: "center",
};
readMe.getRange("A1:F1").format.rowHeight = 34;
readMe.getRange("A3:B9").values = [
  ["Purpose", "Turn rough Telegram text, images, and voice notes into traceable observations linked to known products."],
  ["Source of truth", "Raw messages and media references enter Capture_Inbox first. Structured tabs never replace original evidence."],
  ["Product identity", "Exact part-number matches may link automatically. Photos, OCR, visual features, fuzzy names, new numbers, and conflicts produce candidates for Review_Queue."],
  ["Attachments", "Archive media in Google Drive and store the durable link in Attachments and Capture_Inbox."],
  ["Review habit", "Resolve Review_Queue items before relying on identity, variant, or fitment claims. Reconfirm every supplier report before quoting or purchasing."],
  ["Multiple values", "In Products, separate aliases and additional part numbers with a vertical bar: value one | value two."],
  ["Date format", "Use ISO 8601 timestamps, for example 2026-08-27T14:30:00+01:00."],
];
for (let row = 3; row <= 9; row += 1) {
  readMe.mergeCells(`B${row}:F${row}`);
}
readMe.getRange("A3:A9").format = {
  fill: colors.paleBlue,
  font: { bold: true, color: colors.navy },
  verticalAlignment: "top",
};
readMe.getRange("B3:F9").format = {
  font: { color: colors.ink },
  wrapText: true,
  verticalAlignment: "top",
};
readMe.getRange("A3:F9").format.borders = {
  preset: "inside",
  style: "thin",
  color: colors.line,
};
readMe.getRange("A11:F11").merge();
readMe.getRange("A11").values = [["Recommended workflow"]];
readMe.getRange("A11:F11").format = {
  fill: colors.blue,
  font: { bold: true, color: colors.white, size: 13 },
};
readMe.getRange("A12:F16").values = [
  ["1", "Capture", "Send text, photos, documents, or a short voice note to the private Telegram bot.", null, null, null],
  ["2", "Preserve", "n8n appends the raw input and archives media before extraction.", null, null, null],
  ["3", "Structure", "AI proposes claims; deterministic validation checks identifiers and allowed values.", null, null, null],
  ["4", "Match", "Confirmed part numbers take precedence. Ambiguous names are never silently merged.", null, null, null],
  ["5", "Review", "The bot confirms what was stored or asks for the missing evidence.", null, null, null],
];
for (let row = 12; row <= 16; row += 1) {
  readMe.mergeCells(`C${row}:F${row}`);
}
readMe.getRange("A12:A16").format = {
  fill: colors.paleGold,
  font: { bold: true, color: colors.navy },
  horizontalAlignment: "center",
};
readMe.getRange("B12:B16").format = { font: { bold: true, color: colors.navy } };
readMe.getRange("C12:F16").format = { wrapText: true, font: { color: colors.ink } };
readMe.getRange("A12:F16").format.borders = {
  preset: "inside",
  style: "thin",
  color: colors.line,
};
readMe.getRange("A:A").format.columnWidth = 18;
readMe.getRange("B:B").format.columnWidth = 26;
readMe.getRange("C:F").format.columnWidth = 20;
readMe.getRange("A3:F9").format.rowHeight = 44;
readMe.getRange("A12:F16").format.rowHeight = 32;

for (const definition of definitions) {
  const sheet = workbook.worksheets.add(definition.name);
  sheet.showGridLines = false;
  const lastColumn = columnName(definition.headers.length);
  sheet.mergeCells(`A1:${lastColumn}1`);
  sheet.getRange("A1").values = [[definition.title]];
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastColumn}1`).format.rowHeight = 32;
  sheet.mergeCells(`A2:${lastColumn}2`);
  sheet.getRange("A2").values = [[definition.note]];
  sheet.getRange(`A2:${lastColumn}2`).format = {
    fill: colors.paleBlue,
    font: { color: colors.muted, italic: true },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${lastColumn}2`).format.rowHeight = 34;
  sheet.getRange(`A3:${lastColumn}3`).values = [definition.headers];
  sheet.getRange(`A3:${lastColumn}3`).format = {
    fill: colors.blue,
    font: { bold: true, color: colors.white },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A3:${lastColumn}3`).format.rowHeight = 36;
  sheet.getRange(`A3:${lastColumn}4`).format.borders = {
    preset: "inside",
    style: "thin",
    color: colors.line,
  };
  definition.widths.forEach((width, index) => {
    sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
  });
  sheet.freezePanes.freezeRows(3);
}

const lists = workbook.worksheets.add("Lists");
lists.showGridLines = false;
lists.getRange("A1:M1").values = [[
  "evidence_class", "processing_status", "media_type", "identity_status",
  "review_status", "relationship", "number_type", "review_queue_status",
  "view_type", "feature_type", "availability_status", "supplier_status",
  "review_action"
]];
lists.getRange("A1:L1").format = {
  fill: colors.navy,
  font: { bold: true, color: colors.white },
  wrapText: true,
};
lists.getRange("A2:A6").values = [["observed"], ["user_reported"], ["calculated"], ["inferred"], ["unresolved"]];
lists.getRange("B2:B6").values = [["received"], ["extracting"], ["needs_review"], ["structured"], ["failed"]];
lists.getRange("C2:C7").values = [["none"], ["image"], ["voice"], ["audio"], ["document"], ["video"]];
lists.getRange("D2:D4").values = [["provisional"], ["confirmed"], ["rejected"]];
lists.getRange("E2:E5").values = [["unreviewed"], ["accepted"], ["rejected"], ["needs_information"]];
lists.getRange("F2:F5").values = [["new"], ["confirms"], ["updates"], ["conflicts"]];
lists.getRange("G2:G5").values = [["oem"], ["cross_reference"], ["market_alias"], ["captured"]];
lists.getRange("H2:H5").values = [["open"], ["resolved"], ["rejected"], ["dismissed"]];
lists.getRange("I2:I7").values = [["full_item"], ["label"], ["connector"], ["mounting_points"], ["packaging"], ["unknown"]];
lists.getRange("J2:J9").values = [["shape"], ["mounting"], ["connector"], ["dimension"], ["material"], ["color"], ["marking"], ["fitment"]];
lists.getRange("K2:K5").values = [["reported_available"], ["reported_low_stock"], ["reported_unavailable"], ["unknown"]];
lists.getRange("L2:L4").values = [["active"], ["inactive"], ["unverified"]];
lists.getRange("M2:M4").values = [["link_existing"], ["create_provisional"], ["reject"]];
lists.getRange("A:M").format.columnWidth = 22;
lists.freezePanes.freezeRows(1);

applyValidation(workbook.worksheets.getItem("Capture_Inbox"), "H4:H503", "Lists!$C$2:$C$7");
applyValidation(workbook.worksheets.getItem("Capture_Inbox"), "L4:L503", "Lists!$B$2:$B$6");
applyValidation(workbook.worksheets.getItem("Products"), "I4:I503", "Lists!$D$2:$D$4");
applyValidation(workbook.worksheets.getItem("Part_Numbers"), "E4:E503", "Lists!$G$2:$G$5");
applyValidation(workbook.worksheets.getItem("Observations"), "H4:H503", "Lists!$A$2:$A$6");
applyValidation(workbook.worksheets.getItem("Observations"), "J4:J503", "Lists!$F$2:$F$5");
applyValidation(workbook.worksheets.getItem("Observations"), "K4:K503", "Lists!$E$2:$E$5");
applyValidation(workbook.worksheets.getItem("Image_Evidence"), "F4:F503", "Lists!$I$2:$I$7");
applyValidation(workbook.worksheets.getItem("Image_Evidence"), "I4:I503", "Lists!$A$2:$A$6");
applyValidation(workbook.worksheets.getItem("Image_Evidence"), "K4:K503", "Lists!$E$2:$E$5");
applyValidation(workbook.worksheets.getItem("Visual_Features"), "E4:E503", "Lists!$J$2:$J$9");
applyValidation(workbook.worksheets.getItem("Visual_Features"), "I4:I503", "Lists!$A$2:$A$6");
applyValidation(workbook.worksheets.getItem("Suppliers"), "G4:G503", "Lists!$L$2:$L$4");
applyValidation(workbook.worksheets.getItem("Supplier_Reports"), "F4:F503", "Lists!$K$2:$K$5");
applyValidation(workbook.worksheets.getItem("Supplier_Reports"), "N4:N503", "Lists!$A$2:$A$6");
applyValidation(workbook.worksheets.getItem("Review_Queue"), "G4:G503", "Lists!$H$2:$H$5");
applyValidation(workbook.worksheets.getItem("Review_Decisions"), "D4:D503", "Lists!$M$2:$M$4");

for (const definition of definitions) {
  const sheet = workbook.worksheets.getItem(definition.name);
  const confidenceHeader = definition.headers.indexOf("confidence");
  const identityConfidenceHeader = definition.headers.indexOf("identity_confidence");
  const matchConfidenceHeader = definition.headers.indexOf("match_confidence");
  for (const index of [confidenceHeader, identityConfidenceHeader, matchConfidenceHeader]) {
    if (typeof index === "number" && index >= 0) {
      sheet.getRange(`${columnName(index + 1)}4:${columnName(index + 1)}503`).format.numberFormat = "0%";
    }
  }
}

workbook.worksheets.getItem("Review_Queue").getRange("G4:G503").conditionalFormats.add(
  "containsText",
  { text: "open", format: { fill: colors.paleGold, font: { color: "#7A4D00", bold: true } } },
);
workbook.worksheets.getItem("Capture_Inbox").getRange("L4:L503").conditionalFormats.add(
  "containsText",
  { text: "failed", format: { fill: colors.paleRed, font: { color: "#9B1C1C", bold: true } } },
);
workbook.worksheets.getItem("Capture_Inbox").getRange("L4:L503").conditionalFormats.add(
  "containsText",
  { text: "structured", format: { fill: colors.paleGreen, font: { color: "#1B5E37", bold: true } } },
);

const previews = ["Read_Me", ...definitions.map((definition) => definition.name), "Lists"];
workbook.recalculate();
for (const sheetName of previews) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(
    path.join(outputDir, `preview-${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const inspect = await workbook.inspect({
  kind: "sheet,table",
  include: "id,name",
  maxChars: 5000,
  tableMaxRows: 5,
  tableMaxCols: 20,
});
console.log(inspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "howo_parts_capture_template.xlsx"));

function applyValidation(sheet, range, formula1) {
  sheet.getRange(range).dataValidation = {
    rule: { type: "list", formula1 },
  };
}

function columnName(number) {
  let result = "";
  let current = number;
  while (current > 0) {
    current -= 1;
    result = String.fromCharCode(65 + (current % 26)) + result;
    current = Math.floor(current / 26);
  }
  return result;
}
