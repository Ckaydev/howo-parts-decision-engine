import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const defaultWorkflowPath = path.join(
  here,
  "..",
  "workflows",
  "telegram_raw_capture_v1.json",
);
const args = process.argv.slice(2);
const option = (name) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
};
const inputPath = path.resolve(option("--input") || defaultWorkflowPath);
const outputPath = path.resolve(option("--output") || inputPath);
const parsedInput = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const wasArray = Array.isArray(parsedInput);
if (wasArray && parsedInput.length !== 1) {
  throw new Error("Expected exactly one workflow in array export");
}
const workflow = wasArray ? parsedInput[0] : parsedInput;
if (!workflow || typeof workflow !== "object" || !Array.isArray(workflow.nodes)) {
  throw new Error("Input does not contain an n8n workflow object");
}
const clone = (value) => JSON.parse(JSON.stringify(value));
const sheetReference = workflow.nodes.find(
  (node) => node.name === "Upsert Raw Capture",
);
const telegramReference = workflow.nodes.find(
  (node) => node.name === "Confirm Raw Capture",
);
const documentId = clone(
  sheetReference?.parameters?.documentId || {
    __rl: true,
    value: "REPLACE_WITH_GOOGLE_SPREADSHEET_ID",
    mode: "id",
  },
);
const sheetCredentials = sheetReference?.credentials
  ? clone(sheetReference.credentials)
  : undefined;
const telegramCredentials = telegramReference?.credentials
  ? clone(telegramReference.credentials)
  : undefined;

const withCredentials = (node, credentials) => {
  if (credentials) node.credentials = clone(credentials);
  return node;
};

const readSheet = (name, sheetName, position, id) => withCredentials({
  parameters: {
    documentId: clone(documentId),
    sheetName: { __rl: true, value: sheetName, mode: "name" },
    options: {
      dataLocationOnSheet: {
        values: {
          rangeDefinition: "specifyRange",
          headerRow: 3,
          firstDataRow: 4,
        },
      },
    },
  },
  type: "n8n-nodes-base.googleSheets",
  typeVersion: 4.7,
  position,
  id,
  name,
  alwaysOutputData: true,
}, sheetCredentials);

const schema = (headers) =>
  headers.map((header) => ({
    id: header,
    displayName: header,
    required: false,
    defaultMatch: false,
    display: true,
    type: "string",
    canBeUsedToMatch: true,
  }));

const upsertSheet = (name, sheetName, matchKey, headers, position, id) => withCredentials({
  parameters: {
    operation: "appendOrUpdate",
    documentId: clone(documentId),
    sheetName: { __rl: true, value: sheetName, mode: "name" },
    columns: {
      mappingMode: "defineBelow",
      value: Object.fromEntries(
        headers.map((header) => [header, `={{ $json.row.${header} }}`]),
      ),
      matchingColumns: [matchKey],
      schema: schema(headers),
      attemptToConvertTypes: false,
      convertFieldsToString: false,
    },
    options: {
      locationDefine: { values: { headerRow: 3, firstDataRow: 4 } },
    },
  },
  type: "n8n-nodes-base.googleSheets",
  typeVersion: 4.7,
  position,
  id,
  name,
}, sheetCredentials);

const condition = (route, id) => ({
  conditions: {
    options: {
      caseSensitive: true,
      leftValue: "",
      typeValidation: "strict",
      version: 2,
    },
    conditions: [
      {
        id,
        leftValue: "={{ $json.route }}",
        rightValue: route,
        operator: { type: "string", operation: "equals" },
      },
    ],
    combinator: "and",
  },
  renameOutput: true,
  outputKey: route,
});

const reviewNodeNames = new Set([
  "Prepare Review Notification",
  "Notify Review Needed",
  "Is Review Command?",
  "Read Review Queue for Command",
  "Read Products for Review Command",
  "Read Part Numbers for Review Command",
  "Read Image Evidence for Review Command",
  "Prepare Review Command Request",
  "Resolve Review Command",
  "Route Review Resolution",
  "Switch Review Resolution Route",
  "Upsert Resolved Product",
  "Upsert Review Decision",
  "Confirm Review Resolution",
]);

