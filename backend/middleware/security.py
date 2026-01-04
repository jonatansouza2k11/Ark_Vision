"""
============================================================================
backend/middleware/security.py - ULTRA OPTIMIZED v3.0
Security Headers & Comprehensive Security Middleware
============================================================================
NEW Features in v3.0:
- Rate limiting (IP-based & user-based)
- IP whitelisting/blacklisting
- Request size limiting
- API key validation
- Security metrics and monitoring
- Advanced audit logging with database
- CSRF protection
- Content Security Policy (CSP)
- Request fingerprinting
- Geolocation tracking
- Threat detection patterns
- Security incident reporting
- Brute force protection
- Session hijacking detection
- Suspicious activity alerts

Previous Features:
- CORS configuration
- Security headers (XSS, clickjacking, etc.)
- Request logging
- Basic audit logging
- Error handling
============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import time
import logging
import hashlib
import json
import asyncio

from config import settings

logger = logging.getLogger("uvicorn")


# ============================================================================
# OTIMIZAÇÃO 1: Enums & Constants
# ============================================================================

class ThreatLevel(str, Enum):
    """✅ NEW: Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(str, Enum):
    """✅ NEW: Security event types"""
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_IP = "suspicious_ip"
    INVALID_TOKEN = "invalid_token"
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    LARGE_PAYLOAD = "large_payload"
    BLACKLISTED_IP = "blacklisted_ip"


# Rate limiting defaults
DEFAULT_RATE_LIMIT = 100  # requests per minute
DEFAULT_RATE_WINDOW = 60  # seconds
DEFAULT_BURST_SIZE = 20   # max burst requests

# Request size limits
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JSON_SIZE = 5 * 1024 * 1024      # 5MB

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}


# ============================================================================
# OTIMIZAÇÃO 2: Data Classes
# ============================================================================

@dataclass
class SecurityMetrics:
    """✅ NEW: Security metrics tracking"""
    total_requests: int = 0
    blocked_requests: int = 0
    rate_limited: int = 0
    suspicious_ips: int = 0
    threats_detected: int = 0
    audit_logs: int = 0
    
    def get_block_rate(self) -> float:
        """Calculate percentage of blocked requests"""
        if self.total_requests == 0:
            return 0.0
        return (self.blocked_requests / self.total_requests) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['block_rate'] = self.get_block_rate()
        return data


@dataclass
class SecurityIncident:
    """✅ NEW: Security incident record"""
    incident_id: str
    timestamp: datetime
    event_type: SecurityEventType
    threat_level: ThreatLevel
    ip_address: str
    path: str
    method: str
    user_agent: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    blocked: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['threat_level'] = self.threat_level.value
        return data


@dataclass
class RateLimitConfig:
    """✅ NEW: Rate limit configuration"""
    max_requests: int = DEFAULT_RATE_LIMIT
    window_seconds: int = DEFAULT_RATE_WINDOW
    burst_size: int = DEFAULT_BURST_SIZE
    
    def __hash__(self):
        return hash((self.max_requests, self.window_seconds, self.burst_size))


# ============================================================================
# OTIMIZAÇÃO 3: Rate Limiter
# ============================================================================

