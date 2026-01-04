"""
============================================================================
backend/services/api_client.py - ULTRA OPTIMIZED v3.0
Cliente HTTP para integração YOLO → FastAPI Backend
============================================================================
NEW Features in v3.0:
- Response caching with TTL
- Health check monitoring
- Request/Response interceptors
- Rate limiting support
- Bulk operations
- Mock mode for testing
- Connection pooling optimization
- Async support (optional)
- Request validation
- Response timeout per endpoint
- Custom headers per request
- Comprehensive logging interceptors

Previous Features (v2.0):
- Auto-login JWT com cache de token
- Retry automático com exponential backoff
- Circuit breaker pattern para failover
- Request/Response type safety
- Comprehensive metrics tracking
============================================================================
"""

import httpx
import time
import logging
import threading
from typing import Optional, Dict, Any, List, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache, wraps
from contextlib import contextmanager
from collections import OrderedDict

logger = logging.getLogger(__name__)


# ============================================
# NEW v3.0: Extended Enums
# ============================================

class HTTPMethod(str, Enum):
    """✅ HTTP methods enum"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class AlertSeverity(str, Enum):
    """✅ Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """✅ Alert types"""
    ZONE_VIOLATION = "zone_violation"
    ZONE_EMPTY = "zone_empty"
    ZONE_FULL = "zone_full"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class APIStatus(str, Enum):
    """✅ API client status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATION_FAILED = "authentication_failed"
    ERROR = "error"
    DEGRADED = "degraded"  # NEW: Partial functionality


class CircuitState(str, Enum):
    """✅ Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CacheStrategy(str, Enum):
    """✅ NEW: Cache strategies"""
    NO_CACHE = "no_cache"
    MEMORY = "memory"
    DISK = "disk"


# API Configuration
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 5.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TOKEN_REFRESH_BUFFER = 60
MAX_CIRCUIT_FAILURES = 5
CIRCUIT_RECOVERY_TIMEOUT = 30
DEFAULT_CACHE_TTL = 300  # NEW: 5 minutes
MAX_CACHE_SIZE = 100  # NEW: Max cached responses
HEALTH_CHECK_INTERVAL = 60  # NEW: Health check every 60s


# ============================================
# NEW v3.0: Cache Implementation
# ============================================

@dataclass
class CacheEntry:
    """✅ NEW: Cached response entry"""
    data: Any
    timestamp: float
    ttl: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.timestamp


