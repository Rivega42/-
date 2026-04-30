#!/usr/bin/env node
/**
 * dashboard-fetch.mjs
 * Собирает снепшот данных для дашборда из GitHub GraphQL.
 * Сохраняет в tools/dashboard/data/snapshot.json.
 *
 * Запуск (CI):
 *   GITHUB_TOKEN=... PROJECT_NUMBER=... PROJECT_OWNER=... GITHUB_REPO=owner/repo node scripts/dashboard-fetch.mjs
 *
 * Запуск локально:
 *   gh auth token | xargs -I{} env GITHUB_TOKEN={} ... node scripts/dashboard-fetch.mjs
 */

import { writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const TOKEN = process.env.GITHUB_TOKEN;
const PROJECT_OWNER = process.env.PROJECT_OWNER;
const PROJECT_NUMBER = parseInt(process.env.PROJECT_NUMBER || '0', 10);
const REPO_FULL = process.env.GITHUB_REPO || process.env.GITHUB_REPOSITORY;
const OUTPUT = 'tools/dashboard/data/snapshot.json';

if (!TOKEN || !PROJECT_OWNER || !PROJECT_NUMBER || !REPO_FULL) {
  console.error('Required: GITHUB_TOKEN, PROJECT_OWNER, PROJECT_NUMBER, GITHUB_REPO');
  process.exit(1);
}

const [OWNER, REPO] = REPO_FULL.split('/');

async function gql(query, variables = {}) {
  const res = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, variables }),
  });
  if (!res.ok) throw new Error(`GraphQL ${res.status}: ${await res.text()}`);
  const data = await res.json();
  if (data.errors) throw new Error(JSON.stringify(data.errors));
  return data.data;
}

async function fetchProjectItems() {
  const items = [];
  let cursor = null;
  while (true) {
    const data = await gql(
      `query($owner: String!, $number: Int!, $cursor: String) {
        organization(login: $owner) {
          projectV2(number: $number) {
            id
            title
            url
            items(first: 100, after: $cursor) {
              pageInfo { hasNextPage endCursor }
              nodes {
                id
                content {
                  __typename
                  ... on Issue {
                    id number title state url body createdAt updatedAt closedAt
                    author { login }
                    assignees(first: 5) { nodes { login } }
                    labels(first: 20) { nodes { name color } }
                    milestone { title dueOn }
                  }
                  ... on PullRequest {
                    id number title state url
                    author { login }
                  }
                }
                fieldValues(first: 30) {
                  nodes {
                    __typename
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                      field { ... on ProjectV2SingleSelectField { name } }
                    }
                    ... on ProjectV2ItemFieldNumberValue {
                      number
                      field { ... on ProjectV2Field { name } }
                    }
                    ... on ProjectV2ItemFieldDateValue {
                      date
                      field { ... on ProjectV2Field { name } }
                    }
                    ... on ProjectV2ItemFieldTextValue {
                      text
                      field { ... on ProjectV2Field { name } }
                    }
                    ... on ProjectV2ItemFieldIterationValue {
                      title startDate duration
                      field { ... on ProjectV2IterationField { name } }
                    }
                  }
                }
              }
            }
          }
        }
        user(login: $owner) {
          projectV2(number: $number) {
            id title url
            items(first: 100, after: $cursor) {
              pageInfo { hasNextPage endCursor }
              nodes { id }
            }
          }
        }
      }`,
      { owner: PROJECT_OWNER, number: PROJECT_NUMBER, cursor }
    );

    const project = data.organization?.projectV2 || data.user?.projectV2;
    if (!project) break;

    items.push(...project.items.nodes);
    if (!project.items.pageInfo.hasNextPage) break;
    cursor = project.items.pageInfo.endCursor;
  }
  return items;
}

async function fetchSubIssues(issueNumber) {
  try {
    const res = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/issues/${issueNumber}/sub_issues`,
      { headers: { Authorization: `Bearer ${TOKEN}`, Accept: 'application/vnd.github+json' } }
    );
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

async function fetchMilestones() {
  const res = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/milestones?state=all&per_page=100`,
    { headers: { Authorization: `Bearer ${TOKEN}` } }
  );
  if (!res.ok) return [];
  return await res.json();
}

function flattenItem(raw) {
  if (!raw.content) return null;
  const fv = {};
  for (const v of raw.fieldValues.nodes || []) {
    const fname = v.field?.name;
    if (!fname) continue;
    if (v.name !== undefined) fv[fname] = v.name;
    else if (v.number !== undefined) fv[fname] = v.number;
    else if (v.date !== undefined) fv[fname] = v.date;
    else if (v.text !== undefined) fv[fname] = v.text;
    else if (v.title !== undefined) fv[fname] = { title: v.title, startDate: v.startDate, duration: v.duration };
  }
  return {
    type: raw.content.__typename,
    id: raw.content.id,
    number: raw.content.number,
    title: raw.content.title,
    state: raw.content.state,
    url: raw.content.url,
    body: raw.content.body,
    createdAt: raw.content.createdAt,
    updatedAt: raw.content.updatedAt,
    closedAt: raw.content.closedAt,
    author: raw.content.author?.login,
    assignees: raw.content.assignees?.nodes?.map(a => a.login) || [],
    labels: raw.content.labels?.nodes?.map(l => ({ name: l.name, color: l.color })) || [],
    milestone: raw.content.milestone?.title,
    fields: fv,
  };
}

async function main() {
  console.log(`📡 Fetching project ${PROJECT_OWNER}/#${PROJECT_NUMBER}...`);
  const rawItems = await fetchProjectItems();
  const items = rawItems.map(flattenItem).filter(Boolean);

  console.log(`📋 Got ${items.length} items, fetching sub-issues...`);
  const epics = items.filter(i => i.labels?.some(l => l.name === 'тип: эпик'));
  for (const epic of epics) {
    const subs = await fetchSubIssues(epic.number);
    epic.subIssues = subs.map(s => ({ number: s.number, title: s.title, state: s.state }));
    epic.progress = subs.length > 0
      ? Math.round((subs.filter(s => s.state === 'closed').length / subs.length) * 100)
      : 0;
  }

  console.log('🎯 Fetching milestones...');
  const milestones = await fetchMilestones();

  const snapshot = {
    generatedAt: new Date().toISOString(),
    repo: REPO_FULL,
    projectOwner: PROJECT_OWNER,
    projectNumber: PROJECT_NUMBER,
    items,
    epics: epics.map(e => ({
      number: e.number,
      title: e.title,
      state: e.state,
      url: e.url,
      progress: e.progress,
      subIssues: e.subIssues,
    })),
    milestones: milestones.map(m => ({
      title: m.title,
      state: m.state,
      open: m.open_issues,
      closed: m.closed_issues,
      dueOn: m.due_on,
    })),
    stats: {
      total: items.length,
      open: items.filter(i => i.state === 'OPEN' || i.state === 'open').length,
      closed: items.filter(i => i.state === 'CLOSED' || i.state === 'closed').length,
      epicsCount: epics.length,
      milestonesCount: milestones.length,
    },
  };

  await mkdir(dirname(OUTPUT), { recursive: true });
  await writeFile(OUTPUT, JSON.stringify(snapshot, null, 2));
  console.log(`✅ Snapshot saved to ${OUTPUT}`);
  console.log(`   Total items: ${snapshot.stats.total}`);
  console.log(`   Epics: ${snapshot.stats.epicsCount}`);
  console.log(`   Milestones: ${snapshot.stats.milestonesCount}`);
}

main().catch(e => {
  console.error('❌', e.message);
  process.exit(1);
});
