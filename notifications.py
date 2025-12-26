"""
notifications.py

Classe Notifier para enviar e-mails (Gmail) com ou sem anexo.
- Usa smtplib + EmailMessage.
- Possui envio síncrono (send_email) com tratamento de erro.
- Possui envio em background (send_email_background) para não travar o vídeo.
"""

import smtplib
from email.message import EmailMessage
from pathlib import Path
import mimetypes
import threading


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
                    msg.add_attachment(
                        f.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=file_path.name,
                    )
            else:
                print(f"[Notifier] Aviso: anexo '{attachment_path}' não encontrado.")
        return msg

    def send_email(
        self,
        subject: str,
        body: str,
        to: str | None = None,
        attachment_path: str | None = None,
    ) -> None:
        """
        Envia o e-mail de forma síncrona.
        Usado internamente pelo método em background.
        """
        to_addr = to or self.email_to_default

        msg = self._build_message(
            subject=subject,
            body=body,
            to=to_addr,
            attachment_path=attachment_path,
        )

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.email_user, self.email_app_password)
                server.send_message(msg)
                print("[Notifier] E-mail enviado com sucesso.")
        except smtplib.SMTPAuthenticationError as e:
            print(f"[Notifier] ERRO de autenticação SMTP: {e}")
        except smtplib.SMTPException as e:
            print(f"[Notifier] ERRO SMTP ao enviar e-mail: {e}")
        except Exception as e:
            print(f"[Notifier] ERRO inesperado ao enviar e-mail: {e}")

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
        thread = threading.Thread(
            target=self.send_email,
            args=(subject, body, to, attachment_path),
            daemon=True,
        )
        thread.start()
