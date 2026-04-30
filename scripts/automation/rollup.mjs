/**
 * rollup.mjs
 * Каскадный прогресс эпиков по sub-issues.
 *
 * Логика:
 * - Закрыт sub-issue → найти родителя через native API
 * - Пересчитать Progress = closed/total * 100
 * - Записать в Project поле Progress
 * - Если все sub-issues закрыты → comment в эпик "все закрыты, проверьте acceptance"
 *   + лейбл "статус: на ревью"
 * - Эпик закрыт с открытыми sub-issues → переоткрыть + warning
 */

import {
  getProjectId,
  getProjectFields,
  findProjectItem,
  setNumber,
  getSubIssues,
  getParentIssue,
  commentOnIssue,
  addLabel,
} from './lib/graphql.mjs';

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const projectNumber = process.env.PROJECT_NUMBER;
  const projectOwner = process.env.PROJECT_OWNER || owner;

  const projectId = projectNumber
    ? await getProjectId(github, projectOwner, projectNumber)
    : null;
  const fields = projectId ? await getProjectFields(github, projectId) : {};
  const progressField = fields['Progress'];

  const eventName = context.eventName;
  const action = context.payload.action;

  if (eventName === 'issues') {
    const issue = context.payload.issue;

    if (action === 'closed' && issue.labels?.some(l => l.name === 'тип: эпик')) {
      const subIssues = await getSubIssues(github, owner, repo, issue.number);
      const open = subIssues.filter(s => s.state === 'open');
      if (open.length > 0) {
        await github.rest.issues.update({ owner, repo, issue_number: issue.number, state: 'open' });
        await commentOnIssue(
          github, owner, repo, issue.number,
          `⚠️ Эпик переоткрыт автоматически.\n\nЕсть незакрытые sub-issues:\n${open.map(s => `- #${s.number} ${s.title}`).join('\n')}\n\nЗакройте их или удалите из эпика, затем закрывайте эпик снова.`
        );
        return;
      }
    }

    if (action === 'closed' || action === 'reopened') {
      const parent = await getParentIssue(github, owner, repo, issue.number);
      if (!parent) return;
      await recalculateEpicProgress({ github, owner, repo, epic: parent, projectId, progressField });
    }
  }

  if (eventName === 'pull_request' && action === 'closed' && context.payload.pull_request.merged) {
    const pr = context.payload.pull_request;
    const closingIssueRefs = (pr.body || '').match(/(?:closes|fixes|resolves|закрывает)\s+#(\d+)/gi) || [];
    for (const ref of closingIssueRefs) {
      const num = parseInt(ref.match(/#(\d+)/)[1], 10);
      const parent = await getParentIssue(github, owner, repo, num);
      if (parent) {
        await recalculateEpicProgress({ github, owner, repo, epic: parent, projectId, progressField });
      }
    }
  }
}

async function recalculateEpicProgress({ github, owner, repo, epic, projectId, progressField }) {
  const subs = await getSubIssues(github, owner, repo, epic.number);
  if (subs.length === 0) return;

  const closed = subs.filter(s => s.state === 'closed').length;
  const progress = Math.round((closed / subs.length) * 100);

  if (projectId && progressField) {
    const itemId = await findProjectItem(github, projectId, epic.node_id);
    if (itemId) {
      await setNumber(github, projectId, itemId, progressField.id, progress);
    }
  }

  if (closed === subs.length && epic.state === 'open') {
    await addLabel(github, owner, repo, epic.number, 'статус: на ревью');
    await commentOnIssue(
      github, owner, repo, epic.number,
      `✅ Все sub-issues эпика закрыты (${closed}/${subs.length}).\n\nПроверьте acceptance criteria и закройте эпик, если всё в порядке.`
    );
  }
}
