/**
 * Conditional Sentry bootstrap for the Node backend.
 *
 * We deliberately do NOT add @sentry/node to package.json yet; it is wired up
 * via a dynamic require inside a try/catch so the server continues to work in
 * environments where Sentry is neither installed nor desired. Install the SDK
 * explicitly when you actually want error reporting in production.
 */
export function initSentry(): void {
  if (!process.env.SENTRY_DSN) return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const Sentry = require('@sentry/node');
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
      tracesSampleRate: 0.1,
      environment: process.env.BOOKCABINET_ENV || process.env.NODE_ENV || 'production',
    });
  } catch {
    // SDK not installed — silently ignore so the server still starts.
  }
}
