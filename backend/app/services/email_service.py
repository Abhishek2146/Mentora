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
        self.username = settings.SMTP_EMAIL or settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
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
            logger.info(f"Sending email to {to_email} via {self.host}:{self.port}")
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
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        frontend_url: str
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            frontend_url: Frontend URL for reset link

        Returns:
            True if email sent successfully, False otherwise
        """
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        subject = f"Reset your {self.app_name} password"

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
                <p style="color: #475569; font-size: 16px;">You requested to reset your password. Click the button below to create a new password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">Reset Password</a>
                </div>
                <p style="color: #64748b; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <p style="color: #6366f1; font-size: 14px; word-break: break-all; background: #f1f5f9; padding: 12px; border-radius: 6px;">{reset_link}</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    This link will expire in 1 hour. If you didn't request this, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Reset your {self.app_name} password

        You requested to reset your password. Click the link below to create a new password:

        {reset_link}

        This link will expire in 1 hour. If you didn't request this, please ignore this email.
        """

        return await self.send_email(to_email, subject, html_content, text_content)


email_service = EmailService()