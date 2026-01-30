"""Email notification channel implementation.

This module provides email notifications using SMTP with both HTML and plain text versions.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from lazarus.config.schema import EmailConfig
from lazarus.core.healer import HealingResult

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification channel using SMTP.

    Sends formatted emails with both HTML and plain text versions, including
    error details and PR links when available.

    Attributes:
        config: Email configuration including SMTP settings and recipients
        timeout: SMTP connection timeout in seconds (default: 10)
    """

    def __init__(self, config: EmailConfig, timeout: int = 10) -> None:
        """Initialize Email notifier.

        Args:
            config: Email configuration
            timeout: SMTP connection timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._name = "email"

    @property
    def name(self) -> str:
        """Get the name of this notification channel."""
        return self._name

    def send(self, result: HealingResult, script_path: Path) -> bool:
        """Send an email notification about a healing result.

        Args:
            result: The healing result to notify about
            script_path: Path to the script that was healed

        Returns:
            True if notification was sent successfully, False otherwise
        """
        # Check if we should send based on success/failure
        if result.success and not self.config.on_success:
            logger.debug("Skipping email notification for successful healing (disabled)")
            return True

        if not result.success and not self.config.on_failure:
            logger.debug("Skipping email notification for failed healing (disabled)")
            return True

        try:
            msg = self._build_message(result, script_path)

            # Connect to SMTP server
            if self.config.use_tls:
                server = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.timeout,
                )
                server.starttls()
            else:
                server = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.timeout,
                )

            try:
                # Login if credentials provided
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)

                # Send email
                server.send_message(msg)

                logger.info(f"Successfully sent email notification to {len(self.config.to_addrs)} recipients")
                return True

            finally:
                server.quit()

        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {e}")
            return False

    def _build_message(self, result: HealingResult, script_path: Path) -> MIMEMultipart:
        """Build email message with HTML and plain text versions.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            MIMEMultipart message ready to send
        """
        # Create message container
        msg = MIMEMultipart("alternative")

        # Subject line
        status = "Success" if result.success else "Failed"
        msg["Subject"] = f"[Lazarus] Healing {status}: {script_path.name}"
        msg["From"] = self.config.from_addr
        msg["To"] = ", ".join(self.config.to_addrs)

        # Build plain text version
        text_body = self._build_text_body(result, script_path)

        # Build HTML version
        html_body = self._build_html_body(result, script_path)

        # Attach both versions (clients will prefer HTML if available)
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        return msg

    def _build_text_body(self, result: HealingResult, script_path: Path) -> str:
        """Build plain text email body.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            Plain text email body
        """
        status = "SUCCESSFUL" if result.success else "FAILED"
        lines = [
            f"Lazarus Healing {status}",
            "=" * 50,
            "",
            f"Script: {script_path}",
            f"Status: {status}",
            f"Attempts: {len(result.attempts)}",
            f"Duration: {result.duration:.2f} seconds",
            f"Exit Code: {result.final_execution.exit_code}",
            f"Timestamp: {result.final_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
        ]

        if result.pr_url:
            lines.extend([
                f"Pull Request: {result.pr_url}",
                "",
            ])

        if not result.success and result.error_message:
            lines.extend([
                "Error Summary:",
                "-" * 50,
                result.error_message,
                "",
            ])

        if result.final_execution.stderr:
            stderr = result.final_execution.stderr
            if len(stderr) > 500:
                stderr = stderr[:500] + "\n... (truncated)"

            lines.extend([
                "Error Output:",
                "-" * 50,
                stderr,
                "",
            ])

        lines.extend([
            "",
            "This is an automated notification from Lazarus.",
        ])

        return "\n".join(lines)

    def _build_html_body(self, result: HealingResult, script_path: Path) -> str:
        """Build HTML email body.

        Args:
            result: Healing result
            script_path: Path to script

        Returns:
            HTML email body
        """
        status = "SUCCESSFUL" if result.success else "FAILED"
        status_color = "#28a745" if result.success else "#dc3545"
        status_emoji = "✅" if result.success else "❌"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: {status_color};
                    color: white;
                    padding: 20px;
                    border-radius: 5px 5px 0 0;
                    text-align: center;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 0 0 5px 5px;
                }}
                .field {{
                    margin-bottom: 15px;
                }}
                .label {{
                    font-weight: bold;
                    color: #555;
                }}
                .value {{
                    font-family: 'Courier New', monospace;
                    background-color: white;
                    padding: 5px 10px;
                    border-radius: 3px;
                    display: inline-block;
                }}
                .error {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 3px;
                }}
                .error pre {{
                    background-color: white;
                    padding: 10px;
                    border-radius: 3px;
                    overflow-x: auto;
                    font-size: 12px;
                }}
                .footer {{
                    margin-top: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #007bff;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{status_emoji} Healing {status}</h1>
            </div>
            <div class="content">
                <div class="field">
                    <span class="label">Script:</span>
                    <span class="value">{script_path}</span>
                </div>
                <div class="field">
                    <span class="label">Status:</span>
                    <span class="value">{status}</span>
                </div>
                <div class="field">
                    <span class="label">Attempts:</span>
                    <span class="value">{len(result.attempts)}</span>
                </div>
                <div class="field">
                    <span class="label">Duration:</span>
                    <span class="value">{result.duration:.2f} seconds</span>
                </div>
                <div class="field">
                    <span class="label">Exit Code:</span>
                    <span class="value">{result.final_execution.exit_code}</span>
                </div>
                <div class="field">
                    <span class="label">Timestamp:</span>
                    <span class="value">{result.final_execution.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
                </div>
        """

        if result.pr_url:
            html += f"""
                <div class="field" style="text-align: center; margin-top: 20px;">
                    <a href="{result.pr_url}" class="button">View Pull Request</a>
                </div>
            """

        if not result.success and result.error_message:
            error_html = result.error_message.replace("<", "&lt;").replace(">", "&gt;")
            html += f"""
                <div class="error">
                    <strong>Error Summary:</strong>
                    <pre>{error_html}</pre>
                </div>
            """

        if result.final_execution.stderr:
            stderr = result.final_execution.stderr
            if len(stderr) > 500:
                stderr = stderr[:500] + "\n... (truncated)"
            stderr_html = stderr.replace("<", "&lt;").replace(">", "&gt;")

            html += f"""
                <div class="error">
                    <strong>Error Output:</strong>
                    <pre>{stderr_html}</pre>
                </div>
            """

        html += """
            </div>
            <div class="footer">
                <p>This is an automated notification from Lazarus.</p>
            </div>
        </body>
        </html>
        """

        return html