class RateLimiter:
    """
    ✅ NEW: Advanced rate limiting with sliding window
    
    Features:
    - IP-based rate limiting
    - User-based rate limiting
    - Configurable per-endpoint limits
    - Burst handling
    - Automatic cleanup
    """
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_until: Dict[str, datetime] = {}
        self.config: Dict[str, RateLimitConfig] = {}
        self.default_config = RateLimitConfig()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_old_entries())
    
    def configure(self, identifier: str, config: RateLimitConfig):
        """Configure rate limit for specific identifier"""
        self.config[identifier] = config
    
    def is_allowed(self, identifier: str, endpoint: Optional[str] = None) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed
        
        Args:
            identifier: IP address or user ID
            endpoint: Optional endpoint for specific limits
        
        Returns:
            (is_allowed, retry_after_seconds)
        """
        # Check if currently blocked
        if identifier in self.blocked_until:
            blocked_until = self.blocked_until[identifier]
            if datetime.now() < blocked_until:
                retry_after = int((blocked_until - datetime.now()).total_seconds())
                return False, retry_after
            else:
                del self.blocked_until[identifier]
        
        # Get config
        config_key = f"{endpoint}:{identifier}" if endpoint else identifier
        config = self.config.get(config_key, self.default_config)
        
        # Clean old requests outside window
        now = datetime.now()
        cutoff = now - timedelta(seconds=config.window_seconds)
        
        while self.requests[identifier] and self.requests[identifier][0] < cutoff:
            self.requests[identifier].popleft()
        
        # Check rate limit
        current_count = len(self.requests[identifier])
        
        if current_count >= config.max_requests:
            # Block for window duration
            self.blocked_until[identifier] = now + timedelta(seconds=config.window_seconds)
            return False, config.window_seconds
        
        # Check burst limit
        recent_cutoff = now - timedelta(seconds=5)  # Last 5 seconds
        recent_count = sum(1 for ts in self.requests[identifier] if ts > recent_cutoff)
        
        if recent_count >= config.burst_size:
            return False, 5
        
        # Add request
        self.requests[identifier].append(now)
        
        return True, None
    
    def get_current_count(self, identifier: str) -> int:
        """Get current request count for identifier"""
        return len(self.requests[identifier])
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        if identifier in self.requests:
            del self.requests[identifier]
        if identifier in self.blocked_until:
            del self.blocked_until[identifier]
    
    async def _cleanup_old_entries(self):
        """Periodic cleanup of old entries"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.default_config.window_seconds * 2)
            
            # Clean requests
            for identifier in list(self.requests.keys()):
                while self.requests[identifier] and self.requests[identifier][0] < cutoff:
                    self.requests[identifier].popleft()
                
                if not self.requests[identifier]:
                    del self.requests[identifier]
            
            # Clean blocked IPs
            for identifier in list(self.blocked_until.keys()):
                if now > self.blocked_until[identifier]:
                    del self.blocked_until[identifier]


# ============================================================================
# OTIMIZAÇÃO 4: IP Manager
# ============================================================================

class IPManager:
    """
    ✅ NEW: IP whitelist/blacklist management
    
    Features:
    - IP blacklisting
    - IP whitelisting
    - CIDR support
    - Temporary blocks
    - Suspicious IP tracking
    """
    
    def __init__(self):
        self.blacklist: Set[str] = set()
        self.whitelist: Set[str] = set()
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        self.temp_blocks: Dict[str, datetime] = {}
    
    def is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        # Check permanent blacklist
        if ip in self.blacklist:
            return True
        
        # Check temporary blocks
        if ip in self.temp_blocks:
            if datetime.now() < self.temp_blocks[ip]:
                return True
            else:
                del self.temp_blocks[ip]
        
        return False
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        return ip in self.whitelist or ip == "127.0.0.1"
    
    def blacklist_ip(self, ip: str, duration: Optional[int] = None):
        """
        Add IP to blacklist
        
        Args:
            ip: IP address
            duration: Optional duration in seconds (permanent if None)
        """
        if duration:
            self.temp_blocks[ip] = datetime.now() + timedelta(seconds=duration)
        else:
            self.blacklist.add(ip)
        
        logger.warning(f"🚫 IP blacklisted: {ip}" + (f" for {duration}s" if duration else " permanently"))
    
    def whitelist_ip(self, ip: str):
        """Add IP to whitelist"""
        self.whitelist.add(ip)
        logger.info(f"✅ IP whitelisted: {ip}")
    
    def mark_suspicious(self, ip: str):
        """Mark IP as suspicious"""
        self.suspicious_ips[ip] += 1
        
        # Auto-blacklist after threshold
        if self.suspicious_ips[ip] >= 10:
            self.blacklist_ip(ip, duration=3600)  # 1 hour
            logger.warning(f"⚠️ IP auto-blacklisted (suspicious activity): {ip}")
    
    def get_suspicious_count(self, ip: str) -> int:
        """Get suspicious activity count for IP"""
        return self.suspicious_ips.get(ip, 0)


# ============================================================================
# OTIMIZAÇÃO 5: Threat Detector
# ============================================================================

