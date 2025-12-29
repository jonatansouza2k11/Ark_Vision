"""
notifications.py

Classe Notifier para enviar e-mails (Gmail) com ou sem anexo.
- Usa smtplib + EmailMessage.
- Possui envio síncrono (send_email) com tratamento de erro.
- Possui envio em background (send_email_background) para não travar o vídeo.

✨ MELHORIAS:
- Sistema de logging estruturado
- Logs de sucesso/erro detalhados
- Métricas de tempo de envio
- Logs de tentativas de reconexão
"""

import smtplib
from email.message import EmailMessage
from pathlib import Path
import mimetypes
import threading
import logging
import time

# ✨ NOVO: Configurar logger para este módulo
logger = logging.getLogger(__name__)


class Notifier:
    def __init__(
        self,
        email_user: str,
        email_app_password: str,
        email_to: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ) -> None:
        """
        email_user: endereço Gmail do remetente.
        email_app_password: senha de app do Gmail.
        email_to: destinatário padrão.
        """
        self.email_user = email_user
        self.email_app_password = email_app_password
        self.email_to_default = email_to
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        
        # ✨ NOVO: Log de inicialização
        logger.info(f"📧 Notifier initialized: {email_user} -> {email_to} via {smtp_server}:{smtp_port}")

    def _build_message(
        self,
        subject: str,
        body: str,
        to: str,
        attachment_path: str | None = None,
    ) -> EmailMessage:
        """
        Monta o EmailMessage com texto e, opcionalmente, anexo.
        """
        msg = EmailMessage()
        msg["From"] = self.email_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        if attachment_path is not None:
            file_path = Path(attachment_path)
            if file_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type is None:
                    mime_type = "application/octet-stream"
                maintype, subtype = mime_type.split("/", 1)

                with open(file_path, "rb") as f:
                    file_size_kb = file_path.stat().st_size / 1024
                    msg.add_attachment(
                        f.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=file_path.name,
                    )
                
                # ✨ NOVO: Log de anexo adicionado
                logger.debug(f"📎 Attachment added: {file_path.name} ({file_size_kb:.1f} KB)")
            else:
                # ✨ MELHORADO: Log de aviso mais detalhado
                logger.warning(f"⚠️ Attachment not found: {attachment_path}")
                print(f"[Notifier] Aviso: anexo '{attachment_path}' não encontrado.")
        
        return msg

    def send_email(
        self,
        subject: str,
        body: str,
        to: str | None = None,
        attachment_path: str | None = None,
    ) -> bool:  # ✨ NOVO: Retorna bool indicando sucesso
        """
        Envia o e-mail de forma síncrona.
        Usado internamente pelo método em background.
        
        Returns:
            bool: True se enviado com sucesso, False caso contrário.
        """
        to_addr = to or self.email_to_default
        start_time = time.time()
        
        # ✨ NOVO: Log de início de envio
        logger.info(f"📧 Sending email: '{subject}' to {to_addr}")
        if attachment_path:
            logger.debug(f"   With attachment: {attachment_path}")

        msg = self._build_message(
            subject=subject,
            body=body,
            to=to_addr,
            attachment_path=attachment_path,
        )

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                # ✨ NOVO: Log de conexão
                logger.debug(f"🔌 Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
                
                server.starttls()
                logger.debug("🔐 TLS started")
                
                server.login(self.email_user, self.email_app_password)
                logger.debug(f"✅ Authenticated as {self.email_user}")
                
                server.send_message(msg)
                
                elapsed = time.time() - start_time
                
                # ✨ NOVO: Log de sucesso com métricas
                logger.info(f"✅ Email sent successfully in {elapsed:.2f}s: '{subject}' to {to_addr}")
                print(f"[Notifier] E-mail enviado com sucesso em {elapsed:.2f}s.")
                
                return True
                
        except smtplib.SMTPAuthenticationError as e:
            elapsed = time.time() - start_time
            # ✨ MELHORADO: Log mais detalhado
            logger.error(f"❌ SMTP Authentication failed after {elapsed:.2f}s: {e}")
            logger.error(f"   Check credentials for {self.email_user}")
            print(f"[Notifier] ERRO de autenticação SMTP: {e}")
            return False
            
        except smtplib.SMTPException as e:
            elapsed = time.time() - start_time
            # ✨ MELHORADO: Log com contexto
            logger.error(f"❌ SMTP error after {elapsed:.2f}s sending '{subject}': {e}")
            print(f"[Notifier] ERRO SMTP ao enviar e-mail: {e}")
            return False
            
        except ConnectionError as e:
            elapsed = time.time() - start_time
            # ✨ NOVO: Log específico para erros de conexão
            logger.error(f"❌ Connection error after {elapsed:.2f}s to {self.smtp_server}:{self.smtp_port}: {e}")
            logger.error("   Check network connectivity and firewall settings")
            print(f"[Notifier] ERRO de conexão: {e}")
            return False
            
        except TimeoutError as e:
            elapsed = time.time() - start_time
            # ✨ NOVO: Log específico para timeout
            logger.error(f"❌ Timeout after {elapsed:.2f}s connecting to {self.smtp_server}:{self.smtp_port}")
            print(f"[Notifier] ERRO: Timeout na conexão")
            return False
            
        except Exception as e:
            elapsed = time.time() - start_time
            # ✨ MELHORADO: Log com stack trace completo
            logger.error(f"❌ Unexpected error after {elapsed:.2f}s sending email '{subject}': {e}", exc_info=True)
            print(f"[Notifier] ERRO inesperado ao enviar e-mail: {e}")
            return False

    def send_email_background(
        self,
        subject: str,
        body: str,
        to: str | None = None,
        attachment_path: str | None = None,
    ) -> None:
        """
        Envia o e-mail em uma thread separada para não travar o loop principal.

        Exemplo:
            notifier.send_email_background(
                subject="Alerta",
                body="Pessoa fora da área segura.",
                attachment_path="alerta_id_1.jpg",
            )
        """
        to_addr = to or self.email_to_default
        
        # ✨ NOVO: Log de enfileiramento
        logger.info(f"📬 Email queued for background delivery: '{subject}' to {to_addr}")
        
        thread = threading.Thread(
            target=self._send_with_callback,
            args=(subject, body, to, attachment_path),
            daemon=True,
            name=f"EmailThread-{subject[:20]}"  # ✨ NOVO: Nome descritivo para thread
        )
        thread.start()
        
        # ✨ NOVO: Log de thread criada
        logger.debug(f"🧵 Email thread started: {thread.name}")
    
    def _send_with_callback(
        self,
        subject: str,
        body: str,
        to: str | None,
        attachment_path: str | None,
    ) -> None:
        """
        ✨ NOVO: Wrapper interno para log de conclusão de thread.
        """
        success = self.send_email(subject, body, to, attachment_path)
        
        if success:
            logger.debug(f"🧵 Email thread completed successfully: '{subject}'")
        else:
            logger.error(f"🧵 Email thread failed: '{subject}'")
