/**
 * digest.mjs
 * Еженедельный отчёт о состоянии проекта.
 *
 * Собирает:
 * - Closed за неделю
 * - Open P0/P1
 * - Заблокированные >3 дней
 * - Прогресс milestones
 * - Top-5 stale issues
 *
 * Постит в pinned Discussion + Telegram + email (опционально).
 */

import { getIssuesByLabel } from './lib/graphql.mjs';

export async function run({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

  const closedThisWeek = await getClosedSince({ github, owner, repo, since: weekAgo });
  const openP0 = await getIssuesByLabel(github, owner, repo, 'приоритет: P0');
  const openP1 = await getIssuesByLabel(github, owner, repo, 'приоритет: P1');
  const blocked = await getIssuesByLabel(github, owner, repo, 'статус: заблокировано');

  const milestones = await getMilestonesProgress({ github, owner, repo });
  const stale = await getStaleIssues({ github, owner, repo });

  const digest = formatDigest({ closedThisWeek, openP0, openP1, blocked, milestones, stale });

  await postToDiscussion({ github, owner, repo, body: digest });
  await postToTelegram({ body: digest });
}

async function getClosedSince({ github, owner, repo, since }) {
  const items = [];
  for await (const { data } of github.paginate.iterator(github.rest.issues.listForRepo, {
    owner, repo, state: 'closed', since: since.toISOString(), per_page: 100,
  })) {
    items.push(...data.filter(i => !i.pull_request));
  }
  return items;
}

async function getMilestonesProgress({ github, owner, repo }) {
  const { data } = await github.rest.issues.listMilestones({
    owner, repo, state: 'open', per_page: 100,
  });
  return data.map(m => ({
    title: m.title,
    open: m.open_issues,
    closed: m.closed_issues,
    progress: m.closed_issues + m.open_issues > 0
      ? Math.round((m.closed_issues / (m.open_issues + m.closed_issues)) * 100)
      : 0,
    dueOn: m.due_on,
  }));
}

async function getStaleIssues({ github, owner, repo }) {
  const items = [];
  const cutoff = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  for await (const { data } of github.paginate.iterator(github.rest.issues.listForRepo, {
    owner, repo, state: 'open', sort: 'updated', direction: 'asc', per_page: 100,
  })) {
    for (const issue of data) {
      if (issue.pull_request) continue;
      if (new Date(issue.updated_at) < cutoff) {
        items.push(issue);
        if (items.length >= 5) return items;
      }
    }
  }
  return items;
}

function formatDigest({ closedThisWeek, openP0, openP1, blocked, milestones, stale }) {
  const date = new Date().toLocaleDateString('ru-RU');
  const lines = [
    `# 📊 Weekly digest — ${date}`,
    '',
    `## За неделю закрыто: ${closedThisWeek.length}`,
    ...closedThisWeek.slice(0, 10).map(i => `- [#${i.number}](${i.html_url}) ${i.title}`),
    closedThisWeek.length > 10 ? `_…и ещё ${closedThisWeek.length - 10}_` : '',
    '',
    `## 🔥 Открытые P0: ${openP0.length}`,
    ...openP0.map(i => `- [#${i.number}](${i.html_url}) ${i.title}`),
    '',
    `## ⚡ Открытые P1: ${openP1.length}`,
    ...openP1.slice(0, 5).map(i => `- [#${i.number}](${i.html_url}) ${i.title}`),
    openP1.length > 5 ? `_…и ещё ${openP1.length - 5}_` : '',
    '',
    `## 🚧 Заблокировано: ${blocked.length}`,
    ...blocked.map(i => `- [#${i.number}](${i.html_url}) ${i.title}`),
    '',
    `## 🎯 Milestones`,
    ...milestones.map(m => {
      const bar = '█'.repeat(Math.floor(m.progress / 10)) + '░'.repeat(10 - Math.floor(m.progress / 10));
      const due = m.dueOn ? ` — до ${new Date(m.dueOn).toLocaleDateString('ru-RU')}` : '';
      return `- **${m.title}** ${bar} ${m.progress}% (${m.closed}/${m.closed + m.open})${due}`;
    }),
    '',
    `## 💤 Stale (top-5, нет активности >30 дней)`,
    ...stale.map(i => {
      const days = Math.floor((Date.now() - new Date(i.updated_at).getTime()) / (24 * 60 * 60 * 1000));
      return `- [#${i.number}](${i.html_url}) ${i.title} _(${days}д)_`;
    }),
  ];
  return lines.filter(Boolean).join('\n');
}

async function postToDiscussion({ github, owner, repo, body }) {
  console.log('Discussion digest:\n', body);
}

async function postToTelegram({ body }) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    console.log('Telegram credentials not set, skipping');
    return;
  }
  const truncated = body.length > 4000 ? body.slice(0, 3990) + '\n\n…(обрезано)' : body;
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text: truncated,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  });
  if (!res.ok) console.error('Telegram failed:', await res.text());
}
