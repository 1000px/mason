# src/skills/builtin/email_sender/main.py
import smtplib
import os
import ssl
from email.mime.text import MIMEText
from email.header import Header
from src.skills.base import BaseSkill
from pydantic import BaseModel, Field

class EmailArgs(BaseModel):
    receiver: str = Field(description="收件人邮箱地址。")
    subject: str = Field(default="Mason 提醒", description="邮件主题。")
    body: str = Field(description="邮件正文内容。")

class EmailSenderSkill(BaseSkill):
    name = "email-sender"
    description = "发送电子邮件。"
    args_schema = EmailArgs
    
    permissions = {
        "network": True,
        "filesystem": True,
        "max_cpu": 0.3,
        "max_memory": 64
    }

    def __init__(self):
        super().__init__()
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.163.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")

    def execute(self, receiver: str, body: str, subject: str = "Mason 提醒") -> str:
        if not all([self.sender_email, self.sender_password]):
            return "❌ 错误：未配置发件人邮箱或授权码。"

        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = Header(self.sender_email)
            msg['To'] = Header(receiver)
            msg['Subject'] = Header(subject)

            # 🔧 针对 163 的 SSL 端口优化
            context = ssl.create_default_context()
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=context)
            
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, [receiver], msg.as_string())
            server.quit()
            
            return f"✅ 邮件已成功发送至 {receiver}"
        except Exception as e:
            return f"❌ 发送邮件失败: {str(e)}。请检查端口和授权码。"