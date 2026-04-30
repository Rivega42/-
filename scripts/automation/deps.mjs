/**
 * deps.mjs
 * Резолв блокирующих зависимостей.
 *
 * Логика:
 * - При open/edited issue парсит body на "Зависит от: #N" / "Blocks: #N"
 * - Для каждой зависимости пишет в Project поле Blocked by
 * - При закрытии issue #N — комментирует во все issues, которые зависели от него
 * - Если есть незакрытые блокеры → лейбл "статус: заблокировано"
 */

import {
  getProjectId,
  getProjectFields,
  findProjectItem,
  setText,
  commentOnIssue,
  addLabel,
  removeLabel,
} from './lib/graphql.mjs';
import { parseDependencies, parseBlocks } from './lib/parse.mjs';

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const projectNumber = process.env.PROJECT_NUMBER;
  const projectOwner = process.env.PROJECT_OWNER || owner;

  const projectId = projectNumber
    ? await getProjectId(github, projectOwner, projectNumber)
    : null;
  const fields = projectId ? await getProjectFields(github, projectId) : {};
  const blockedByField = fields['Blocked by'];

  const eventName = context.eventName;
  const action = context.payload.action;
  if (eventName !== 'issues') return;

  const issue = context.payload.issue;

  if (action === 'opened' || action === 'edited') {
    const deps = parseDependencies(issue.body);
    const blocks = parseBlocks(issue.body);

    if (projectId && blockedByField) {
      const itemId = await findProjectItem(github, projectId, issue.node_id);
      if (itemId && deps.length > 0) {
        await setText(github, projectId, itemId, blockedByField.id, deps.map(d => `#${d}`).join(', '));
      }
    }

    let hasOpenBlockers = false;
    for (const depNum of deps) {
      try {
        const { data: dep } = await github.rest.issues.get({ owner, repo, issue_number: depNum });
        if (dep.state === 'open') {
          hasOpenBlockers = true;
        }
      } catch (e) {
        await commentOnIssue(
          github, owner, repo, issue.number,
          `⚠️ Зависимость #${depNum} не найдена.`
        );
      }
    }

    if (hasOpenBlockers) {
      await addLabel(github, owner, repo, issue.number, 'статус: заблокировано');
    } else if (deps.length > 0) {
      await removeLabel(github, owner, repo, issue.number, 'статус: заблокировано');
    }

    for (const blockedNum of blocks) {
      try {
        await commentOnIssue(
          github, owner, repo, blockedNum,
          `🔗 Зависимость от #${issue.number}: «${issue.title}». Эта задача блокирует данный issue.`
        );
      } catch (e) { /* skip */ }
    }
  }

  if (action === 'closed') {
    const dependents = await findDependents({ github, owner, repo, closedIssueNumber: issue.number });
    for (const dep of dependents) {
      const remaining = parseDependencies(dep.body).filter(n => n !== issue.number);
      if (remaining.length === 0) {
        await removeLabel(github, owner, repo, dep.number, 'статус: заблокировано');
        await commentOnIssue(
          github, owner, repo, dep.number,
          `✅ Зависимость #${issue.number} закрыта. Все блокеры разрешены, можно начинать работу.`
        );
      } else {
        await commentOnIssue(
          github, owner, repo, dep.number,
          `🔓 Зависимость #${issue.number} закрыта. Осталось ${remaining.length} блокеров: ${remaining.map(n => `#${n}`).join(', ')}.`
        );
      }
    }
  }
}

async function findDependents({ github, owner, repo, closedIssueNumber }) {
  const dependents = [];
  for await (const { data } of github.paginate.iterator(github.rest.issues.listForRepo, {
    owner, repo, state: 'open', per_page: 100,
  })) {
    for (const issue of data) {
      if (issue.pull_request) continue;
      const deps = parseDependencies(issue.body);
      if (deps.includes(closedIssueNumber)) {
        dependents.push(issue);
      }
    }
  }
  return dependents;
}
