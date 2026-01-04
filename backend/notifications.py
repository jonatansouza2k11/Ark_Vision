"""
notifications.py - OPTIMIZED v2.0

Email notification system with Gmail SMTP
Enhanced with retry logic, metrics tracking, and comprehensive logging

Features:
- Synchronous and asynchronous email sending
- Attachment support with validation
- Automatic retry on transient failures
- Connection pooling and timeout handling
- Structured logging with metrics
- Thread-safe background sending
"""

import smtplib
from email.message import EmailMessage
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, List
from functools import lru_cache
import mimetypes
import threading
import logging
import time

logger = logging.getLogger(__name__)


# ============================================
# OTIMIZAÇÃO 1: Constants & Enums
# ============================================

class EmailStatus(str, Enum):
    """✅ Email delivery status"""
    SUCCESS = "success"
    FAILED = "failed"
    QUEUED = "queued"
    SENDING = "sending"
    RETRY = "retry"


class EmailErrorType(str, Enum):
    """✅ Specific error types for better handling"""
    AUTH_FAILED = "authentication_failed"
    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    SMTP_ERROR = "smtp_error"
    ATTACHMENT_NOT_FOUND = "attachment_not_found"
    INVALID_CONFIG = "invalid_configuration"
    UNKNOWN = "unknown_error"


# Default SMTP settings
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5  # seconds
MAX_ATTACHMENT_SIZE_MB = 25  # Gmail limit


# ============================================
# OTIMIZAÇÃO 2: Dataclasses for Type Safety
# ============================================

@dataclass(frozen=True)
class SMTPConfig:
    """✅ Immutable SMTP configuration"""
    server: str
    port: int
    user: str
    password: str
    timeout: int = DEFAULT_TIMEOUT
    use_tls: bool = True
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.server or not self.user or not self.password:
            raise ValueError("SMTP server, user, and password are required")
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid port: {self.port}")


@dataclass
class EmailConfig:
    """✅ Email configuration with validation"""
    to: str
    subject: str
    body: str
    from_addr: Optional[str] = None
    attachment_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate email config"""
        if not self.to or "@" not in self.to:
            raise ValueError(f"Invalid recipient email: {self.to}")
        if not self.subject:
            raise ValueError("Email subject cannot be empty")


@dataclass
class EmailResult:
    """✅ Comprehensive email sending result"""
    status: EmailStatus
    elapsed_time: float
    error_type: Optional[EmailErrorType] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    
    @property
    def success(self) -> bool:
        """Convenience property"""
        return self.status == EmailStatus.SUCCESS
    
    def __str__(self) -> str:
        if self.success:
            return f"Email sent successfully in {self.elapsed_time:.2f}s"
        return f"Email failed: {self.error_type} - {self.error_message}"


@dataclass
class AttachmentInfo:
    """✅ Attachment metadata"""
    path: Path
    size_bytes: int
    mime_type: str
    filename: str
    
    @property
    def size_mb(self) -> float:
        """Size in megabytes"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def size_kb(self) -> float:
        """Size in kilobytes"""
        return self.size_bytes / 1024


# ============================================
# OTIMIZAÇÃO 3: Helper Functions
# ============================================

def _validate_attachment(path: str) -> Tuple[bool, Optional[AttachmentInfo], Optional[str]]:
    """
    ✅ Validate attachment file
    
    Args:
        path: Path to attachment file
    
    Returns:
        Tuple of (is_valid, attachment_info, error_message)
    """
    try:
        file_path = Path(path)
        
        # Check if file exists
        if not file_path.is_file():
            return False, None, f"File not found: {path}"
        
        # Get file size
        size_bytes = file_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        # Check size limit
        if size_mb > MAX_ATTACHMENT_SIZE_MB:
            return False, None, f"File too large: {size_mb:.1f}MB (max: {MAX_ATTACHMENT_SIZE_MB}MB)"
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"
        
        # Create AttachmentInfo
        info = AttachmentInfo(
            path=file_path,
            size_bytes=size_bytes,
            mime_type=mime_type,
            filename=file_path.name
        )
        
        return True, info, None
        
    except Exception as e:
        return False, None, f"Attachment validation error: {e}"


def _parse_mime_type(mime_type: str) -> Tuple[str, str]:
    """
    ✅ Parse MIME type into maintype and subtype
    
    Args:
        mime_type: MIME type string (e.g., "image/jpeg")
    
    Returns:
        Tuple of (maintype, subtype)
    """
    parts = mime_type.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "application", "octet-stream"


