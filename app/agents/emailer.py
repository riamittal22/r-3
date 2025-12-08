"""
Email Agent
Assembles and delivers the digest via HTML email or saves to file.
"""

import logging
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List

logger = logging.getLogger(__name__)


class EmailAgent:
    """Assemble and deliver the personalized digest."""

    def __init__(self):
        """Initialize the Email Agent with SMTP credentials."""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_from = os.getenv("EMAIL_FROM")
        self.email_to = os.getenv("EMAIL_TO")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        
        logger.info("Email Agent initialized")

    def create_html_digest(
        self,
        articles_by_preference: Dict[str, List[Dict]],
        user_name: str = "there",
    ) -> str:
        """
        Create a beautiful HTML email digest.
        
        Args:
            articles_by_preference: Dictionary mapping preferences to ranked articles
            user_name: User's name for personalization
            
        Returns:
            HTML email content
        """
        today = datetime.now().strftime("%B %d, %Y")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #4A90E2;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #4A90E2;
            margin: 0;
            font-size: 28px;
        }}
        .date {{
            color: #999;
            font-size: 12px;
            margin-top: 10px;
        }}
        .greeting {{
            color: #333;
            font-size: 16px;
            margin-bottom: 20px;
        }}
        .preference-section {{
            margin-bottom: 30px;
            border-left: 4px solid #4A90E2;
            padding-left: 15px;
        }}
        .preference-title {{
            color: #4A90E2;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            text-transform: capitalize;
        }}
        .article {{
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }}
        .article-title {{
            color: #2C3E50;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .article-summary {{
            color: #555;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        .article-meta {{
            color: #999;
            font-size: 12px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Your Personalized Digest</h1>
            <div class="date">{today}</div>
        </div>
        
        <div class="greeting">
            Good morning, {user_name}! ☀️ Here's your curated digest based on your interests.
        </div>
"""
        
        for preference, articles in articles_by_preference.items():
            if articles:
                html += f"""
        <div class="preference-section">
            <div class="preference-title">{preference.title()}</div>
"""
                for article in articles[:5]:  # Top 5 per preference
                    title = article.get("metadata", {}).get("title", "Untitled")
                    summary = article.get("summary", article.get("content", "")[:200])
                    source = article.get("metadata", {}).get("source", "Unknown")
                    
                    html += f"""
            <div class="article">
                <div class="article-title">{title}</div>
                <div class="article-summary">{summary}</div>
                <div class="article-meta">Source: {source}</div>
            </div>
"""
                
                html += "</div>"
        
        html += """
        <div class="footer">
            <p>This digest was automatically generated using RAG and multi-agent AI.</p>
            <p>© 2024 R^3 Project</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html

    def save_digest(
        self,
        html_content: str,
        output_file: str = "digest.html",
    ) -> bool:
        """
        Save digest to an HTML file.
        
        Args:
            html_content: HTML content
            output_file: Output file path
            
        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"✅ Digest saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving digest: {e}")
            return False

    def send_email(
        self,
        html_content: str,
        subject: str = "Your Daily Personalized Digest",
    ) -> bool:
        """
        Send digest via SMTP email.
        
        Args:
            html_content: HTML content
            subject: Email subject
            
        Returns:
            True if successful
        """
        if not self.email_from or not self.email_to or not self.email_password:
            logger.warning("Email credentials not configured; skipping email send")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = self.email_to
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.sendmail(self.email_from, self.email_to, msg.as_string())
            
            logger.info(f"✅ Email sent to {self.email_to}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