workflow.nodes = workflow.nodes.filter((node) => !reviewNodeNames.has(node.name));
for (const name of reviewNodeNames) delete workflow.connections[name];

const detectionExpression = `={{ (() => {
  const message = $json.message ?? $json.edited_message ?? $json.channel_post ?? {};
  const text = String(message.text ?? message.caption ?? '').trim();
  const replyText = String(
    message.reply_to_message?.text ?? message.reply_to_message?.caption ?? ''
  );
  const full = /^\\/(?:resolve|review)(?:@\\w+)?\\s+/i.test(text);
  const shorthand = /^(?:link|new|reject)\\b/i.test(text)
    && /(?:^|\\n)\\s*Review ID:\\s*[A-Za-z0-9_-]+/i.test(replyText);
  return full || shorthand;
})() }}`;

const prepareCode = `const update = $('Telegram Capture').first().json;
const message = update.message ?? update.edited_message ?? update.channel_post;
if (!message) throw new Error('Telegram review command is missing a message');

const rows = (name) => $(name).all()
  .map((item) => item.json)
  .filter((row) => Object.values(row).some((value) => String(value ?? '').trim()));

return [{
  json: {
    message: {
      text: String(message.text ?? message.caption ?? ''),
      reply_text: String(
        message.reply_to_message?.text ?? message.reply_to_message?.caption ?? ''
      ),
      sender_id: String(message.from?.id ?? ''),
      chat_id: String(message.chat?.id ?? ''),
      message_id: String(message.message_id ?? ''),
      sent_at: new Date(Number(message.date) * 1000).toISOString(),
    },
    review_queue: rows('Read Review Queue for Command'),
    products: rows('Read Products for Review Command'),
    part_numbers: rows('Read Part Numbers for Review Command'),
    image_evidence: rows('Read Image Evidence for Review Command'),
  },
}];`;

const routeCode = `const result = $input.first().json;
if (!result.rows || !result.decision) {
  throw new Error('Review resolution response is missing rows or decision');
}

const routes = [
  ['review_queue', 'review_queue'],
  ['review_decisions', 'review_decision'],
  ['products', 'product'],
  ['part_numbers', 'part_number'],
  ['observations', 'observation'],
  ['image_evidence', 'image_evidence'],
];
const routed = [];
for (const [key, route] of routes) {
  for (const row of result.rows[key] || []) routed.push({ route, row });
}
return routed.map((item) => ({ json: item }));`;

const notificationCode = `const row = $input.first().json;
if (String(row.status || '').toLowerCase() !== 'open') return [];

const parseList = (value) => {
  if (Array.isArray(value)) return value;
  if (typeof value !== 'string' || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const candidates = parseList(row.candidate_matches).slice(0, 3);
const questions = parseList(row.questions_needed).slice(0, 3);
const lines = [
  'Review needed',
  \`Review ID: \${row.review_id}\`,
  \`Reason: \${row.reason || 'identity requires confirmation'}\`,
];
if (candidates.length) {
  lines.push('', 'Candidates:');
  for (const [index, candidate] of candidates.entries()) {
    const score = Number(candidate.score);
    const percentage = Number.isFinite(score)
      ? \` — \${Math.round(score * 100)}%\`
      : '';
    lines.push(
      \`\${index + 1}. \${candidate.canonical_name || 'Unnamed product'} (\${candidate.product_id})\${percentage}\`,
    );
  }
}
if (questions.length) {
  lines.push('', 'Check:');
  for (const question of questions) lines.push(\`- \${question}\`);
}
lines.push(
  '',
  'Reply to this message with one decision:',
  'link PRODUCT_ID',
  'link PRODUCT_ID --accept-image',
  'new "PRODUCT NAME"',
  'reject',
  '',
  'Only add --pn=PART_NUMBER after checking the physical label.',
);
return [{ json: { ...row, notification_text: lines.join('\\n') } }];`;

