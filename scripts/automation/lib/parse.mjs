/**
 * Парсинг тела issue для извлечения структурированных полей.
 * Поддерживает два формата:
 *   1. YAML form-style: "### Эпик (родитель)\n\nEPIC-1"
 *   2. Inline-stilo: "Эпик: EPIC-1, Приоритет: P1"
 *   3. Markdown blockquote: "> Эпик: EPIC-1"
 */

const FIELD_PATTERNS = {
  epic: /(?:эпик|epic)(?:\s*\(?родитель\)?)?[:\s]*\n*\s*(EPIC-\d+|EPIC\d+|не относится)/i,
  priority: /(?:приоритет|priority)[:\s]*\n*\s*(P[0-3])/i,
  size: /(?:размер|size)[:\s]*\n*\s*\(?[^)]*\)?\s*\n*\s*(XS|S|M|L|XL)\b/i,
  component: /(?:компонент|component)[:\s]*\n*\s*(web|mobile|api|db|devops|ai|ui-kit|integrations|другое)/i,
  deadline: /(?:дедлайн|deadline)[^:]*[:\s]*\n*\s*(\d{4}-\d{2}-\d{2})/i,
  batch: /(?:батч|batch|релиз|release)[:\s]*\n*\s*(v\d+\.\d+\.\d+|без батча)/i,
  sprint: /(?:спринт|sprint)[:\s]*\n*\s*(текущий|следующий|бэклог|\d{4}-Q\d-S\d+)/i,
  stream: /(?:stream|поток|направление)[:\s]*\n*\s*(Платформа|Продукт|Инфра|AI|Команда)/i,
};

/**
 * Парсит все известные поля из body.
 */
export function parseIssueBody(body) {
  if (!body) return {};
  const result = {};
  for (const [key, pattern] of Object.entries(FIELD_PATTERNS)) {
    const match = body.match(pattern);
    if (match) result[key] = match[1].trim();
  }
  result.dependencies = parseDependencies(body);
  result.blocks = parseBlocks(body);
  return result;
}

/**
 * Парсит "Зависит от: #140, #141" или "Depends on: #140".
 * Возвращает массив номеров.
 */
export function parseDependencies(body) {
  if (!body) return [];
  const patterns = [
    /(?:зависит\s+от|depends\s+on|blocked\s+by)[:\s]*([^\n]+)/gi,
  ];
  const numbers = new Set();
  for (const pattern of patterns) {
    const matches = body.matchAll(pattern);
    for (const m of matches) {
      const refs = m[1].match(/#(\d+)/g);
      if (refs) refs.forEach(r => numbers.add(parseInt(r.slice(1), 10)));
    }
  }
  return [...numbers];
}

/**
 * Парсит "Blocks: #150" или "Блокирует: #150".
 */
export function parseBlocks(body) {
  if (!body) return [];
  const patterns = [
    /(?:блокирует|blocks)[:\s]*([^\n]+)/gi,
  ];
  const numbers = new Set();
  for (const pattern of patterns) {
    const matches = body.matchAll(pattern);
    for (const m of matches) {
      const refs = m[1].match(/#(\d+)/g);
      if (refs) refs.forEach(r => numbers.add(parseInt(r.slice(1), 10)));
    }
  }
  return [...numbers];
}

/**
 * Парсит "Closes #N" / "Fixes #N" / "Resolves #N" из тела PR.
 */
export function parseClosingKeywords(body) {
  if (!body) return [];
  const pattern = /(?:closes|fixes|resolves|закрывает|исправляет)\s+#(\d+)/gi;
  const matches = body.matchAll(pattern);
  return [...matches].map(m => parseInt(m[1], 10));
}

/**
 * Возвращает список missing required полей для валидации.
 */
export function validateRequiredFields(parsed, isEpic = false) {
  const required = isEpic
    ? ['priority']
    : ['epic', 'priority', 'size', 'component'];
  return required.filter(f => !parsed[f]);
}

/**
 * Извлекает имя эпика из title (формат "[EPIC N] ..." или "EPIC-N: ...").
 */
export function extractEpicId(title) {
  const match = title?.match(/(?:\[)?EPIC[\s-]?(\d+)(?:\])?/i);
  return match ? `EPIC-${match[1]}` : null;
}

/**
 * Конвертирует title в slug для веток.
 */
export function titleToSlug(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .slice(0, 50);
}
