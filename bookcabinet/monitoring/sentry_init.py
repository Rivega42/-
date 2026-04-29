"""Sentry error tracking — initialized only if SENTRY_DSN env var is set."""
import logging
import os


def init_sentry() -> bool:
    """Initialize Sentry if SENTRY_DSN is set.

    Returns True when Sentry is wired up, False otherwise (missing DSN or
    the SDK is not installed). Safe to call multiple times.
    """
    dsn = os.environ.get('SENTRY_DSN')
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            environment=os.environ.get('BOOKCABINET_ENV', 'production'),
            integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
        )
        return True
    except ImportError:
        print("Sentry SDK not installed")
        return False