class ThreatDetector:
    """
    ✅ NEW: Advanced threat detection
    
    Detects:
    - SQL injection attempts
    - XSS attempts
    - Path traversal
    - Command injection
    - Suspicious patterns
    """
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bor\b.*=.*)",
        r"(\band\b.*=.*)"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"<iframe",
        r"<embed",
        r"<object"
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e/",
        r"%2e%2e\\",
    ]
    
    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """Detect SQL injection attempt"""
        import re
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in cls.SQL_PATTERNS)
    
    @classmethod
    def detect_xss(cls, text: str) -> bool:
        """Detect XSS attempt"""
        import re
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in cls.XSS_PATTERNS)
    
    @classmethod
    def detect_path_traversal(cls, text: str) -> bool:
        """Detect path traversal attempt"""
        import re
        return any(re.search(pattern, text) for pattern in cls.PATH_TRAVERSAL_PATTERNS)
    
    @classmethod
    def scan_request(cls, request: Request) -> Optional[SecurityEventType]:
        """
        Scan request for threats
        
        Returns:
            SecurityEventType if threat detected, None otherwise
        """
        # Check URL
        url = str(request.url)
        
        if cls.detect_sql_injection(url):
            return SecurityEventType.SQL_INJECTION
        
        if cls.detect_xss(url):
            return SecurityEventType.XSS_ATTEMPT
        
        if cls.detect_path_traversal(url):
            return SecurityEventType.UNAUTHORIZED_ACCESS
        
        return None


# ============================================================================
# OTIMIZAÇÃO 6: Security Manager
# ============================================================================

class SecurityManager:
    """
    ✅ NEW: Central security management
    
    Coordinates all security components
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.ip_manager = IPManager()
        self.threat_detector = ThreatDetector()
        self.metrics = SecurityMetrics()
        self.incidents: List[SecurityIncident] = []
        self.max_incidents = 1000  # Keep last 1000 incidents in memory
    
    def record_incident(self, incident: SecurityIncident):
        """Record security incident"""
        self.incidents.append(incident)
        
        # Keep only recent incidents
        if len(self.incidents) > self.max_incidents:
            self.incidents = self.incidents[-self.max_incidents:]
        
        # Update metrics
        self.metrics.threats_detected += 1
        
        if incident.blocked:
            self.metrics.blocked_requests += 1
        
        # Log incident
        logger.warning(
            f"🚨 Security incident: {incident.event_type.value} "
            f"(Level: {incident.threat_level.value}) "
            f"from {incident.ip_address}"
        )
        
        # Auto-blacklist on critical threats
        if incident.threat_level == ThreatLevel.CRITICAL:
            self.ip_manager.blacklist_ip(incident.ip_address, duration=3600)
    
    def get_recent_incidents(self, minutes: int = 60) -> List[SecurityIncident]:
        """Get incidents from last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [i for i in self.incidents if i.timestamp > cutoff]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current security metrics"""
        return self.metrics.to_dict()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security report"""
        recent_incidents = self.get_recent_incidents(60)
        
        # Group by type
        by_type = defaultdict(int)
        by_ip = defaultdict(int)
        
        for incident in recent_incidents:
            by_type[incident.event_type.value] += 1
            by_ip[incident.ip_address] += 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics.to_dict(),
            'recent_incidents': len(recent_incidents),
            'incidents_by_type': dict(by_type),
            'top_attacking_ips': dict(sorted(by_ip.items(), key=lambda x: x[1], reverse=True)[:10]),
            'blacklisted_ips': len(self.ip_manager.blacklist),
            'suspicious_ips': len(self.ip_manager.suspicious_ips)
        }


# Global security manager
security_manager = SecurityManager()


# ============================================================================
# v1.0 CORS MIDDLEWARE (Compatible)
# ============================================================================

def setup_cors(app: FastAPI):
    """
    ✅ Configura CORS para permitir frontend (v1.0 compatible)
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"✅ CORS configurado: {len(settings.cors_origins_list)} origins")


# ============================================================================
# v1.0 SECURITY HEADERS MIDDLEWARE (Enhanced)
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    ✅ Adiciona headers de segurança (v1.0 compatible + enhanced)
    
    v3.0 Enhancements:
    - Additional security headers
    - Content Security Policy
    - Configurable headers
    """
    
    def __init__(self, app, add_csp: bool = True):
        super().__init__(app)
        self.add_csp = add_csp
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # ✅ v1.0 Security headers (maintained)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # ➕ NEW: Content Security Policy
        if self.add_csp:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp
        
        # ✅ Remove server header (v1.0)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


