import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from config import settings

logger = logging.getLogger("email_service")

class EmailService:
    @classmethod
    def send_html_email(
        cls, 
        to_email: str, 
        subject: str, 
        html_body: str, 
        text_fallback: str = ""
    ) -> str:
        """
        Sends an HTML email with optional plain-text fallback.
        Uses SMTP connection if SMTP settings are configured in settings.
        Otherwise falls back to console printing (development only).
        Returns the email status string: "SENT", "FAILED", or "DEVELOPMENT_LOG_ONLY".
        """
        email_from = getattr(settings, "SMTP_FROM_EMAIL", "noreply@donateai.org")
        smtp_host = getattr(settings, "SMTP_HOST", None)
        smtp_port = getattr(settings, "SMTP_PORT", 587)
        smtp_username = getattr(settings, "SMTP_USERNAME", None)
        smtp_password = getattr(settings, "SMTP_PASSWORD", None)
        smtp_use_tls = getattr(settings, "SMTP_USE_TLS", True)

        # Fallback to console print if credentials are not configured
        if not smtp_host or not smtp_username or not smtp_password:
            logger.warning(
                f"[EMAIL_STATUS: DEVELOPMENT_LOG_ONLY] Logged email to {to_email}.\n"
                f"Reason: SMTP credentials are not fully configured in your environment.\n"
                f"Subject: {subject}\n"
                f"Body (truncated): {html_body[:300]}..."
            )
            # Print to stdout/console directly for testing feedback
            print(
                f"\n=== [DEVELOPMENT_LOG_ONLY EMAIL] ===\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Body:\n{text_fallback or html_body[:500]}\n"
                f"====================================\n"
            )
            return "DEVELOPMENT_LOG_ONLY"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = email_from
            msg["To"] = to_email

            if text_fallback:
                msg.attach(MIMEText(text_fallback, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Establish secure connection
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.ehlo()
            if smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(smtp_username, smtp_password)
            server.sendmail(email_from, to_email, msg.as_string())
            server.quit()

            logger.info(f"[EMAIL_STATUS: SENT] Email to {to_email} with subject '{subject}' sent successfully.")
            return "SENT"
        except Exception as e:
            logger.error(f"[EMAIL_STATUS: FAILED] Email to {to_email} with subject '{subject}' failed: {str(e)}")
            return "FAILED"

    @classmethod
    def load_template(cls, template_name: str, replacements: dict) -> str:
        """
        Loads an HTML email template from backend/templates/emails/ and performs replacements.
        """
        # Find path to templates/emails
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_path = os.path.join(base_dir, "templates", "emails", template_name)

        if not os.path.exists(template_path):
            logger.warning(f"Email template not found: {template_path}. Falling back to blank replacement.")
            return ""

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            for key, val in replacements.items():
                # Replace both {{ key }} and {{key}}
                template_content = template_content.replace(f"{{{{ {key} }}}}", str(val))
                template_content = template_content.replace(f"{{{{{key}}}}}", str(val))

            return template_content
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return ""
