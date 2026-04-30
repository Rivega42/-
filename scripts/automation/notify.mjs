/**
 * notify.mjs
 * Уведомления в Telegram.
 *
 * Триггеры:
 * - issues.opened/labeled с приоритет: P0 → срочное уведомление
 * - PR висит на ревью >24ч → reminder
 * - Эпик закрыт → digest-уведомление
 */

export async function run({ github, context }) {
  const eventName = context.eventName;
  const action = context.payload.action;

  if (eventName === 'issues') {
    if (action === 'opened' || action === 'labeled') {
      const issue = context.payload.issue;
      const labels = issue.labels?.map(l => l.name) || [];

      if (labels.includes('приоритет: P0')) {
        await sendTelegram(`🚨 *P0 issue открыт*\n\n[#${issue.number}](${issue.html_url}) ${issue.title}\n\nАвтор: @${issue.user.login}`);
      }

      if (action === 'opened' && labels.includes('тип: эпик')) {
        await sendTelegram(`🎯 *Новый эпик*\n\n[#${issue.number}](${issue.html_url}) ${issue.title}`);
      }
    }

    if (action === 'closed' && context.payload.issue.labels?.some(l => l.name === 'тип: эпик')) {
      const issue = context.payload.issue;
      await sendTelegram(`🎉 *Эпик завершён*\n\n[#${issue.number}](${issue.html_url}) ${issue.title}\n\nProgress: 100%`);
    }
  }

  if (eventName === 'pull_request_review' && action === 'submitted') {
    const review = context.payload.review;
    const pr = context.payload.pull_request;
    if (review.state === 'changes_requested') {
      await sendTelegram(`🔄 *Запрошены изменения в PR*\n\n[#${pr.number}](${pr.html_url}) ${pr.title}\n\nРевьюер: @${review.user.login}`);
    }
  }

  if (eventName === 'schedule') {
    await checkStalePRs({ github, context });
  }
}

async function checkStalePRs({ github, context }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);

  for await (const { data } of github.paginate.iterator(github.rest.pulls.list, {
    owner, repo, state: 'open', per_page: 100,
  })) {
    for (const pr of data) {
      if (pr.draft) continue;
      if (new Date(pr.updated_at) > cutoff) continue;

      const { data: reviews } = await github.rest.pulls.listReviews({
        owner, repo, pull_number: pr.number,
      });

      const lastActivity = reviews.length > 0
        ? new Date(reviews[reviews.length - 1].submitted_at)
        : new Date(pr.created_at);

      if (lastActivity < cutoff) {
        const hours = Math.floor((Date.now() - lastActivity.getTime()) / (60 * 60 * 1000));
        await sendTelegram(`⏰ *PR висит на ревью ${hours}ч*\n\n[#${pr.number}](${pr.html_url}) ${pr.title}\n\nАвтор: @${pr.user.login}`);
      }
    }
  }
}

async function sendTelegram(text) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    console.log('Telegram credentials not set, skipping');
    console.log('Would send:', text);
    return;
  }
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  });
  if (!res.ok) console.error('Telegram failed:', await res.text());
}