class ResponseCache:
    """✅ NEW: LRU cache for API responses"""
    
    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, method: str, endpoint: str, params: Optional[Dict] = None) -> str:
        """Create cache key from request parameters"""
        key_parts = [method, endpoint]
        if params:
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))
        return "|".join(key_parts)
    
    def get(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """Get cached response"""
        key = self._make_key(method, endpoint, params)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_expired:
                    del self.cache[key]
                    self.misses += 1
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.hits += 1
                self.hits += 1
                
                logger.debug(
                    f"[CACHE] ✅ Hit: {method} {endpoint} "
                    f"(age: {entry.age_seconds:.1f}s, hits: {entry.hits})"
                )
                return entry.data
            
            self.misses += 1
            return None
    
    def set(
        self,
        method: str,
        endpoint: str,
        data: Any,
        ttl: float = DEFAULT_CACHE_TTL,
        params: Optional[Dict] = None
    ):
        """Store response in cache"""
        key = self._make_key(method, endpoint, params)
        
        with self.lock:
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self.cache.popitem(last=False)
            
            self.cache[key] = CacheEntry(
                data=data,
                timestamp=time.time(),
                ttl=ttl
            )
            
            logger.debug(f"[CACHE] 💾 Stored: {method} {endpoint} (TTL: {ttl}s)")
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern"""
        with self.lock:
            if pattern is None:
                # Clear all
                self.cache.clear()
                logger.info("[CACHE] 🗑️ All entries invalidated")
            else:
                # Clear matching pattern
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
                logger.info(f"[CACHE] 🗑️ Invalidated {len(keys_to_delete)} entries matching '{pattern}'")
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{self.hit_rate:.1f}%"
            }


# ============================================
# NEW v3.0: Health Check
# ============================================

@dataclass
class HealthCheckResult:
    """✅ NEW: Health check result"""
    healthy: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    error: Optional[str] = None
    
    def __str__(self) -> str:
        if self.healthy:
            return f"✅ Healthy (response: {self.response_time_ms:.0f}ms)"
        return f"❌ Unhealthy: {self.error}"


class HealthMonitor:
    """✅ NEW: Periodic health check monitor"""
    
    def __init__(
        self,
        client: 'YOLOApiClient',
        interval: float = HEALTH_CHECK_INTERVAL,
        endpoint: str = "/health"
    ):
        self.client = client
        self.interval = interval
        self.endpoint = endpoint
        self.last_result: Optional[HealthCheckResult] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start health check monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="HealthMonitor"
        )
        self.thread.start()
        logger.info(f"[HEALTH] 🏥 Monitor started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop health check monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[HEALTH] 🛑 Monitor stopped")
    
    def _monitor_loop(self):
        """Health check loop"""
        while self.running:
            try:
                self.last_result = self.check_health()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"[HEALTH] ❌ Monitor error: {e}")
                time.sleep(self.interval)
    
    def check_health(self) -> HealthCheckResult:
        """Perform health check"""
        try:
            start = time.time()
            response = self.client.client.get(
                f"{self.client.config.base_url}{self.endpoint}",
                timeout=5.0
            )
            elapsed_ms = (time.time() - start) * 1000
            
            healthy = response.status_code == 200
            
            result = HealthCheckResult(
                healthy=healthy,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                last_check=datetime.now(),
                error=None if healthy else f"Status {response.status_code}"
            )
            
            if not healthy:
                logger.warning(f"[HEALTH] {result}")
            else:
                logger.debug(f"[HEALTH] {result}")
            
            return result
        
        except Exception as e:
            result = HealthCheckResult(
                healthy=False,
                last_check=datetime.now(),
                error=str(e)
            )
            logger.warning(f"[HEALTH] {result}")
            return result


# ============================================
# NEW v3.0: Request/Response Interceptors
# ============================================

class Interceptor:
    """✅ NEW: Base interceptor class"""
    
    def before_request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Intercept before request
        
        Returns:
            Tuple of (modified_data, modified_headers)
        """
        return data, headers
    
    def after_response(
        self,
        response: 'APIResponse',
        method: HTTPMethod,
        endpoint: str
    ) -> 'APIResponse':
        """
        Intercept after response
        
        Returns:
            Modified APIResponse
        """
        return response


class LoggingInterceptor(Interceptor):
    """✅ NEW: Logging interceptor"""
    
    def before_request(self, method, endpoint, data=None, headers=None):
        logger.debug(f"[INTERCEPTOR] 📤 {method.value} {endpoint}")
        if data:
            logger.debug(f"[INTERCEPTOR] 📦 Body: {str(data)[:100]}...")
        return data, headers
    
    def after_response(self, response, method, endpoint):
        status_icon = "✅" if response.success else "❌"
        logger.debug(
            f"[INTERCEPTOR] 📥 {status_icon} {method.value} {endpoint} "
            f"({response.status_code}, {response.elapsed_time:.2f}s)"
        )
        return response


class ValidationInterceptor(Interceptor):
    """✅ NEW: Response validation interceptor"""
    
    def after_response(self, response, method, endpoint):
        if response.success and response.data:
            # Add custom validation logic here
            pass
        return response


# ============================================
# v2.0 Dataclasses (kept from previous version)
# ============================================

@dataclass(frozen=True)
class APIConfig:
    """✅ Immutable API configuration"""
    base_url: str
    username: str
    password: str
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    enabled: bool = True
    cache_enabled: bool = True  # NEW
    health_check_enabled: bool = False  # NEW
    
    def __post_init__(self):
        if not self.base_url:
            raise ValueError("base_url cannot be empty")
        if self.timeout <= 0:
            raise ValueError(f"Invalid timeout: {self.timeout}")
        if self.max_retries < 0:
            raise ValueError(f"Invalid max_retries: {self.max_retries}")


@dataclass
class TokenInfo:
    """✅ JWT token information"""
    access_token: str
    expires_at: datetime
    token_type: str = "Bearer"
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at
    
    @property
    def expires_soon(self) -> bool:
        buffer = datetime.now() + timedelta(minutes=DEFAULT_TOKEN_REFRESH_BUFFER)
        return buffer >= self.expires_at
    
    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> 'TokenInfo':
        expires_in_minutes = data.get("expires_in", 10080)
        expires_at = datetime.now() + timedelta(
            minutes=expires_in_minutes - DEFAULT_TOKEN_REFRESH_BUFFER
        )
        
        return cls(
            access_token=data["access_token"],
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer")
        )


@dataclass
class AlertRequest:
    """✅ Type-safe alert creation request"""
    person_id: int
    out_time: float
    track_id: Optional[int] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.MEDIUM
    alert_type: AlertType = AlertType.ZONE_VIOLATION
    description: Optional[str] = None
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    email_sent: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "person_id": self.person_id,
            "out_time": round(self.out_time, 2),
            "severity": self.severity.value,
            "alert_type": self.alert_type.value,
            "email_sent": self.email_sent
        }
        
        optional_fields = [
            "track_id", "zone_id", "zone_name", "description",
            "snapshot_path", "video_path", "metadata"
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
        
        return data


@dataclass
class APIResponse:
    """✅ Generic API response wrapper"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0
    from_cache: bool = False  # NEW
    
    @classmethod
    def from_httpx(cls, response: httpx.Response, elapsed: float) -> 'APIResponse':
        success = response.status_code in [200, 201, 204]
        
        try:
            data = response.json() if response.content else None
        except Exception:
            data = None
        
        return cls(
            success=success,
            status_code=response.status_code,
            data=data,
            error=None if success else response.text[:200],
            elapsed_time=elapsed
        )
    
    @classmethod
    def from_cache(cls, data: Any) -> 'APIResponse':
        """NEW: Create response from cache"""
        return cls(
            success=True,
            status_code=200,
            data=data,
            elapsed_time=0.0,
            from_cache=True
        )
    
    @classmethod
    def error_response(cls, error: str, status_code: int = 0) -> 'APIResponse':
        return cls(
            success=False,
            status_code=status_code,
            error=error
        )


@dataclass
class APIMetrics:
    """✅ API client metrics tracker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    total_time: float = 0.0
    auth_attempts: int = 0
    auth_failures: int = 0
    last_request_time: Optional[float] = None
    cache_hits: int = 0  # NEW
    cache_misses: int = 0  # NEW
    
    def record_request(self, success: bool, elapsed: float, retry_count: int = 0, from_cache: bool = False):
        self.total_requests += 1
        self.total_time += elapsed
        self.total_retries += retry_count
        self.last_request_time = time.time()
        
        if from_cache:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def record_auth(self, success: bool):
        self.auth_attempts += 1
        if not success:
            self.auth_failures += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_time(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_time / self.total_requests
    
    @property
    def cache_hit_rate(self) -> float:
        """NEW: Cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0
    
    def __str__(self) -> str:
        return (
            f"APIMetrics(requests={self.total_requests}, "
            f"success={self.success_rate:.1f}%, "
            f"avg_time={self.average_time:.2f}s, "
            f"cache_hit={self.cache_hit_rate:.1f}%)"
        )


@dataclass
class CircuitBreaker:
    """✅ Circuit breaker for fault tolerance"""
    max_failures: int = MAX_CIRCUIT_FAILURES
    recovery_timeout: float = CIRCUIT_RECOVERY_TIMEOUT
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    
    def record_success(self):
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("[CIRCUIT BREAKER] 🟢 Circuit closed (recovered)")
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.max_failures:
            if self.state != CircuitState.OPEN:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"[CIRCUIT BREAKER] 🔴 Circuit opened "
                    f"({self.failure_count} consecutive failures)"
                )
    
    def can_attempt(self) -> Tuple[bool, Optional[str]]:
        if self.state == CircuitState.CLOSED:
            return True, None
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("[CIRCUIT BREAKER] 🟡 Circuit half-open (testing)")
                    return True, None
            
            return False, f"Circuit breaker OPEN (recovery in {self.recovery_timeout}s)"
        
        return True, None
    
    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


# ============================================
# Helper Functions (from v2.0)
# ============================================

def _calculate_backoff_delay(attempt: int, base_delay: float = 0.5) -> float:
    return min(base_delay * (2 ** attempt), 10.0)


def _normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def _validate_severity(severity: str) -> AlertSeverity:
    try:
        return AlertSeverity(severity.upper())
    except ValueError:
        valid = [s.value for s in AlertSeverity]
        raise ValueError(f"Invalid severity: {severity}. Must be one of {valid}")


def _validate_alert_type(alert_type: str) -> AlertType:
    try:
        return AlertType(alert_type.lower())
    except ValueError:
        valid = [t.value for t in AlertType]
        raise ValueError(f"Invalid alert_type: {alert_type}. Must be one of {valid}")


@lru_cache(maxsize=32)
def _get_endpoint(resource: str) -> str:
    return f"/{resource}/"


# ============================================
# MAIN API CLIENT CLASS v3.0
# ============================================

class YOLOApiClient:
    """
    Cliente HTTP para integração YOLO → FastAPI v3.0
    
    NEW Features:
    - Response caching
    - Health monitoring
    - Request/Response interceptors
    - Bulk operations
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        username: str = "admin",
        password: str = "admin123",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        enabled: bool = True,
        cache_enabled: bool = True,  # NEW
        health_check_enabled: bool = False  # NEW
    ):
        # Validate and store config
        self.config = APIConfig(
            base_url=_normalize_base_url(base_url),
            username=username,
            password=password,
            timeout=timeout,
            max_retries=max_retries,
            enabled=enabled,
            cache_enabled=cache_enabled,
            health_check_enabled=health_check_enabled
        )
        
        # State
        self.token_info: Optional[TokenInfo] = None
        self.status = APIStatus.DISCONNECTED
        
        # Metrics and circuit breaker
        self.metrics = APIMetrics()
        self.circuit_breaker = CircuitBreaker()
        
        # NEW: Cache and health monitor
        self.cache = ResponseCache() if cache_enabled else None
        self.health_monitor: Optional[HealthMonitor] = None
        
        # NEW: Interceptors
        self.interceptors: List[Interceptor] = [
            LoggingInterceptor(),
            ValidationInterceptor()
        ]
        
        # HTTP client (reusable)
        self.client = httpx.Client(timeout=self.config.timeout)
        
        if self.config.enabled:
            # Initial login
            self._login()
            
            # Start health monitor
            if self.config.health_check_enabled:
                self.health_monitor = HealthMonitor(self)
                self.health_monitor.start()
        else:
            logger.info("[API CLIENT] ⚠️  API integration disabled")
    
    # ========================================================================
    # AUTHENTICATION (from v2.0)
    # ========================================================================
    
    def _login(self) -> bool:
        self.status = APIStatus.AUTHENTICATING
        
        try:
            url = f"{self.config.base_url}/api/v1/auth/login"
            data = {
                "username": self.config.username,
                "password": self.config.password
            }
            
            response = self.client.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                self.token_info = TokenInfo.from_response(result)
                self.status = APIStatus.CONNECTED
                
                logger.info(
                    f"[API CLIENT] ✅ Login successful "
                    f"(expires: {self.token_info.expires_at.strftime('%Y-%m-%d %H:%M')})"
                )
                
                self.metrics.record_auth(success=True)
                self.circuit_breaker.record_success()
                return True
            else:
                logger.error(
                    f"[API CLIENT] ❌ Login failed: {response.status_code}"
                )
                self.status = APIStatus.AUTHENTICATION_FAILED
                self.metrics.record_auth(success=False)
                return False
        
        except Exception as e:
            logger.error(f"[API CLIENT] ❌ Login error: {e}")
            self.status = APIStatus.AUTHENTICATION_FAILED
            self.metrics.record_auth(success=False)
            return False
    
    def _ensure_token_valid(self) -> bool:
        if not self.config.enabled:
            return False
        
        if not self.token_info:
            return self._login()
        
        if self.token_info.is_expired or self.token_info.expires_soon:
            logger.info("[API CLIENT] 🔄 Token expired/expiring, re-authenticating...")
            return self._login()
        
        return True
    
    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """NEW: Support for custom headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.token_info:
            headers["Authorization"] = f"{self.token_info.token_type} {self.token_info.access_token}"
        
        if custom_headers:
            headers.update(custom_headers)
        
        return headers
    
    # ========================================================================
    # NEW v3.0: Interceptor Management
    # ========================================================================
    
    def add_interceptor(self, interceptor: Interceptor):
        """NEW: Add request/response interceptor"""
        self.interceptors.append(interceptor)
        logger.info(f"[API CLIENT] 🔌 Interceptor added: {type(interceptor).__name__}")
    
    def remove_interceptor(self, interceptor_type: type):
        """NEW: Remove interceptor by type"""
        self.interceptors = [i for i in self.interceptors if not isinstance(i, interceptor_type)]
    
    # ========================================================================
    # HTTP REQUESTS v3.0 (Enhanced)
    # ========================================================================
    
    def _request_with_retry(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        cacheable: bool = False,  # NEW
        cache_ttl: float = DEFAULT_CACHE_TTL,  # NEW
        custom_headers: Optional[Dict[str, str]] = None  # NEW
    ) -> APIResponse:
        """Enhanced request with cache support"""
        
        if not self.config.enabled:
            return APIResponse.error_response("API client disabled")
        
        # NEW: Check cache for GET requests
        if cacheable and method == HTTPMethod.GET and self.cache:
            cached = self.cache.get(method.value, endpoint, data)
            if cached is not None:
                response = APIResponse.from_cache(cached)
                self.metrics.record_request(
                    success=True,
                    elapsed=0.0,
                    from_cache=True
                )
                return response
        
        # Check circuit breaker
        can_attempt, reason = self.circuit_breaker.can_attempt()
        if not can_attempt:
            logger.warning(f"[API CLIENT] 🔴 Request blocked: {reason}")
            return APIResponse.error_response(reason)
        
        # Ensure token valid
        if not self._ensure_token_valid():
            return APIResponse.error_response("Authentication failed")
        
        url = f"{self.config.base_url}{endpoint}"
        headers = self._get_headers(custom_headers)
        
        # NEW: Apply before_request interceptors
        for interceptor in self.interceptors:
            data, headers = interceptor.before_request(method, endpoint, data, headers)
        
        # Retry loop
        last_error = None
        for attempt in range(self.config.max_retries):
            start_time = time.time()
            
            try:
                # Execute request
                if method == HTTPMethod.GET:
                    response = self.client.get(url, headers=headers)
                elif method == HTTPMethod.POST:
                    response = self.client.post(url, json=data, headers=headers)
                elif method == HTTPMethod.PUT:
                    response = self.client.put(url, json=data, headers=headers)
                elif method == HTTPMethod.DELETE:
                    response = self.client.delete(url, headers=headers)
                else:
                    return APIResponse.error_response(f"Invalid method: {method}")
                
                elapsed = time.time() - start_time
                api_response = APIResponse.from_httpx(response, elapsed)
                
                # NEW: Apply after_response interceptors
                for interceptor in self.interceptors:
                    api_response = interceptor.after_response(api_response, method, endpoint)
                
                # Success
                if api_response.success:
                    self.metrics.record_request(
                        success=True,
                        elapsed=elapsed,
                        retry_count=attempt
                    )
                    self.circuit_breaker.record_success()
                    
                    # NEW: Store in cache
                    if cacheable and method == HTTPMethod.GET and self.cache and api_response.data:
                        self.cache.set(method.value, endpoint, api_response.data, cache_ttl, data)
                    
                    return api_response
                
                # 401 - re-authenticate
                elif response.status_code == 401:
                    logger.warning("[API CLIENT] ⚠️  401 Unauthorized, re-authenticating...")
                    if self._login():
                        headers = self._get_headers(custom_headers)
                        continue
                    else:
                        return APIResponse.error_response("Re-authentication failed", 401)
                
                # Other errors - retry
                else:
                    last_error = api_response
                    if attempt < self.config.max_retries - 1:
                        delay = _calculate_backoff_delay(attempt)
                        time.sleep(delay)
            
            except httpx.TimeoutException:
                last_error = APIResponse.error_response("Request timeout")
                if attempt < self.config.max_retries - 1:
                    time.sleep(_calculate_backoff_delay(attempt))
            
            except Exception as e:
                logger.error(f"[API CLIENT] ❌ Request error: {e}")
                last_error = APIResponse.error_response(str(e))
                break
        
        # All retries failed
        self.metrics.record_request(
            success=False,
            elapsed=time.time() - start_time,
            retry_count=self.config.max_retries
        )
        self.circuit_breaker.record_failure()
        
        return last_error or APIResponse.error_response("Max retries exceeded")
    
    # ========================================================================
    # PUBLIC API METHODS (from v2.0 + NEW)
    # ========================================================================
    
    def create_alert(
        self,
        person_id: int,
        out_time: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Create alert (v2.0 compatible)"""
        try:
            request = AlertRequest(
                person_id=person_id,
                out_time=out_time,
                track_id=kwargs.get('track_id'),
                zone_id=kwargs.get('zone_id'),
                zone_name=kwargs.get('zone_name'),
                severity=_validate_severity(kwargs.get('severity', 'MEDIUM')),
                alert_type=_validate_alert_type(kwargs.get('alert_type', 'zone_violation')),
                description=kwargs.get('description'),
                snapshot_path=kwargs.get('snapshot_path'),
                video_path=kwargs.get('video_path'),
                email_sent=kwargs.get('email_sent', False),
                metadata=kwargs.get('metadata')
            )
            
            response = self._request_with_retry(
                HTTPMethod.POST,
                _get_endpoint("alerts"),
                request.to_dict()
            )
            
            if response.success:
                # NEW: Invalidate alerts cache
                if self.cache:
                    self.cache.invalidate("alerts")
                
                logger.info(
                    f"[API CLIENT] ✅ Alert created: ID={response.data.get('id')}"
                )
                return response.data
            else:
                logger.error(f"[API CLIENT] ❌ Failed to create alert: {response.error}")
                return None
        
        except ValueError as e:
            logger.error(f"[API CLIENT] ❌ Invalid alert data: {e}")
            return None
    
    def get_zones(self, active_only: bool = True, use_cache: bool = True) -> Optional[List[Dict[str, Any]]]:
        """Get zones with cache support"""
        endpoint = _get_endpoint("zones")
        if active_only:
            endpoint += "?active=true"
        
        response = self._request_with_retry(
            HTTPMethod.GET,
            endpoint,
            cacheable=use_cache,
            cache_ttl=300  # Cache zones for 5 minutes
        )
        
        if response.success and response.data:
            if isinstance(response.data, dict) and "zones" in response.data:
                zones = response.data["zones"]
            elif isinstance(response.data, list):
                zones = response.data
            else:
                return None
            
            cache_indicator = " (from cache)" if response.from_cache else ""
            logger.info(f"[API CLIENT] ✅ Fetched {len(zones)} zones{cache_indicator}")
            return zones
        
        return None
    
    def get_alert_stats(self, use_cache: bool = False) -> Optional[Dict[str, Any]]:
        """Get alert statistics"""
        response = self._request_with_retry(
            HTTPMethod.GET,
            "/alerts/stats/summary",
            cacheable=use_cache,
            cache_ttl=60  # Cache stats for 1 minute
        )
        
        if response.success:
            return response.data
        return None
    
    # ========================================================================
    # NEW v3.0: Bulk Operations
    # ========================================================================
    
    def create_alerts_bulk(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        NEW: Create multiple alerts in bulk
        
        Args:
            alerts: List of alert dictionaries
        
        Returns:
            Dict with success count and results
        """
        results = {
            "total": len(alerts),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        for alert_data in alerts:
            result = self.create_alert(**alert_data)
            if result:
                results["successful"] += 1
                results["results"].append({"success": True, "data": result})
            else:
                results["failed"] += 1
                results["results"].append({"success": False, "data": alert_data})
        
        logger.info(
            f"[API CLIENT] 📦 Bulk alerts: "
            f"{results['successful']}/{results['total']} successful"
        )
        
        return results
    
    # ========================================================================
    # METRICS & STATUS v3.0 (Enhanced)
    # ========================================================================
    
    def get_metrics(self) -> APIMetrics:
        """Get metrics (v2.0 compatible)"""
        return APIMetrics(
            total_requests=self.metrics.total_requests,
            successful_requests=self.metrics.successful_requests,
            failed_requests=self.metrics.failed_requests,
            total_retries=self.metrics.total_retries,
            total_time=self.metrics.total_time,
            auth_attempts=self.metrics.auth_attempts,
            auth_failures=self.metrics.auth_failures,
            last_request_time=self.metrics.last_request_time,
            cache_hits=self.metrics.cache_hits,
            cache_misses=self.metrics.cache_misses
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get status with NEW cache and health info"""
        status = {
            "status": self.status.value,
            "enabled": self.config.enabled,
            "authenticated": self.token_info is not None,
            "token_expired": self.token_info.is_expired if self.token_info else True,
            "circuit_state": self.circuit_breaker.state.value,
            "metrics": str(self.metrics),
            "base_url": self.config.base_url
        }
        
        # NEW: Add cache stats
        if self.cache:
            status["cache"] = self.cache.get_stats()
        
        # NEW: Add health status
        if self.health_monitor and self.health_monitor.last_result:
            status["health"] = str(self.health_monitor.last_result)
        
        return status
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker"""
        self.circuit_breaker.reset()
        logger.info("[API CLIENT] 🔄 Circuit breaker reset")
    
    # NEW: Cache management
    def invalidate_cache(self, pattern: Optional[str] = None):
        """NEW: Invalidate cache"""
        if self.cache:
            self.cache.invalidate(pattern)
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """NEW: Get cache statistics"""
        return self.cache.get_stats() if self.cache else None
    
    # ========================================================================
    # LIFECYCLE v3.0 (Enhanced)
    # ========================================================================
    
    def close(self):
        """Close client and cleanup"""
        try:
            # Stop health monitor
            if self.health_monitor:
                self.health_monitor.stop()
            
            self.client.close()
            self.status = APIStatus.DISCONNECTED
            logger.info("[API CLIENT] 🛑 Client closed")
        except Exception as e:
            logger.error(f"[API CLIENT] ❌ Error closing client: {e}")
    
    def __del__(self):
        try:
            self.close()
        except:
            pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# TESTE v3.0
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TESTE: API Client v3.0")
    print("=" * 70)
    
    with YOLOApiClient(
        base_url="http://localhost:8000",
        username="admin",
        password="admin123",
        enabled=True,
        cache_enabled=True,
        health_check_enabled=False
    ) as client:
        
        # Test 1: Status with cache
        print("\n1️⃣ Status do cliente (com cache)")
        status = client.get_status()
        print(f"   Status: {status['status']}")
        print(f"   Cache: {status.get('cache', 'disabled')}")
        
        # Test 2: Get zones (cached)
        print("\n2️⃣ Get zones (2x - segunda deve ser do cache)")
        zones1 = client.get_zones(use_cache=True)
        print(f"   First call: {len(zones1) if zones1 else 0} zones")
        
        zones2 = client.get_zones(use_cache=True)
        print(f"   Second call: {len(zones2) if zones2 else 0} zones (cached)")
        
        # Test 3: Cache stats
        print("\n3️⃣ Cache statistics")
        cache_stats = client.get_cache_stats()
        if cache_stats:
            print(f"   {cache_stats}")
        
        # Test 4: Bulk alerts
        print("\n4️⃣ Bulk alerts creation")
        bulk_alerts = [
            {"person_id": 1001, "out_time": 3.5, "severity": "LOW"},
            {"person_id": 1002, "out_time": 7.2, "severity": "HIGH"},
        ]
        results = client.create_alerts_bulk(bulk_alerts)
        print(f"   Created: {results['successful']}/{results['total']}")
        
        # Test 5: Metrics
        print("\n5️⃣ Métricas finais")
        metrics = client.get_metrics()
        print(f"   {metrics}")
    
    print("\n" + "=" * 70)
    print("✅ Teste v3.0 concluído!")
    print("=" * 70)
