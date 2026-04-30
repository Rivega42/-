/**
 * validate.mjs
 * Валидация issue на полноту обязательных полей.
 *
 * Логика:
 * - При opened/edited парсит body
 * - Проверяет наличие: epic, priority, size, component (для не-эпиков)
 * - Если чего-то нет → comment с чек-листом + лейбл "статус: нужна инфа"
 * - Если всё заполнено → снимает лейбл "статус: нужна инфа"
 */

import { addLabel, removeLabel, commentOnIssue } from './lib/graphql.mjs';
import { parseIssueBody, validateRequiredFields } from './lib/parse.mjs';

const REQUIRED_LABEL_PREFIXES = {
  type: 'тип:',
  priority: 'приоритет:',
};

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const eventName = context.eventName;
  const action = context.payload.action;
  if (eventName !== 'issues' || (action !== 'opened' && action !== 'edited')) return;

  const issue = context.payload.issue;
  const labels = issue.labels?.map(l => l.name) || [];
  const isEpic = labels.includes('тип: эпик');
  const isVikaTask = issue.title.startsWith('[devops:vika]') || labels.includes('для: вики');

  if (isVikaTask) {
    return;
  }

  const parsed = parseIssueBody(issue.body);
  const missingBodyFields = validateRequiredFields(parsed, isEpic);
  const missingLabels = [];

  if (!labels.some(l => l.startsWith(REQUIRED_LABEL_PREFIXES.type))) {
    missingLabels.push('тип: ...');
  }
  if (!labels.some(l => l.startsWith(REQUIRED_LABEL_PREFIXES.priority))) {
    missingLabels.push('приоритет: P0/P1/P2/P3');
  }

  if (missingBodyFields.length === 0 && missingLabels.length === 0) {
    await removeLabel(github, owner, repo, issue.number, 'статус: нужна инфа');
    return;
  }

  const fieldNames = {
    epic: 'Эпик (родитель)',
    priority: 'Приоритет (P0/P1/P2/P3)',
    size: 'Размер (XS/S/M/L/XL)',
    component: 'Компонент',
  };

  const checklist = [
    ...missingBodyFields.map(f => `- [ ] Заполнить поле «${fieldNames[f] || f}» в body`),
    ...missingLabels.map(l => `- [ ] Добавить лейбл \`${l}\``),
  ];

  const body = `⚠️ В issue не хватает обязательных полей. Заполните, чтобы можно было перевести в работу:\n\n${checklist.join('\n')}\n\nКогда исправите — лейбл \`статус: нужна инфа\` снимется автоматически.\n\nПодробности в [docs/ai/AUTOMATION.md](../blob/main/docs/ai/AUTOMATION.md).`;

  await addLabel(github, owner, repo, issue.number, 'статус: нужна инфа');

  const { data: comments } = await github.rest.issues.listComments({
    owner, repo, issue_number: issue.number, per_page: 100,
  });
  const alreadyCommented = comments.some(c => c.user?.type === 'Bot' && c.body?.includes('не хватает обязательных полей'));
  if (!alreadyCommented) {
    await commentOnIssue(github, owner, repo, issue.number, body);
  }
}
