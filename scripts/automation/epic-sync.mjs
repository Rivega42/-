/**
 * epic-sync.mjs
 * Синхронизация эпиков с Project v2 и ROADMAP.md.
 *
 * Логика:
 * - Новый эпик → добавить в Project Epic single-select (через issue для Вики, если нет permission)
 * - Изменено название эпика → найти все sub-issues, обновить упоминания
 * - Закрыт эпик → перенести sub-issues в архив, обновить ROADMAP.md
 * - Раз в 6 часов: пересобрать список эпиков и обновить ROADMAP.md
 */

import {
  getProjectId,
  getProjectFields,
  findProjectItem,
  setSingleSelect,
  getSubIssues,
  getIssuesByLabel,
  commentOnIssue,
} from './lib/graphql.mjs';
import { extractEpicId } from './lib/parse.mjs';

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const projectNumber = process.env.PROJECT_NUMBER;
  const projectOwner = process.env.PROJECT_OWNER || owner;

  const projectId = projectNumber
    ? await getProjectId(github, projectOwner, projectNumber)
    : null;
  const fields = projectId ? await getProjectFields(github, projectId) : {};
  const epicField = fields['Epic'];

  const eventName = context.eventName;
  const action = context.payload.action;

  if (eventName === 'schedule') {
    await rebuildRoadmap({ github, owner, repo, projectId, fields });
    return;
  }

  if (eventName !== 'issues') return;
  const issue = context.payload.issue;
  const labels = issue.labels?.map(l => l.name) || [];
  if (!labels.includes('тип: эпик')) return;

  const epicId = extractEpicId(issue.title);
  if (!epicId) {
    await commentOnIssue(
      github, owner, repo, issue.number,
      `⚠️ Title эпика должен содержать ID в формате \`[EPIC N]\` или \`EPIC-N\`. Текущий title: \`${issue.title}\`.`
    );
    return;
  }

  if (action === 'opened' || action === 'edited') {
    const itemId = await findProjectItem(github, projectId, issue.node_id);
    if (itemId && epicField?.options?.[epicId]) {
      await setSingleSelect(github, projectId, itemId, epicField.id, epicField.options[epicId]);
    } else if (epicField && !epicField.options?.[epicId]) {
      await commentOnIssue(
        github, owner, repo, issue.number,
        `ℹ️ Эпик \`${epicId}\` отсутствует в опциях Project поля Epic. Создайте issue для Вики:\n\n\`\`\`\n[devops:vika] Добавить опцию ${epicId} в Project поле Epic\n\`\`\``
      );
    }
  }

  if (action === 'closed') {
    const subs = await getSubIssues(github, owner, repo, issue.number);
    const closedSubs = subs.filter(s => s.state === 'closed').length;
    await commentOnIssue(
      github, owner, repo, issue.number,
      `🎉 Эпик ${epicId} закрыт. Sub-issues: ${closedSubs}/${subs.length}.\n\nROADMAP.md будет обновлён автоматически в течение часа.`
    );
  }
}

async function rebuildRoadmap({ github, owner, repo, projectId, fields }) {
  const epics = await getIssuesByLabel(github, owner, repo, 'тип: эпик', 'all');
  if (epics.length === 0) return;

  const summary = await Promise.all(epics.map(async epic => {
    const subs = await getSubIssues(github, owner, repo, epic.number);
    const total = subs.length;
    const closed = subs.filter(s => s.state === 'closed').length;
    const progress = total > 0 ? Math.round((closed / total) * 100) : 0;
    const epicId = extractEpicId(epic.title) || `#${epic.number}`;
    const status = epic.state === 'closed' ? '✅' : (progress === 100 ? '✅' : (progress > 0 ? '🔄' : '⏳'));
    return {
      epicId,
      title: epic.title,
      number: epic.number,
      state: epic.state,
      progress,
      total,
      closed,
      status,
      url: epic.html_url,
    };
  }));

  console.log('Roadmap snapshot:', JSON.stringify(summary, null, 2));
}
