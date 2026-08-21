"""
Email Service Module for Zenix AI.
Provides email sending capabilities via SMTP.
Supports: Gmail, Outlook, Yahoo, and custom SMTP servers.
"""

import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message structure."""
    to: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    from_name: Optional[str] = None


@dataclass
class EmailResult:
    """Result of email sending."""
    success: bool
    message_id: Optional[str]
    error: Optional[str] = None


class EmailService:
    """
    Email sending service via SMTP.
    Supports multiple email providers.
    """

    # SMTP configurations for common providers
    SMTP_CONFIGS = {
        "gmail": {
            "host": "smtp.gmail.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        },
        "outlook": {
            "host": "smtp-mail.outlook.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        },
        "yahoo": {
            "host": "smtp.mail.yahoo.com",
            "port": 587,
            "use_tls": True,
            "use_ssl": False,
        },
        "custom": {
            "host": os.environ.get("SMTP_HOST", ""),
            "port": int(os.environ.get("SMTP_PORT", "587")),
            "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
            "use_ssl": os.environ.get("SMTP_USE_SSL", "false").lower() == "true",
        },
    }

    def __init__(self, provider: str = "gmail"):
        """
        Initialize email service.

        Args:
            provider: Email provider ("gmail", "outlook", "yahoo", "custom")
        """
        self.provider = provider
        self.config = self.SMTP_CONFIGS.get(provider, self.SMTP_CONFIGS["custom"])

        # Get credentials from environment
        self.email = os.environ.get("EMAIL_ADDRESS", "")
        self.password = os.environ.get("EMAIL_PASSWORD", "")

        if not self.email or not self.password:
            logger.warning(f"Email credentials not configured for {provider}")

    def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send an email.

        Args:
            message: EmailMessage object

        Returns:
            EmailResult with success status
        """
        if not self.email or not self.password:
            return EmailResult(
                success=False,
                message_id=None,
                error="Email credentials not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables."
            )

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{message.from_name or 'Zenix AI'} <{self.email}>"
            msg['To'] = ', '.join(message.to)
            msg['Subject'] = message.subject

            if message.cc:
                msg['Cc'] = ', '.join(message.cc)

            # Add plain text body
            msg.attach(MIMEText(message.body, 'plain', 'utf-8'))

            # Add HTML body if provided
            if message.html_body:
                msg.attach(MIMEText(message.html_body, 'html', 'utf-8'))

            # Add attachments
            if message.attachments:
                for file_path in message.attachments:
                    if os.path.exists(file_path):
                        self._attach_file(msg, file_path)

            # Get all recipients
            recipients = message.to.copy()
            if message.cc:
                recipients.extend(message.cc)
            if message.bcc:
                recipients.extend(message.bcc)

            # Send email
            with smtplib.SMTP(self.config['host'], self.config['port']) as server:
                if self.config['use_tls']:
                    server.starttls()
                server.login(self.email, self.password)
                server.sendmail(self.email, recipients, msg.as_string())

            logger.info(f"Email sent to {', '.join(message.to)}")
            return EmailResult(
                success=True,
                message_id=f"sent_{hash(message.subject)}",
            )

        except smtplib.SMTPAuthenticationError:
            return EmailResult(
                success=False,
                message_id=None,
                error="Authentication failed. Check your email and password. For Gmail, use App Password."
            )
        except smtplib.SMTPException as e:
            return EmailResult(
                success=False,
                message_id=None,
                error=f"SMTP error: {str(e)}"
            )
        except Exception as e:
            return EmailResult(
                success=False,
                message_id=None,
                error=f"Email sending failed: {str(e)}"
            )

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach a file to the email."""
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        filename = os.path.basename(file_path)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)

    def send_text_email(self, to: List[str], subject: str, body: str,
                       from_name: str = None) -> EmailResult:
        """Convenience method to send a simple text email."""
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            from_name=from_name,
        )
        return self.send_email(message)

    def send_html_email(self, to: List[str], subject: str, body: str,
                       html_body: str = None, from_name: str = None) -> EmailResult:
        """Convenience method to send an HTML email."""
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html_body=html_body or f"<html><body>{body}</body></html>",
            from_name=from_name,
        )
        return self.send_email(message)

    def verify_connection(self) -> bool:
        """Verify SMTP connection and credentials."""
        if not self.email or not self.password:
            return False

        try:
            with smtplib.SMTP(self.config['host'], self.config['port']) as server:
                if self.config['use_tls']:
                    server.starttls()
                server.login(self.email, self.password)
            return True
        except Exception:
            return False


class EmailTemplates:
    """Pre-defined email templates."""

    @staticmethod
    def job_application(name: str, position: str, company: str) -> Dict[str, str]:
        """Job application email template."""
        subject = f"Application for {position} at {company}"
        body = f"""Dear Hiring Manager,

I am writing to express my interest in the {position} position at {company}.

I believe my skills and experience make me a strong candidate for this role. I have attached my resume for your review.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Best regards,
{name}"""
        return {"subject": subject, "body": body}

    @staticmethod
    def complaint(name: str, issue: str, details: str) -> Dict[str, str]:
        """Complaint email template."""
        subject = f"Complaint: {issue}"
        body = f"""Dear Sir/Madam,

I am writing to bring to your attention an issue regarding {issue}.

{details}

I request you to look into this matter and take appropriate action at the earliest.

Thank you,
{name}"""
        return {"subject": subject, "body": body}

    @staticmethod
    def follow_up(name: str, context: str) -> Dict[str, str]:
        """Follow-up email template."""
        subject = "Follow-up"
        body = f"""Dear Sir/Madam,

I hope this email finds you well.

I am writing to follow up on {context}.

Please let me know if you need any additional information from my end.

Thank you for your time.

Best regards,
{name}"""
        return {"subject": subject, "body": body}


# Singleton instances
_email_service = None
_email_templates = None


def get_email_service(provider: str = "gmail") -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService(provider)
    return _email_service


def get_email_templates() -> EmailTemplates:
    """Get or create the email templates singleton."""
    global _email_templates
    if _email_templates is None:
        _email_templates = EmailTemplates()
    return _email_templates
