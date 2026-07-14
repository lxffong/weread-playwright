import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

class Notifier:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def send(self, title: str, message: str):
        if self.config.get('notifications.email.enabled'):
            self._send_email(title, message)
        if self.config.get('notifications.bark.enabled'):
            self._send_bark(title, message)
 
    def send_with_attachment(self, title: str, message: str, attachment_path: str):
        if self.config.get('notifications.email.enabled'):
            self.send_email_with_attachment(title, message, attachment_path)
        if self.config.get('notifications.bark.enabled'):
            self._send_bark(title, message)

    def _send_email(self, subject: str, body: str):
        try:
            smtp_server = self.config.get('notifications.email.smtp_server')
            smtp_port = self.config.get('notifications.email.smtp_port')
            from_email = self.config.get('notifications.email.from')
            to_email = self.config.get('notifications.email.to')
            password = self.config.get('notifications.email.password')
            security = self.config.get('notifications.email.security', 'auto')

            # 验证配置完整性
            if not all([smtp_server, smtp_port, from_email, to_email, password]):
                self.logger.warning("邮件配置不完整，跳过发送")
                return

            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 发送邮件，根据 security 配置和端口选择加密方式
            server = self._connect_smtp(smtp_server, smtp_port, security)

            server.login(from_email, password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"邮件通知已发送: {subject}")

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP认证失败，请检查邮箱和密码: {e}")
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP错误: {e}")
        except ConnectionError as e:
            self.logger.error(f"连接错误，请检查SMTP服务器地址和端口: {e}")
        except TimeoutError as e:
            self.logger.error(f"连接超时，请检查网络或防火墙设置: {e}")
        except Exception as e:
            self.logger.error(f"邮件发送失败: {type(e).__name__}: {e}")

    def _connect_smtp(self, smtp_server: str, smtp_port: int, security: str):
        """根据 security 配置创建 SMTP 连接"""
        if security == 'ssl':
            self.logger.info("使用 SSL 连接...")
            return smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        elif security == 'tls':
            self.logger.info("使用 TLS 连接...")
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()
            return server
        elif security == 'none':
            self.logger.info("使用无加密连接...")
            return smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        else:  # auto
            # 根据端口自动选择：465 用 SSL，其他用 TLS
            if smtp_port == 465:
                self.logger.info("自动选择 SSL 连接...")
                return smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                self.logger.info("自动选择 TLS 连接...")
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
                return server

    def _send_bark(self, title: str, body: str):
        try:
            bark_url = self.config.get('notifications.bark.url')
            url = f"{bark_url}/{title}/{body}"
            requests.get(url, timeout=10)
            self.logger.info(f"Bark 通知已发送: {title}")
        except Exception as e:
            self.logger.error(f"Bark 发送失败: {e}")

    def send_email_with_attachment(self, subject: str, body: str, attachment_path: str):
        """发送带附件的邮件"""
        if not self.config.get('notifications.email.enabled'):
            return

        try:
            smtp_server = self.config.get('notifications.email.smtp_server')
            smtp_port = self.config.get('notifications.email.smtp_port')
            from_email = self.config.get('notifications.email.from')
            to_email = self.config.get('notifications.email.to')
            password = self.config.get('notifications.email.password')
            security = self.config.get('notifications.email.security', 'auto')

            # 验证配置完整性
            if not all([smtp_server, smtp_port, from_email, to_email, password]):
                self.logger.warning("邮件配置不完整，跳过发送")
                return

            # 验证附件文件存在
            attachment_file = Path(attachment_path)
            if not attachment_file.exists():
                self.logger.warning(f"附件文件不存在: {attachment_path}")
                return

            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添加附件
            with open(attachment_file, 'rb') as f:
                part = MIMEApplication(f.read(), Name=attachment_file.name)
            part['Content-Disposition'] = f'attachment; filename="{attachment_file.name}"'
            msg.attach(part)

            # 发送邮件，根据 security 配置选择加密方式
            self.logger.info(f"正在连接邮件服务器: {smtp_server}:{smtp_port}")
            server = self._connect_smtp(smtp_server, smtp_port, security)

            self.logger.info("正在登录邮件服务器...")
            server.login(from_email, password)

            self.logger.info("正在发送邮件...")
            server.send_message(msg)
            server.quit()

            self.logger.info(f"带附件的邮件已发送: {subject}")

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP认证失败，请检查邮箱和密码: {e}")
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP错误: {e}")
        except ConnectionError as e:
            self.logger.error(f"连接错误，请检查SMTP服务器地址和端口: {e}")
        except TimeoutError as e:
            self.logger.error(f"连接超时，请检查网络或防火墙设置: {e}")
        except Exception as e:
            self.logger.error(f"带附件邮件发送失败: {type(e).__name__}: {e}")