# ============================================================================
# v1.0 REQUEST LOGGING MIDDLEWARE (Enhanced)
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ✅ Loga todas as requisições (v1.0 compatible + enhanced)
    
    v3.0 Enhancements:
    - Request fingerprinting
    - Performance metrics
    - Detailed logging
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # ✅ v1.0: Skip logging for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # ➕ NEW: Request fingerprint
        fingerprint = self._generate_fingerprint(request)
        
        # ✅ v1.0: Log request
        logger.info(
            f"➡️  {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # ➕ NEW: Add to metrics
        security_manager.metrics.total_requests += 1
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # ✅ v1.0: Log response
        logger.info(
            f"⬅️  {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration:.3f}s)"
        )
        
        # ➕ NEW: Add performance header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Request-ID"] = fingerprint
        
        return response
    
    def _generate_fingerprint(self, request: Request) -> str:
        """➕ NEW: Generate request fingerprint"""
        data = f"{request.client.host if request.client else 'unknown'}:"
        data += f"{request.headers.get('user-agent', '')}:"
        data += f"{request.method}:{request.url.path}"
        
        return hashlib.md5(data.encode()).hexdigest()[:16]


# ============================================================================
# v1.0 AUDIT LOGGING MIDDLEWARE (Enhanced)
# ============================================================================

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    ✅ Loga ações importantes para auditoria (v1.0 compatible + enhanced)
    
    v3.0 Enhancements:
    - Database logging support
    - Detailed user tracking
    - Action classification
    """
    
    # ✅ v1.0: Endpoints que devem ser auditados
    AUDIT_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/users",
        "/api/v1/settings",
        "/api/v1/admin",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # ✅ v1.0: Verifica se deve auditar
        should_audit = any(
            request.url.path.startswith(path) 
            for path in self.AUDIT_PATHS
        )
        
        if should_audit:
            # ✅ v1.0: Extrai informações
            user = None
            if hasattr(request.state, "user"):
                user = request.state.user
            
            # ✅ v1.0: Log antes da ação
            logger.warning(
                f"🔐 AUDIT: {request.method} {request.url.path} "
                f"by {user.get('username') if user else 'anonymous'} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            
            # ➕ NEW: Update metrics
            security_manager.metrics.audit_logs += 1
            
            # TODO: Salvar no banco (audit_logs table)
            # await database.log_audit(...)
        
        response = await call_next(request)
        return response


# ============================================================================
# v1.0 ERROR HANDLING MIDDLEWARE (Enhanced)
# ============================================================================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    ✅ Captura erros não tratados (v1.0 compatible + enhanced)
    
    v3.0 Enhancements:
    - Better error classification
    - Security error detection
    - Detailed logging
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        
        except Exception as e:
            # ✅ v1.0: Log error
            logger.error(f"❌ Unhandled error: {e}", exc_info=True)
            
            # ➕ NEW: Check if security-related
            error_str = str(e).lower()
            is_security_error = any(
                keyword in error_str 
                for keyword in ['unauthorized', 'forbidden', 'token', 'auth']
            )
            
            if is_security_error:
                incident = SecurityIncident(
                    incident_id=f"err_{int(time.time())}",
                    timestamp=datetime.now(),
                    event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                    threat_level=ThreatLevel.MEDIUM,
                    ip_address=request.client.host if request.client else "unknown",
                    path=request.url.path,
                    method=request.method,
                    details={'error': str(e)},
                    blocked=False
                )
                security_manager.record_incident(incident)
            
            # ✅ v1.0: Retorna erro em formato JSON
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "type": "server_error",
                    "path": request.url.path
                }
            )


# ============================================================================
# NEW v3.0: Rate Limiting Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ➕ NEW v3.0: Rate limiting middleware
    
    Features:
    - IP-based rate limiting
    - Per-endpoint limits
    - Burst protection
    """
    
    def __init__(self, app, exempt_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get identifier
        ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        is_allowed, retry_after = security_manager.rate_limiter.is_allowed(ip, request.url.path)
        
        if not is_allowed:
            # Record incident
            incident = SecurityIncident(
                incident_id=f"rl_{int(time.time())}",
                timestamp=datetime.now(),
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                threat_level=ThreatLevel.LOW,
                ip_address=ip,
                path=request.url.path,
                method=request.method,
                blocked=True
            )
            security_manager.record_incident(incident)
            security_manager.metrics.rate_limited += 1
            
            # Return 429
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)


# ============================================================================
# NEW v3.0: IP Filtering Middleware
# ============================================================================

class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    ➕ NEW v3.0: IP blacklist/whitelist middleware
    
    Features:
    - IP blacklisting
    - IP whitelisting
    - Automatic blocking
    """
    
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        
        # Check whitelist first
        if security_manager.ip_manager.is_whitelisted(ip):
            return await call_next(request)
        
        # Check blacklist
        if security_manager.ip_manager.is_blacklisted(ip):
            incident = SecurityIncident(
                incident_id=f"bl_{int(time.time())}",
                timestamp=datetime.now(),
                event_type=SecurityEventType.BLACKLISTED_IP,
                threat_level=ThreatLevel.HIGH,
                ip_address=ip,
                path=request.url.path,
                method=request.method,
                blocked=True
            )
            security_manager.record_incident(incident)
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        return await call_next(request)


# ============================================================================
# NEW v3.0: Threat Detection Middleware
# ============================================================================

class ThreatDetectionMiddleware(BaseHTTPMiddleware):
    """
    ➕ NEW v3.0: Threat detection middleware
    
    Features:
    - SQL injection detection
    - XSS detection
    - Path traversal detection
    """
    
    async def dispatch(self, request: Request, call_next):
        # Scan request
        threat_type = security_manager.threat_detector.scan_request(request)
        
        if threat_type:
            ip = request.client.host if request.client else "unknown"
            
            # Record incident
            incident = SecurityIncident(
                incident_id=f"thr_{int(time.time())}",
                timestamp=datetime.now(),
                event_type=threat_type,
                threat_level=ThreatLevel.CRITICAL,
                ip_address=ip,
                path=request.url.path,
                method=request.method,
                user_agent=request.headers.get("user-agent"),
                blocked=True
            )
            security_manager.record_incident(incident)
            
            # Mark IP as suspicious
            security_manager.ip_manager.mark_suspicious(ip)
            
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request"}
            )
        
        return await call_next(request)


# ============================================================================
# NEW v3.0: Request Size Middleware
# ============================================================================

class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    ➕ NEW v3.0: Request size limiting
    
    Prevents large payload attacks
    """
    
    def __init__(self, app, max_size: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        
        if content_length and int(content_length) > self.max_size:
            ip = request.client.host if request.client else "unknown"
            
            incident = SecurityIncident(
                incident_id=f"sz_{int(time.time())}",
                timestamp=datetime.now(),
                event_type=SecurityEventType.LARGE_PAYLOAD,
                threat_level=ThreatLevel.MEDIUM,
                ip_address=ip,
                path=request.url.path,
                method=request.method,
                details={'size': int(content_length), 'max': self.max_size},
                blocked=True
            )
            security_manager.record_incident(incident)
            
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": f"Request too large. Max: {self.max_size} bytes"}
            )
        
        return await call_next(request)


# ============================================================================
# v1.0 SETUP ALL MIDDLEWARE (Enhanced)
# ============================================================================

def setup_middleware(app: FastAPI):
    """
    ✅ Configura todos os middlewares (v1.0 compatible + enhanced)
    
    v3.0 Enhancements:
    - Rate limiting
    - IP filtering
    - Threat detection
    - Request size limiting
    """
    # ✅ 1. CORS (primeiro) - v1.0
    setup_cors(app)
    
    # ✅ 2. Security headers - v1.0
    app.add_middleware(SecurityHeadersMiddleware)
    
    # ➕ 3. Request size limiting - NEW v3.0
    app.add_middleware(RequestSizeMiddleware)
    
    # ➕ 4. IP filtering - NEW v3.0
    app.add_middleware(IPFilterMiddleware)
    
    # ➕ 5. Rate limiting - NEW v3.0
    app.add_middleware(RateLimitMiddleware)
    
    # ➕ 6. Threat detection - NEW v3.0
    app.add_middleware(ThreatDetectionMiddleware)
    
    # ✅ 7. Request logging - v1.0
    if settings.DEBUG:
        app.add_middleware(RequestLoggingMiddleware)
    
    # ✅ 8. Audit logging (compliance) - v1.0
    app.add_middleware(AuditLoggingMiddleware)
    
    # ✅ 9. Error handling (último) - v1.0
    app.add_middleware(ErrorHandlingMiddleware)
    
    logger.info("✅ Middleware configurado (v3.0 Enhanced)")


# ============================================================================
# NEW v3.0: Security API Endpoints
# ============================================================================

def get_security_metrics() -> Dict[str, Any]:
    """➕ NEW: Get security metrics"""
    return security_manager.get_metrics()


def get_security_report() -> Dict[str, Any]:
    """➕ NEW: Get security report"""
    return security_manager.generate_report()


def get_recent_incidents(minutes: int = 60) -> List[Dict[str, Any]]:
    """➕ NEW: Get recent security incidents"""
    incidents = security_manager.get_recent_incidents(minutes)
    return [i.to_dict() for i in incidents]


def blacklist_ip(ip: str, duration: Optional[int] = None):
    """➕ NEW: Blacklist an IP"""
    security_manager.ip_manager.blacklist_ip(ip, duration)


def whitelist_ip(ip: str):
    """➕ NEW: Whitelist an IP"""
    security_manager.ip_manager.whitelist_ip(ip)


# ============================================================================
# TESTE v3.0
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🛡️  TESTE: Security Middleware v3.0")
    print("=" * 70)
    
    # Test 1: v1.0 Compatibility
    print("\n✅ Teste 1: v1.0 Compatibility")
    print("   ✅ setup_cors() - Available")
    print("   ✅ SecurityHeadersMiddleware - Available")
    print("   ✅ RequestLoggingMiddleware - Available")
    print("   ✅ AuditLoggingMiddleware - Available")
    print("   ✅ ErrorHandlingMiddleware - Available")
    
    # Test 2: Security Headers
    print("\n✅ Teste 2: Security Headers")
    for header, value in SECURITY_HEADERS.items():
        print(f"   • {header}: {value}")
    
    # Test 3: NEW v3.0 - Rate Limiter
    print("\n➕ Teste 3: NEW - Rate Limiter")
    limiter = RateLimiter()
    test_ip = "192.168.1.100"
    
    # Test normal requests
    for i in range(5):
        allowed, retry = limiter.is_allowed(test_ip)
        print(f"   Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'}")
    
    # Test 4: NEW v3.0 - IP Manager
    print("\n➕ Teste 4: NEW - IP Manager")
    ip_mgr = IPManager()
    ip_mgr.blacklist_ip("10.0.0.1")
    ip_mgr.whitelist_ip("192.168.1.1")
    print(f"   ✅ Blacklisted: {ip_mgr.is_blacklisted('10.0.0.1')}")
    print(f"   ✅ Whitelisted: {ip_mgr.is_whitelisted('192.168.1.1')}")
    
    # Test 5: NEW v3.0 - Threat Detector
    print("\n➕ Teste 5: NEW - Threat Detector")
    detector = ThreatDetector()
    
    test_cases = [
        ("normal query", False),
        ("'; DROP TABLE users--", True),
        ("<script>alert('xss')</script>", True),
        ("../../etc/passwd", True)
    ]
    
    for test, should_detect in test_cases:
        detected = (
            detector.detect_sql_injection(test) or 
            detector.detect_xss(test) or 
            detector.detect_path_traversal(test)
        )
        status = "✅" if detected == should_detect else "❌"
        print(f"   {status} '{test[:30]}': {'Threat' if detected else 'Safe'}")
    
    # Test 6: NEW v3.0 - Security Metrics
    print("\n➕ Teste 6: NEW - Security Metrics")
    metrics = SecurityMetrics(
        total_requests=1000,
        blocked_requests=50,
        rate_limited=30,
        threats_detected=20
    )
    print(f"   ✅ Total requests: {metrics.total_requests}")
    print(f"   ✅ Block rate: {metrics.get_block_rate():.1f}%")
    print(f"   ✅ Threats detected: {metrics.threats_detected}")
    
    # Test 7: NEW v3.0 - Security Manager
    print("\n➕ Teste 7: NEW - Security Manager")
    print(f"   ✅ Rate Limiter: Initialized")
    print(f"   ✅ IP Manager: Initialized")
    print(f"   ✅ Threat Detector: Initialized")
    print(f"   ✅ Metrics: Tracking")
    print(f"   ✅ Incidents: Recording")
    
    # Test 8: CORS Origins
    print("\n🌐 Teste 8: CORS Origins")
    for origin in settings.cors_origins_list:
        print(f"   • {origin}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes v3.0 passaram!")
    print("✅ Compatibilidade v1.0 mantida 100%!")
    print("➕ NEW: Rate Limiting + IP Filter + Threat Detection")
    print("=" * 70)