workflow.nodes.push(
  {
    parameters: { jsCode: notificationCode },
    type: "n8n-nodes-base.code",
    typeVersion: 2,
    position: [5440, -192],
    id: "10282fdc-b36e-58a8-87d2-260877b0bf4a",
    name: "Prepare Review Notification",
  },
  withCredentials({
    parameters: {
      chatId: "={{ $('Normalize Telegram Capture').item.json.chat_id }}",
      text: "={{ $json.notification_text }}",
      additionalFields: { appendAttribution: false },
    },
    type: "n8n-nodes-base.telegram",
    typeVersion: 1.2,
    position: [5664, -192],
    id: "74e528f8-39db-5c82-9a0e-5903d3193651",
    name: "Notify Review Needed",
  }, telegramCredentials),
  {
    parameters: {
      conditions: {
        options: {
          caseSensitive: true,
          leftValue: "",
          typeValidation: "strict",
          version: 3,
        },
        conditions: [
          {
            id: "8c00f3dd-fc44-5b87-a51b-4c0ce58124be",
            leftValue: detectionExpression,
            rightValue: "",
            operator: {
              type: "boolean",
              operation: "true",
              singleValue: true,
            },
          },
        ],
        combinator: "and",
      },
      options: {},
    },
    type: "n8n-nodes-base.if",
    typeVersion: 2.3,
    position: [800, -320],
    id: "47584cb1-e95f-5792-9f1d-a75b60c9aa96",
    name: "Is Review Command?",
  },
  readSheet(
    "Read Review Queue for Command",
    "Review_Queue",
    [1024, -1216],
    "793772dd-2f8d-581d-884d-c1f34f267298",
  ),
  readSheet(
    "Read Products for Review Command",
    "Products",
    [1248, -1216],
    "ace5ca85-5f91-5cee-951f-d501f7e667e4",
  ),
  readSheet(
    "Read Part Numbers for Review Command",
    "Part_Numbers",
    [1472, -1216],
    "fd167d4a-f97f-5f87-9c6e-0777bd04f75e",
  ),
  readSheet(
    "Read Image Evidence for Review Command",
    "Image_Evidence",
    [1696, -1216],
    "9cd14a5f-3e27-532c-a857-e558b874095a",
  ),
  {
    parameters: { jsCode: prepareCode },
    type: "n8n-nodes-base.code",
    typeVersion: 2,
    position: [1920, -1216],
    id: "401fa63f-0a45-5f86-8b8f-ab75cc76ba19",
    name: "Prepare Review Command Request",
  },
  {
    parameters: {
      method: "POST",
      url: "http://howo-capture:8765/v1/resolve-review-command",
      sendBody: true,
      specifyBody: "json",
      jsonBody: "={{ $json }}",
      options: {},
    },
    type: "n8n-nodes-base.httpRequest",
    typeVersion: 4.3,
    position: [2144, -1216],
    id: "49f55428-c5ca-54ea-9c1f-3b0a98f1e43d",
    name: "Resolve Review Command",
  },
  {
    parameters: { jsCode: routeCode },
    type: "n8n-nodes-base.code",
    typeVersion: 2,
    position: [2368, -1216],
    id: "b6198d1f-51e8-55e9-8022-9b84de73a260",
    name: "Route Review Resolution",
  },
  {
    parameters: {
      mode: "rules",
      rules: {
        values: [
          condition("review_queue", "f4e978c1-c5a3-50c4-a9c0-95bbf4ac45bc"),
          condition("review_decision", "f381ed75-b0f3-5a20-b2fa-b2499573b218"),
          condition("product", "ee8ae239-f9d4-5cf3-b5da-c2d81d825213"),
          condition("part_number", "0cfda001-190e-5e0d-b868-00e50bd5fcb9"),
          condition("observation", "bca76b59-6a6f-5419-99d0-42c4ec87c768"),
          condition("image_evidence", "5c197813-6ab0-5c89-81cb-e58f9a4563e9"),
        ],
      },
      options: { fallbackOutput: "none" },
    },
    type: "n8n-nodes-base.switch",
    typeVersion: 3.3,
    position: [2592, -1216],
    id: "4eec50ca-e74e-599a-8e4b-2b663be47a84",
    name: "Switch Review Resolution Route",
  },
  upsertSheet(
    "Upsert Resolved Product",
    "Products",
    "product_id",
    [
      "product_id",
      "canonical_name",
      "primary_part_number",
      "aliases",
      "additional_part_numbers",
      "category",
      "system",
      "summary",
      "identity_status",
      "identity_confidence",
      "created_at",
      "updated_at",
    ],
    [2848, -1120],
    "25f41b34-f93c-527c-8ea1-2098b1ca7882",
  ),
  upsertSheet(
    "Upsert Review Decision",
    "Review_Decisions",
    "decision_id",
    [
      "decision_id",
      "review_id",
      "capture_id",
      "action",
      "product_id",
      "canonical_name",
      "identity_confidence",
      "accepted_image_evidence_ids",
      "rejected_image_evidence_ids",
      "confirmed_part_numbers",
      "reviewer",
      "reviewed_at",
      "notes",
    ],
    [2848, -1248],
    "d63f5fa1-d17a-5741-8f05-f92e495e8f60",
  ),
  withCredentials({
    parameters: {
      chatId:
        "={{ String(($('Telegram Capture').first().json.message ?? $('Telegram Capture').first().json.edited_message ?? $('Telegram Capture').first().json.channel_post).chat.id) }}",
      text: "={{ $('Resolve Review Command').first().json.confirmation_text }}",
      additionalFields: { appendAttribution: false },
    },
    type: "n8n-nodes-base.telegram",
    typeVersion: 1.2,
    position: [3072, -1248],
    id: "167b9e70-8733-52b3-9446-2741dbc9e3ec",
    name: "Confirm Review Resolution",
  }, telegramCredentials),
);

