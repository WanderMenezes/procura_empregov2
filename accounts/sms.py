import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to_number: str, message: str) -> bool:
    """Send SMS using configured backend.

    - If `SMS_BACKEND` == 'twilio' and Twilio credentials present, try to send via Twilio.
    - Otherwise, fallback to console logging (development-friendly).

    Returns True on success, False on failure.
    """
    backend = getattr(settings, 'SMS_BACKEND', 'console')

    if backend == 'twilio':
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')
        if not (account_sid and auth_token and from_number):
            logger.warning('Twilio selected but credentials missing; falling back to console')
            backend = 'console'

    if backend == 'twilio':
        try:
            from twilio.rest import Client
        except Exception:
            logger.exception('Twilio library not installed; falling back to console')
            return _send_console(to_number, message)

        try:
            client = Client(account_sid, auth_token)
            client.messages.create(body=message, from_=from_number, to=to_number)
            logger.info('Sent SMS via Twilio to %s', to_number)
            return True
        except Exception:
            logger.exception('Failed to send SMS via Twilio')
            return False

    return _send_console(to_number, message, channel='SMS')


def send_whatsapp(
    to_number: str,
    message: str,
    *,
    content_variables: dict[str, str] | None = None,
) -> bool:
    """Send WhatsApp using configured backend."""
    backend = getattr(
        settings,
        'WHATSAPP_BACKEND',
        getattr(settings, 'SMS_BACKEND', 'console'),
    )

    if backend != 'twilio':
        logger.warning(
            'WhatsApp backend is set to %s; real delivery is unavailable.',
            backend,
        )
        return False

    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = (
        getattr(settings, 'TWILIO_WHATSAPP_FROM_NUMBER', '')
        or getattr(settings, 'TWILIO_FROM_NUMBER', '')
    )
    content_sid = getattr(settings, 'TWILIO_WHATSAPP_CONTENT_SID', '').strip()
    if not (account_sid and auth_token and from_number):
        logger.warning('Twilio WhatsApp selected but credentials are incomplete.')
        return False

    try:
        from twilio.rest import Client
    except Exception:
        logger.exception('Twilio library not installed; WhatsApp delivery is unavailable.')
        return False

    try:
        client = Client(account_sid, auth_token)
        payload = {
            'from_': _as_whatsapp_address(from_number),
            'to': _as_whatsapp_address(to_number),
        }
        if content_sid:
            payload['content_sid'] = content_sid
            if content_variables:
                payload['content_variables'] = json.dumps(content_variables)
        else:
            payload['body'] = message
        client.messages.create(**payload)
        logger.info('Sent WhatsApp via Twilio to %s', to_number)
        return True
    except Exception:
        logger.exception('Failed to send WhatsApp via Twilio')
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