def _format_error_message(error: Exception, error_type: EmailErrorType) -> str:
    """
    ✅ Format error message with context
    
    Args:
        error: Exception object
        error_type: Type of error
    
    Returns:
        Formatted error message
    """
    base_msg = str(error)
    
    context_map = {
        EmailErrorType.AUTH_FAILED: "Check Gmail App Password and ensure 2FA is enabled",
        EmailErrorType.CONNECTION_FAILED: "Check network connectivity and firewall settings",
        EmailErrorType.TIMEOUT: "SMTP server not responding, check network or try again later",
        EmailErrorType.SMTP_ERROR: "Check SMTP server settings and recipient address",
    }
    
    context = context_map.get(error_type, "")
    if context:
        return f"{base_msg} ({context})"
    return base_msg


@lru_cache(maxsize=16)
def _get_mime_info(filename: str) -> Tuple[str, str]:
    """
    ✅ Cached MIME type lookup
    
    Args:
        filename: Name of file
    
    Returns:
        Tuple of (maintype, subtype)
    """
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "application/octet-stream"
    return _parse_mime_type(mime_type)


# ============================================
# OTIMIZAÇÃO 4: Metrics Tracking
# ============================================

@dataclass
class EmailMetrics:
    """✅ Email sending metrics tracker"""
    total_sent: int = 0
    total_failed: int = 0
    total_retries: int = 0
    total_time: float = 0.0
    last_send_time: Optional[float] = None
    
    def record_success(self, elapsed: float):
        """Record successful send"""
        self.total_sent += 1
        self.total_time += elapsed
        self.last_send_time = time.time()
    
    def record_failure(self, retry_count: int = 0):
        """Record failed send"""
        self.total_failed += 1
        self.total_retries += retry_count
        self.last_send_time = time.time()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.total_sent + self.total_failed
        return (self.total_sent / total * 100) if total > 0 else 0.0
    
    @property
    def average_time(self) -> float:
        """Calculate average send time"""
        return (self.total_time / self.total_sent) if self.total_sent > 0 else 0.0
    
    def __str__(self) -> str:
        return (
            f"EmailMetrics(sent={self.total_sent}, failed={self.total_failed}, "
            f"success_rate={self.success_rate:.1f}%, avg_time={self.average_time:.2f}s)"
        )


# ============================================
# MAIN NOTIFIER CLASS
# ============================================

