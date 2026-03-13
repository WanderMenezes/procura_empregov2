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

    return _send_console(to_number, message)


def _send_console(to_number: str, message: str) -> bool:
    # development fallback: log and return True
    logger.info('SMS to %s: %s', to_number, message)
    # keep a print for devs who watch console
    print(f"[SMS] to={to_number} message={message}")
    return True
