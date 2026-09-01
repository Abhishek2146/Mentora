"""
Email Service for sending transactional emails.
"""
import aiosmtplib
from email.message import EmailMessage
from typing import Optional
import logging

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        # Gmail app passwords are shown as "xxxx xxxx xxxx xxxx" — spaces must be stripped.
        # Also strip surrounding whitespace from env-loaded values.
        raw_user = (settings.SMTP_EMAIL or settings.SMTP_USER or "").strip()
        raw_pass = (settings.SMTP_PASSWORD or "").strip().replace(" ", "")
        self.username = raw_user
        self.password = raw_pass
        self.from_email = self.username
        self.app_name = settings.APP_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured, skipping email send")
            return False

        message = EmailMessage()
        message["From"] = f"{self.app_name} <{self.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        if text_content:
            message.set_content(text_content)
            message.add_alternative(html_content, subtype="html")
        else:
            message.set_content(html_content, subtype="html")

        try:
            logger.info(f"Sending email to {to_email} via {self.host}:{self.port} as {self.username}")
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                start_tls=True,
                username=self.username,
                password=self.password,
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            # Specific hint for Gmail 535
            err_str = str(e)
            if "535" in err_str or "BadCredentials" in err_str or "Username and Password not accepted" in err_str:
                logger.error(
                    f"Failed to send email to {to_email}: {e} — "
                    "Gmail 535: verify 2-Step Verification is ON, App Password is 16 chars "
                    "(no spaces), and SMTP_USER/EMAIL matches the Google account that generated it. "
                    "Regenerate at https://myaccount.google.com/apppasswords"
                )
            else:
                logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        frontend_url: str,
        otp: str | None = None,
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            frontend_url: Frontend URL for reset link
            otp: 6-digit OTP (optional, shown alongside link)

        Returns:
            True if email sent successfully, False otherwise
        """
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        subject = f"Reset your {self.app_name} password"

        otp_block_html = ""
        otp_block_text = ""
        if otp:
            otp_block_html = f"""
                <div style="margin: 24px 0; padding: 16px; background: #fff; border: 2px dashed #6366f1; border-radius: 8px; text-align: center;">
                    <p style="color: #475569; font-size: 14px; margin: 0 0 8px;">Or use this 6-digit OTP (valid for 10 minutes):</p>
                    <p style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #6366f1; margin: 0;">{otp}</p>
                    <p style="color: #64748b; font-size: 12px; margin: 8px 0 0;">Enter it on the “Verify OTP” page to reset your password.</p>
                </div>
            """
            otp_block_text = f"""
Your OTP (valid 10 min): {otp}
Go to {frontend_url}/verify-otp?email={to_email} to enter it.
"""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Mentora</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0;">Your AI Learning Companion</p>
            </div>
            <div style="background: #f8fafc; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0; border-top: none;">
                <h2 style="color: #1e293b; margin-top: 0;">Reset Your Password</h2>
                <p style="color: #475569; font-size: 16px;">You requested to reset your password. Choose one of the options below:</p>
                <p style="color: #475569; font-size: 14px; font-weight: 600; margin-top: 16px;">Option 1 — Reset link (1 hour):</p>
                <div style="text-align: center; margin: 16px 0;">
                    <a href="{reset_link}" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">Reset Password</a>
                </div>
                <p style="color: #64748b; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #6366f1; font-size: 14px; word-break: break-all; background: #f1f5f9; padding: 12px; border-radius: 6px;">{reset_link}</p>
                {otp_block_html}
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    Both the link (1 hour) and OTP (10 minutes) expire soon. If you didn't request this, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Reset your {self.app_name} password

        Option 1 — Reset link (1 hour):
        {reset_link}
        {otp_block_text}
        If you didn't request this, please ignore this email.
        """

        return await self.send_email(to_email, subject, html_content, text_content)


email_service = EmailService()