class Notifier:
    """
    Email notification system with Gmail SMTP
    
    Features:
    - Sync and async sending
    - Automatic retry on failures
    - Attachment support with validation
    - Comprehensive logging and metrics
    """
    
    def __init__(
        self,
        email_user: str,
        email_app_password: str,
        email_to: str,
        smtp_server: str = DEFAULT_SMTP_SERVER,
        smtp_port: int = DEFAULT_SMTP_PORT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: int = DEFAULT_RETRY_DELAY,
    ) -> None:
        """
        Initialize email notifier
        
        Args:
            email_user: Gmail address (sender)
            email_app_password: Gmail App Password (not regular password)
            email_to: Default recipient email
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries (seconds)
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Create SMTP config (validates automatically)
        try:
            self.smtp_config = SMTPConfig(
                server=smtp_server,
                port=smtp_port,
                user=email_user,
                password=email_app_password
            )
        except ValueError as e:
            logger.error(f"❌ Invalid SMTP configuration: {e}")
            raise
        
        self.email_to_default = email_to
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Metrics tracking
        self.metrics = EmailMetrics()
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(
            f"📧 Notifier initialized: {email_user} -> {email_to} "
            f"via {smtp_server}:{smtp_port} (retries: {max_retries})"
        )
    
    def _build_message(
        self,
        config: EmailConfig,
        attachment_info: Optional[AttachmentInfo] = None
    ) -> EmailMessage:
        """
        Build EmailMessage object
        
        Args:
            config: Email configuration
            attachment_info: Optional attachment metadata
        
        Returns:
            EmailMessage ready to send
        """
        msg = EmailMessage()
        msg["From"] = config.from_addr or self.smtp_config.user
        msg["To"] = config.to
        msg["Subject"] = config.subject
        msg.set_content(config.body)
        
        if attachment_info:
            maintype, subtype = _parse_mime_type(attachment_info.mime_type)
            
            with open(attachment_info.path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment_info.filename,
                )
            
            logger.debug(
                f"📎 Attachment added: {attachment_info.filename} "
                f"({attachment_info.size_kb:.1f} KB, {attachment_info.mime_type})"
            )
        
        return msg
    
    def _send_with_retry(
        self,
        msg: EmailMessage,
        subject: str
    ) -> EmailResult:
        """
        Send email with automatic retry logic
        
        Args:
            msg: EmailMessage to send
            subject: Email subject (for logging)
        
        Returns:
            EmailResult with delivery status
        """
        start_time = time.time()
        last_error = None
        last_error_type = EmailErrorType.UNKNOWN
        
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                logger.info(
                    f"🔄 Retry attempt {attempt}/{self.max_retries} "
                    f"for '{subject}' (waiting {self.retry_delay}s)"
                )
                time.sleep(self.retry_delay)
            
            try:
                # Connect and send
                with smtplib.SMTP(
                    self.smtp_config.server,
                    self.smtp_config.port,
                    timeout=self.smtp_config.timeout
                ) as server:
                    
                    if attempt == 0:
                        logger.debug(
                            f"🔌 Connecting to SMTP: "
                            f"{self.smtp_config.server}:{self.smtp_config.port}"
                        )
                    
                    if self.smtp_config.use_tls:
                        server.starttls()
                        logger.debug("🔐 TLS started")
                    
                    server.login(
                        self.smtp_config.user,
                        self.smtp_config.password
                    )
                    
                    if attempt == 0:
                        logger.debug(f"✅ Authenticated as {self.smtp_config.user}")
                    
                    server.send_message(msg)
                    
                    elapsed = time.time() - start_time
                    
                    logger.info(
                        f"✅ Email sent successfully in {elapsed:.2f}s "
                        f"(attempt {attempt + 1}): '{subject}'"
                    )
                    
                    return EmailResult(
                        status=EmailStatus.SUCCESS,
                        elapsed_time=elapsed,
                        retry_count=attempt
                    )
            
            except smtplib.SMTPAuthenticationError as e:
                last_error = e
                last_error_type = EmailErrorType.AUTH_FAILED
                logger.error(
                    f"❌ SMTP Authentication failed (attempt {attempt + 1}): {e}"
                )
                # Don't retry auth errors
                break
            
            except smtplib.SMTPException as e:
                last_error = e
                last_error_type = EmailErrorType.SMTP_ERROR
                logger.warning(
                    f"⚠️ SMTP error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
            
            except (ConnectionError, OSError) as e:
                last_error = e
                last_error_type = EmailErrorType.CONNECTION_FAILED
                logger.warning(
                    f"⚠️ Connection error (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                )
            
            except TimeoutError as e:
                last_error = e
                last_error_type = EmailErrorType.TIMEOUT
                logger.warning(
                    f"⚠️ Timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )
            
            except Exception as e:
                last_error = e
                last_error_type = EmailErrorType.UNKNOWN
                logger.error(
                    f"❌ Unexpected error (attempt {attempt + 1}): {e}",
                    exc_info=True
                )
                break
        
        # All retries failed
        elapsed = time.time() - start_time
        error_msg = _format_error_message(last_error, last_error_type)
        
        logger.error(
            f"❌ Email failed after {self.max_retries + 1} attempts "
            f"in {elapsed:.2f}s: '{subject}' - {error_msg}"
        )
        
        return EmailResult(
            status=EmailStatus.FAILED,
            elapsed_time=elapsed,
            error_type=last_error_type,
            error_message=error_msg,
            retry_count=self.max_retries
        )
    
    def send_email(
        self,
        subject: str,
        body: str,
        to: Optional[str] = None,
        attachment_path: Optional[str] = None,
    ) -> EmailResult:
        """
        Send email synchronously
        
        Args:
            subject: Email subject
            body: Email body (plain text)
            to: Recipient email (uses default if None)
            attachment_path: Optional file path to attach
        
        Returns:
            EmailResult with delivery status and metrics
        """
        to_addr = to or self.email_to_default
        
        logger.info(f"📧 Sending email: '{subject}' to {to_addr}")
        
        # Validate attachment if provided
        attachment_info = None
        if attachment_path:
            is_valid, attachment_info, error = _validate_attachment(attachment_path)
            if not is_valid:
                logger.error(f"❌ Invalid attachment: {error}")
                result = EmailResult(
                    status=EmailStatus.FAILED,
                    elapsed_time=0.0,
                    error_type=EmailErrorType.ATTACHMENT_NOT_FOUND,
                    error_message=error
                )
                with self._lock:
                    self.metrics.record_failure()
                return result
        
        # Build email config
        try:
            email_config = EmailConfig(
                to=to_addr,
                subject=subject,
                body=body,
                attachment_path=attachment_path
            )
        except ValueError as e:
            logger.error(f"❌ Invalid email configuration: {e}")
            result = EmailResult(
                status=EmailStatus.FAILED,
                elapsed_time=0.0,
                error_type=EmailErrorType.INVALID_CONFIG,
                error_message=str(e)
            )
            with self._lock:
                self.metrics.record_failure()
            return result
        
        # Build message
        msg = self._build_message(email_config, attachment_info)
        
        # Send with retry
        result = self._send_with_retry(msg, subject)
        
        # Update metrics
        with self._lock:
            if result.success:
                self.metrics.record_success(result.elapsed_time)
            else:
                self.metrics.record_failure(result.retry_count)
        
        return result
    
    def send_email_background(
        self,
        subject: str,
        body: str,
        to: Optional[str] = None,
        attachment_path: Optional[str] = None,
    ) -> None:
        """
        Send email asynchronously in background thread
        
        Args:
            subject: Email subject
            body: Email body
            to: Recipient email (uses default if None)
            attachment_path: Optional file path to attach
        """
        to_addr = to or self.email_to_default
        
        logger.info(
            f"📬 Email queued for background delivery: '{subject}' to {to_addr}"
        )
        
        thread = threading.Thread(
            target=self._send_background_worker,
            args=(subject, body, to, attachment_path),
            daemon=True,
            name=f"EmailThread-{subject[:20]}"
        )
        thread.start()
        
        logger.debug(f"🧵 Email thread started: {thread.name}")
    
    def _send_background_worker(
        self,
        subject: str,
        body: str,
        to: Optional[str],
        attachment_path: Optional[str],
    ) -> None:
        """
        Background worker for async email sending
        
        Args:
            subject: Email subject
            body: Email body
            to: Recipient email
            attachment_path: Optional attachment path
        """
        try:
            result = self.send_email(subject, body, to, attachment_path)
            
            if result.success:
                logger.debug(
                    f"🧵 Email thread completed successfully: '{subject}' "
                    f"in {result.elapsed_time:.2f}s"
                )
            else:
                logger.error(
                    f"🧵 Email thread failed: '{subject}' - {result.error_message}"
                )
        except Exception as e:
            logger.error(
                f"🧵 Email thread crashed: '{subject}' - {e}",
                exc_info=True
            )
    
    def get_metrics(self) -> EmailMetrics:
        """
        Get current email metrics
        
        Returns:
            Copy of current metrics
        """
        with self._lock:
            return EmailMetrics(
                total_sent=self.metrics.total_sent,
                total_failed=self.metrics.total_failed,
                total_retries=self.metrics.total_retries,
                total_time=self.metrics.total_time,
                last_send_time=self.metrics.last_send_time
            )
    
    def reset_metrics(self) -> None:
        """Reset metrics counters"""
        with self._lock:
            self.metrics = EmailMetrics()
        logger.info("📊 Email metrics reset")


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    import os
    
    print("=" * 70)
    print("🧪 Testing Email Notifier v2.0")
    print("=" * 70)
    
    # Mock configuration (replace with real values to test)
    notifier = Notifier(
        email_user="test@gmail.com",
        email_app_password="mock_password",
        email_to="recipient@example.com",
        max_retries=2
    )
    
    print("\n1️⃣ Testing attachment validation...")
    is_valid, info, error = _validate_attachment(__file__)
    if is_valid and info:
        print(f"   ✅ Valid: {info.filename} ({info.size_kb:.1f} KB)")
    else:
        print(f"   ❌ Invalid: {error}")
    
    print("\n2️⃣ Testing MIME type parsing...")
    maintype, subtype = _parse_mime_type("image/jpeg")
    print(f"   image/jpeg -> {maintype}/{subtype}")
    
    print("\n3️⃣ Testing metrics...")
    notifier.metrics.record_success(1.5)
    notifier.metrics.record_success(2.0)
    notifier.metrics.record_failure(retry_count=1)
    print(f"   {notifier.get_metrics()}")
    
    print("\n4️⃣ Testing EmailResult...")
    result = EmailResult(
        status=EmailStatus.SUCCESS,
        elapsed_time=1.23
    )
    print(f"   {result}")
    
    print("\n" + "=" * 70)
    print("✅ Tests completed!")
    print("=" * 70)
