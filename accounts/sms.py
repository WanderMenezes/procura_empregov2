import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to_number: str, message: str) -> bool:
    """Send SMS by logging to the console.

    Twilio integration has been removed from this deployment. SMS is delivered
    via the console fallback for development and diagnostics.
    """
    backend = getattr(settings, 'SMS_BACKEND', 'console')
    if backend != 'console':
        logger.warning(
            'SMS backend %s is not supported; using console fallback.',
            backend,
        )
    return _send_console(to_number, message, channel='SMS')


def send_whatsapp(
    to_number: str,
    message: str,
    *,
    content_variables: dict[str, str] | None = None,
) -> bool:
    """WhatsApp delivery is disabled."""
    logger.warning('WhatsApp delivery is disabled in this deployment.')
    return False


def _as_whatsapp_address(number: str) -> str:
    value = (number or '').strip()
    if not value:
        return value
    if value.startswith('whatsapp:'):
        return value
    return f'whatsapp:{value}'


def _send_console(to_number: str, message: str, channel: str = 'SMS') -> bool:
    # development fallback: log and return True
    logger.info('%s to %s: %s', channel, to_number, message)
    # keep a print for devs who watch console
    print(f"[{channel}] to={to_number} message={message}")
    return True