workflow.connections["Telegram Capture"] = {
  main: [[{ node: "Is Review Command?", type: "main", index: 0 }]],
};
workflow.connections["Is Review Command?"] = {
  main: [
    [{ node: "Read Review Queue for Command", type: "main", index: 0 }],
    [{ node: "Normalize Telegram Capture", type: "main", index: 0 }],
  ],
};

const sequence = [
  "Read Review Queue for Command",
  "Read Products for Review Command",
  "Read Part Numbers for Review Command",
  "Read Image Evidence for Review Command",
  "Prepare Review Command Request",
  "Resolve Review Command",
  "Route Review Resolution",
  "Switch Review Resolution Route",
];
for (let index = 0; index < sequence.length - 1; index += 1) {
  workflow.connections[sequence[index]] = {
    main: [[{ node: sequence[index + 1], type: "main", index: 0 }]],
  };
}
workflow.connections["Switch Review Resolution Route"] = {
  main: [
    [{ node: "Upsert Review Item", type: "main", index: 0 }],
    [{ node: "Upsert Review Decision", type: "main", index: 0 }],
    [{ node: "Upsert Resolved Product", type: "main", index: 0 }],
    [{ node: "Upsert Part Number", type: "main", index: 0 }],
    [{ node: "Upsert Observation", type: "main", index: 0 }],
    [{ node: "Upsert Image Evidence", type: "main", index: 0 }],
    [],
  ],
};
workflow.connections["Upsert Review Decision"] = {
  main: [[{ node: "Confirm Review Resolution", type: "main", index: 0 }]],
};
workflow.connections["Upsert Review Item"] = {
  main: [[{ node: "Prepare Review Notification", type: "main", index: 0 }]],
};
workflow.connections["Prepare Review Notification"] = {
  main: [[{ node: "Notify Review Needed", type: "main", index: 0 }]],
};

const output = wasArray ? [workflow] : workflow;
fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
