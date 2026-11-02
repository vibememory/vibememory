"""Minimal account-security email delivery.

This module is deliberately narrow: it only sends Vibe Memory verification and password-reset
messages. It is not a general notification or external-action proxy, and it never logs message
bodies, tokens, credentials, or recipients.
"""

import smtplib
import ssl
from email.message import EmailMessage


class RecoveryMailDelivery:
    def __init__(self, settings):
        self.host = settings.smtp_host.strip()
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.sender = settings.smtp_from.strip()
        self.starttls = settings.smtp_starttls
        self.ssl = settings.smtp_ssl
        self.timeout = settings.smtp_timeout_seconds

    @property
    def available(self):
        return bool(self.host and self.sender)

    def send(self, recipient, subject, body):
        if not self.available:
            raise RuntimeError("account recovery email is not configured")
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        context = ssl.create_default_context()
        connection = (
            smtplib.SMTP_SSL(
                self.host, self.port, timeout=self.timeout, context=context
            )
            if self.ssl
            else smtplib.SMTP(self.host, self.port, timeout=self.timeout)
        )
        with connection as smtp:
            if self.starttls:
                smtp.starttls(context=context)
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)

