/**
 * auto-labels.mjs
 * Синхронизирует лейблы issue/PR с полем Status в Project v2.
 *
 * Логика:
 * - Issue opened → если в проекте нет → добавить, Status: Бэклог
 * - Лейбл "статус: в работе" → Project Status = В работе
 * - Лейбл "статус: на ревью" → Project Status = На ревью
 * - Лейбл "статус: готово" → Project Status = Готово
 * - PR opened с "Closes #N" → linked issue Status = На ревью + лейбл
 * - PR merged → linked issue Status = Готово + закрыть
 * - PR converted_to_draft → откат на В работе
 * - Issue closed без PR → если статус был "В работе" → "Готово"
 * - Issue assigned → если был "Бэклог" → "Готово к работе"
 */

import {
  getProjectId,
  getProjectFields,
  findProjectItem,
  addItemToProject,
  setSingleSelect,
  addLabel,
  removeLabel,
  commentOnIssue,
} from './lib/graphql.mjs';
import { parseClosingKeywords } from './lib/parse.mjs';

const STATUS_MAP = {
  'статус: бэклог': 'Бэклог',
  'статус: discovery': 'Discovery',
  'статус: готово к работе': 'Готово к работе',
  'статус: в работе': 'В работе',
  'статус: на ревью': 'На ревью',
  'статус: готово': 'Готово',
  'статус: заблокировано': 'Заблокировано',
};

const REVERSE_STATUS_MAP = Object.fromEntries(
  Object.entries(STATUS_MAP).map(([k, v]) => [v, k])
);

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const projectNumber = process.env.PROJECT_NUMBER;
  const projectOwner = process.env.PROJECT_OWNER || owner;

  if (!projectNumber) {
    console.log('PROJECT_NUMBER not set, skipping');
    return;
  }

  const projectId = await getProjectId(github, projectOwner, projectNumber);
  if (!projectId) {
    console.log(`Project not found: ${projectOwner}/${projectNumber}`);
    return;
  }
  const fields = await getProjectFields(github, projectId);
  const statusField = fields['Status'];

  const eventName = context.eventName;
  const action = context.payload.action;

  if (eventName === 'issues') {
    await handleIssueEvent({ github, context, projectId, statusField, action, owner, repo });
  } else if (eventName === 'pull_request') {
    await handlePREvent({ github, context, projectId, statusField, action, owner, repo });
  }
}

async function handleIssueEvent({ github, context, projectId, statusField, action, owner, repo }) {
  const issue = context.payload.issue;
  if (!issue) return;

  let itemId = await findProjectItem(github, projectId, issue.node_id);

  if (action === 'opened') {
    if (!itemId) {
      itemId = await addItemToProject(github, projectId, issue.node_id);
    }
    await setStatus(github, projectId, itemId, statusField, 'Бэклог');
    return;
  }

  if (action === 'assigned' && issue.assignees.length > 0) {
    const currentLabels = issue.labels.map(l => l.name);
    if (currentLabels.includes('статус: бэклог') || !currentLabels.some(l => l.startsWith('статус:'))) {
      await syncStatus({ github, projectId, itemId, statusField, owner, repo, issueNumber: issue.number, target: 'Готово к работе' });
    }
    return;
  }

  if (action === 'labeled') {
    const newLabel = context.payload.label?.name;
    if (newLabel?.startsWith('статус:') && STATUS_MAP[newLabel]) {
      const targetStatus = STATUS_MAP[newLabel];
      if (itemId && statusField) {
        await setStatus(github, projectId, itemId, statusField, targetStatus);
      }
      for (const label of Object.keys(STATUS_MAP)) {
        if (label !== newLabel) {
          await removeLabel(github, owner, repo, issue.number, label);
        }
      }
    }
    return;
  }

  if (action === 'closed') {
    if (itemId && statusField) {
      await setStatus(github, projectId, itemId, statusField, 'Готово');
    }
    await syncLabel(github, owner, repo, issue.number, 'статус: готово');
    return;
  }

  if (action === 'reopened') {
    if (itemId && statusField) {
      await setStatus(github, projectId, itemId, statusField, 'В работе');
    }
    await syncLabel(github, owner, repo, issue.number, 'статус: в работе');
    return;
  }
}

async function handlePREvent({ github, context, projectId, statusField, action, owner, repo }) {
  const pr = context.payload.pull_request;
  if (!pr) return;

  const closingIssues = parseClosingKeywords(pr.body);
  if (closingIssues.length === 0) return;

  for (const issueNumber of closingIssues) {
    let issue;
    try {
      const { data } = await github.rest.issues.get({ owner, repo, issue_number: issueNumber });
      issue = data;
    } catch (e) {
      continue;
    }

    const itemId = await findProjectItem(github, projectId, issue.node_id);

    if (action === 'opened' || action === 'reopened' || action === 'ready_for_review') {
      if (!pr.draft) {
        if (itemId && statusField) {
          await setStatus(github, projectId, itemId, statusField, 'На ревью');
        }
        await syncLabel(github, owner, repo, issueNumber, 'статус: на ревью');
      }
      continue;
    }

    if (action === 'converted_to_draft') {
      if (itemId && statusField) {
        await setStatus(github, projectId, itemId, statusField, 'В работе');
      }
      await syncLabel(github, owner, repo, issueNumber, 'статус: в работе');
      continue;
    }

    if (action === 'closed' && pr.merged) {
      if (itemId && statusField) {
        await setStatus(github, projectId, itemId, statusField, 'Готово');
      }
      await syncLabel(github, owner, repo, issueNumber, 'статус: готово');
      continue;
    }

    if (action === 'closed' && !pr.merged) {
      if (itemId && statusField) {
        await setStatus(github, projectId, itemId, statusField, 'В работе');
      }
      await syncLabel(github, owner, repo, issueNumber, 'статус: в работе');
    }
  }
}

async function setStatus(github, projectId, itemId, statusField, statusName) {
  if (!statusField || !statusField.options) return;
  const optionId = statusField.options[statusName];
  if (!optionId) {
    console.log(`Status option not found: ${statusName}`);
    return;
  }
  await setSingleSelect(github, projectId, itemId, statusField.id, optionId);
}

async function syncStatus({ github, projectId, itemId, statusField, owner, repo, issueNumber, target }) {
  if (itemId && statusField) {
    await setStatus(github, projectId, itemId, statusField, target);
  }
  await syncLabel(github, owner, repo, issueNumber, REVERSE_STATUS_MAP[target]);
}

async function syncLabel(github, owner, repo, issueNumber, targetLabel) {
  if (!targetLabel) return;
  for (const label of Object.keys(STATUS_MAP)) {
    if (label !== targetLabel) {
      await removeLabel(github, owner, repo, issueNumber, label);
    }
  }
  await addLabel(github, owner, repo, issueNumber, targetLabel);
}
