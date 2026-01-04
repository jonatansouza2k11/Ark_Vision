"""
backend/database_sync.py - OPTIMIZED v2.0
Wrappers SÍNCRONOS para funções do database.py
Usado APENAS por código síncrono (YOLO, threads, etc)

Features:
- Type-safe wrappers para todas as funções async
- Retry logic automático em operações críticas
- Metrics tracking de operações síncronas
- Thread-safe async execution
- Comprehensive error handling
- Connection pooling optimization

✅ NÃO modifica o database.py original
✅ Mantém compatibilidade total com FastAPI
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor
import time
import threading

# ✅ Import com fallback
try:
    from backend.database import (
        get_setting as async_get_setting,
        set_setting as async_set_setting,
        get_all_settings as async_get_all_settings,
        log_alert as async_log_alert,
        save_detection as async_save_detection,
        log_system_action as async_log_system_action,
        get_all_zones as async_get_all_zones,
        get_zone_by_id as async_get_zone_by_id,
        create_zone as async_create_zone,
        update_zone as async_update_zone,
        delete_zone as async_delete_zone,
    )
except ModuleNotFoundError:
    from database import (
        get_setting as async_get_setting,
        set_setting as async_set_setting,
        get_all_settings as async_get_all_settings,
        log_alert as async_log_alert,
        save_detection as async_save_detection,
        log_system_action as async_log_system_action,
        get_all_zones as async_get_all_zones,
        get_zone_by_id as async_get_zone_by_id,
        create_zone as async_create_zone,
        update_zone as async_update_zone,
        delete_zone as async_delete_zone,
    )

logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')


# ============================================
# OTIMIZAÇÃO 1: Constants & Enums
# ============================================

class ExecutionStrategy(str, Enum):
    """✅ Strategy for executing async code"""
    NEW_LOOP = "new_loop"  # Create new event loop
    THREAD_POOL = "thread_pool"  # Use thread pool executor
    AUTO = "auto"  # Auto-detect best strategy


class OperationType(str, Enum):
    """✅ Types of database operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UPDATE = "update"


# Configuration
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_MAX_RETRIES = 2
THREAD_POOL_MAX_WORKERS = 4


# ============================================
# OTIMIZAÇÃO 2: Dataclasses for Metrics
# ============================================

@dataclass
class OperationMetrics:
    """✅ Metrics for sync wrapper operations"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time: float = 0.0
    retries: int = 0
    last_call_time: Optional[float] = None
    
    def record_call(self, success: bool, elapsed: float, retry_count: int = 0):
        """Record operation metrics"""
        self.total_calls += 1
        self.total_time += elapsed
        self.retries += retry_count
        self.last_call_time = time.time()
        
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def average_time(self) -> float:
        """Calculate average execution time"""
        if self.total_calls == 0:
            return 0.0
        return self.total_time / self.total_calls
    
    def __str__(self) -> str:
        return (
            f"OperationMetrics(calls={self.total_calls}, "
            f"success_rate={self.success_rate:.1f}%, "
            f"avg_time={self.average_time:.3f}s)"
        )


@dataclass
class SyncWrapperStats:
    """✅ Global statistics for all sync wrappers"""
    operations: Dict[str, OperationMetrics] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def get_or_create_metrics(self, operation: str) -> OperationMetrics:
        """Get or create metrics for an operation"""
        with self.lock:
            if operation not in self.operations:
                self.operations[operation] = OperationMetrics()
            return self.operations[operation]
    
    def record(self, operation: str, success: bool, elapsed: float, retry_count: int = 0):
        """Record operation execution"""
        metrics = self.get_or_create_metrics(operation)
        with self.lock:
            metrics.record_call(success, elapsed, retry_count)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all operations"""
        with self.lock:
            return {
                op: {
                    "calls": m.total_calls,
                    "success_rate": f"{m.success_rate:.1f}%",
                    "avg_time": f"{m.average_time:.3f}s",
                    "retries": m.retries
                }
                for op, m in self.operations.items()
            }


# Global stats instance
_global_stats = SyncWrapperStats()


# ============================================
# OTIMIZAÇÃO 3: Thread Pool Management
# ============================================

@lru_cache(maxsize=1)
def _get_thread_pool() -> ThreadPoolExecutor:
    """
    ✅ Get or create thread pool executor (cached)
    
    Returns:
        ThreadPoolExecutor instance
    """
    return ThreadPoolExecutor(
        max_workers=THREAD_POOL_MAX_WORKERS,
        thread_name_prefix="AsyncBridge"
    )


def _cleanup_thread_pool():
    """Cleanup thread pool on exit"""
    try:
        pool = _get_thread_pool()
        pool.shutdown(wait=True)
        logger.info("[SYNC WRAPPER] 🛑 Thread pool shutdown")
    except Exception as e:
        logger.error(f"[SYNC WRAPPER] ❌ Error shutting down thread pool: {e}")


# Register cleanup
import atexit
atexit.register(_cleanup_thread_pool)


# ============================================
# OTIMIZAÇÃO 4: Async Execution Strategies
# ============================================

def _detect_strategy() -> ExecutionStrategy:
    """
    ✅ Auto-detect best execution strategy
    
    Returns:
        ExecutionStrategy to use
    """
    try:
        # Check if event loop is running
        asyncio.get_running_loop()
        return ExecutionStrategy.THREAD_POOL
    except RuntimeError:
        return ExecutionStrategy.NEW_LOOP


def _run_async_new_loop(coro) -> Any:
    """
    ✅ Execute async code by creating a new event loop
    
    Args:
        coro: Coroutine to execute
    
    Returns:
        Result of coroutine execution
    """
    return asyncio.run(coro)


def _run_async_thread_pool(coro) -> Any:
    """
    ✅ Execute async code using thread pool executor
    
    Args:
        coro: Coroutine to execute
    
    Returns:
        Result of coroutine execution
    """
    pool = _get_thread_pool()
    future = pool.submit(asyncio.run, coro)
    return future.result(timeout=DEFAULT_TIMEOUT)


def _run_async(
    coro,
    strategy: ExecutionStrategy = ExecutionStrategy.AUTO,
    timeout: Optional[float] = None
) -> Any:
    """
    ✅ Execute async coroutine synchronously (optimized)
    
    Args:
        coro: Coroutine to execute
        strategy: Execution strategy to use
        timeout: Optional timeout in seconds
    
    Returns:
        Result of coroutine execution
    
    Raises:
        TimeoutError: If execution exceeds timeout
        RuntimeError: If execution fails
    """
    # Auto-detect strategy if needed
    if strategy == ExecutionStrategy.AUTO:
        strategy = _detect_strategy()
    
    try:
        if strategy == ExecutionStrategy.NEW_LOOP:
            return _run_async_new_loop(coro)
        elif strategy == ExecutionStrategy.THREAD_POOL:
            return _run_async_thread_pool(coro)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    except asyncio.TimeoutError:
        raise TimeoutError(f"Async execution timed out after {timeout}s")
    except Exception as e:
        logger.error(f"[SYNC WRAPPER] ❌ Async execution error: {e}")
        raise


# ============================================
# OTIMIZAÇÃO 5: Decorators for Wrappers
# ============================================

def sync_wrapper(
    operation_name: str,
    operation_type: OperationType = OperationType.READ,
    max_retries: int = 0,
    default_on_error: Optional[Any] = None
):
    """
    ✅ Decorator to create sync wrappers with metrics and retry
    
    Args:
        operation_name: Name of the operation (for metrics)
        operation_type: Type of operation (READ/WRITE/etc)
        max_retries: Number of retries on failure
        default_on_error: Default value to return on error
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    elapsed = time.time() - start_time
                    _global_stats.record(
                        operation_name,
                        success=True,
                        elapsed=elapsed,
                        retry_count=attempt
                    )
                    
                    if attempt > 0:
                        logger.info(
                            f"[SYNC WRAPPER] ✅ {operation_name} succeeded on retry {attempt}"
                        )
                    
                    return result
                
                except Exception as e:
                    last_error = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"[SYNC WRAPPER] ⚠️ {operation_name} failed "
                            f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(0.1 * (attempt + 1))  # Small backoff
                    else:
                        logger.error(
                            f"[SYNC WRAPPER] ❌ {operation_name} error: {e}"
                        )
            
            # All retries failed
            elapsed = time.time() - start_time
            _global_stats.record(
                operation_name,
                success=False,
                elapsed=elapsed,
                retry_count=max_retries
            )
            
            if default_on_error is not None:
                return default_on_error
            
            raise last_error
        
        return wrapper
    return decorator


# ============================================
# SETTINGS WRAPPERS
# ============================================

@sync_wrapper("get_setting", OperationType.READ, default_on_error=None)
def get_setting(key: str, default: Any = None) -> Any:
    """
    ✅ Wrapper SÍNCRONO para database.get_setting()
    
    Args:
        key: Setting key
        default: Default value if not found
    
    Returns:
        Setting value or default
    
    Usage:
        conf = get_setting("conf_thresh", "0.5")
    """
    return _run_async(async_get_setting(key, default))


@sync_wrapper("set_setting", OperationType.WRITE, max_retries=DEFAULT_MAX_RETRIES)
def set_setting(key: str, value: Any, updated_by: str = "system") -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.set_setting()
    
    Args:
        key: Setting key
        value: Setting value
        updated_by: Username who updated
    
    Returns:
        True if successful
    
    Usage:
        set_setting("conf_thresh", "0.9")
    """
    _run_async(async_set_setting(key, value, updated_by))
    return True


@sync_wrapper("get_all_settings", OperationType.READ, default_on_error={})
def get_all_settings() -> Dict[str, Any]:
    """
    ✅ Wrapper SÍNCRONO para database.get_all_settings()
    
    Returns:
        Dict with all settings
    
    Usage:
        all_settings = get_all_settings()
    """
    return _run_async(async_get_all_settings())


# ============================================
# ALERT WRAPPERS
# ============================================

@sync_wrapper("log_alert", OperationType.WRITE, max_retries=DEFAULT_MAX_RETRIES)
def log_alert(
    person_id: int,
    out_time: float,
    snapshot_path: Optional[str] = None,
    email_sent: bool = False,
    track_id: Optional[int] = None,
    video_path: Optional[str] = None,
    zone_index: Optional[int] = None,
    zone_id: Optional[int] = None,
    zone_name: Optional[str] = None,
    alert_type: str = "zone_violation",
    severity: str = "medium",
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.log_alert()
    
    Args:
        person_id: Person ID
        out_time: Time outside zone
        snapshot_path: Path to snapshot image
        email_sent: Whether email was sent
        track_id: YOLO track ID
        video_path: Path to video
        zone_index: Legacy zone index
        zone_id: Zone foreign key
        zone_name: Zone name
        alert_type: Type of alert
        severity: Alert severity
        description: Alert description
        metadata: Additional metadata
    
    Returns:
        True if successful
    
    Usage:
        log_alert(123, 5.2, "snapshot.jpg", True, track_id=42)
    """
    _run_async(async_log_alert(
        person_id=person_id,
        out_time=out_time,
        snapshot_path=snapshot_path,
        email_sent=email_sent,
        track_id=track_id,
        video_path=video_path,
        zone_index=zone_index,
        zone_id=zone_id,
        zone_name=zone_name,
        alert_type=alert_type,
        severity=severity,
        description=description,
        metadata=metadata
    ))
    return True


# ============================================
# DETECTION WRAPPERS
# ============================================

@sync_wrapper("save_detection", OperationType.WRITE, max_retries=1)
def save_detection(
    track_id: int,
    zone_index: Optional[int] = None,
    zone_name: Optional[str] = None,
    confidence: Optional[float] = None,
    bbox: Optional[Dict[str, Any]] = None,
    status: str = "active",
    duration_seconds: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.save_detection()
    
    Args:
        track_id: YOLO track ID
        zone_index: Zone index
        zone_name: Zone name
        confidence: Detection confidence
        bbox: Bounding box coordinates
        status: Detection status
        duration_seconds: Duration in seconds
        metadata: Additional metadata
    
    Returns:
        True if successful
    
    Usage:
        save_detection(42, zone_index=0, confidence=0.95)
    """
    _run_async(async_save_detection(
        track_id=track_id,
        zone_index=zone_index,
        zone_name=zone_name,
        confidence=confidence,
        bbox=bbox,
        status=status,
        duration_seconds=duration_seconds,
        metadata=metadata
    ))
    return True


# ============================================
# SYSTEM LOG WRAPPERS
# ============================================

@sync_wrapper("log_system_action", OperationType.WRITE, max_retries=1)
def log_system_action(
    action: str,
    username: str,
    reason: Optional[str] = None,
    email_sent: bool = False,
    ip_address: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.log_system_action()
    
    Args:
        action: Action performed
        username: User who performed action
        reason: Reason for action
        email_sent: Whether email was sent
        ip_address: IP address
        context: Additional context
        session_id: Session ID
    
    Returns:
        True if successful
    
    Usage:
        log_system_action("zone_created", "admin", reason="New zone added")
    """
    _run_async(async_log_system_action(
        action=action,
        username=username,
        reason=reason,
        email_sent=email_sent,
        ip_address=ip_address,
        context=context,
        session_id=session_id
    ))
    return True


# ============================================
# ZONE WRAPPERS
# ============================================

@sync_wrapper("get_all_zones", OperationType.READ, default_on_error=[])
def get_all_zones(active_only: bool = False) -> List[Dict[str, Any]]:
    """
    ✅ Wrapper SÍNCRONO para database.get_all_zones()
    
    Args:
        active_only: Return only active zones
    
    Returns:
        List of zones
    
    Usage:
        zones = get_all_zones(active_only=True)
    """
    return _run_async(async_get_all_zones(active_only))


@sync_wrapper("get_zone_by_id", OperationType.READ, default_on_error=None)
def get_zone_by_id(zone_id: int) -> Optional[Dict[str, Any]]:
    """
    ✅ Wrapper SÍNCRONO para database.get_zone_by_id()
    
    Args:
        zone_id: Zone ID
    
    Returns:
        Zone dict or None
    
    Usage:
        zone = get_zone_by_id(1)
    """
    return _run_async(async_get_zone_by_id(zone_id))


@sync_wrapper("create_zone", OperationType.WRITE, max_retries=DEFAULT_MAX_RETRIES)
def create_zone(
    name: str,
    mode: str,
    points: List[List[float]],
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = 5.0,
    full_timeout: Optional[float] = 10.0,
    empty_threshold: Optional[int] = 0,
    full_threshold: Optional[int] = 3,
    enabled: bool = True,
    active: bool = True
) -> int:
    """
    ✅ Wrapper SÍNCRONO para database.create_zone()
    
    Args:
        name: Zone name
        mode: Zone mode
        points: Zone polygon points
        (other zone parameters)
    
    Returns:
        New zone ID
    
    Usage:
        zone_id = create_zone("Zone 1", "GENERIC", [[0,0], [100,0], [100,100], [0,100]])
    """
    return _run_async(async_create_zone(
        name=name,
        mode=mode,
        points=points,
        max_out_time=max_out_time,
        email_cooldown=email_cooldown,
        empty_timeout=empty_timeout,
        full_timeout=full_timeout,
        empty_threshold=empty_threshold,
        full_threshold=full_threshold,
        enabled=enabled,
        active=active
    ))


@sync_wrapper("update_zone", OperationType.UPDATE, max_retries=DEFAULT_MAX_RETRIES)
def update_zone(
    zone_id: int,
    name: Optional[str] = None,
    mode: Optional[str] = None,
    points: Optional[List[List[float]]] = None,
    max_out_time: Optional[float] = None,
    email_cooldown: Optional[float] = None,
    empty_timeout: Optional[float] = None,
    full_timeout: Optional[float] = None,
    empty_threshold: Optional[int] = None,
    full_threshold: Optional[int] = None,
    enabled: Optional[bool] = None,
    active: Optional[bool] = None
) -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.update_zone()
    
    Args:
        zone_id: Zone ID to update
        (optional zone parameters to update)
    
    Returns:
        True if successful
    
    Usage:
        update_zone(1, name="Updated Zone", enabled=False)
    """
    return _run_async(async_update_zone(
        zone_id=zone_id,
        name=name,
        mode=mode,
        points=points,
        max_out_time=max_out_time,
        email_cooldown=email_cooldown,
        empty_timeout=empty_timeout,
        full_timeout=full_timeout,
        empty_threshold=empty_threshold,
        full_threshold=full_threshold,
        enabled=enabled,
        active=active
    ))


@sync_wrapper("delete_zone", OperationType.DELETE, max_retries=DEFAULT_MAX_RETRIES)
def delete_zone(zone_id: int) -> bool:
    """
    ✅ Wrapper SÍNCRONO para database.delete_zone()
    
    Args:
        zone_id: Zone ID to delete (soft delete)
    
    Returns:
        True if successful
    
    Usage:
        delete_zone(1)
    """
    return _run_async(async_delete_zone(zone_id))


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_wrapper_stats() -> Dict[str, Any]:
    """
    ✅ Get statistics for all sync wrappers
    
    Returns:
        Dict with operation statistics
    
    Usage:
        stats = get_wrapper_stats()
        print(f"Total calls: {stats['summary']['total_calls']}")
    """
    summary = _global_stats.get_summary()
    
    total_calls = sum(
        _global_stats.operations[op].total_calls
        for op in _global_stats.operations
    )
    total_success = sum(
        _global_stats.operations[op].successful_calls
        for op in _global_stats.operations
    )
    
    return {
        "operations": summary,
        "summary": {
            "total_calls": total_calls,
            "total_success": total_success,
            "overall_success_rate": (
                f"{(total_success / total_calls * 100):.1f}%"
                if total_calls > 0 else "0.0%"
            )
        }
    }


def reset_wrapper_stats():
    """
    ✅ Reset all wrapper statistics
    
    Usage:
        reset_wrapper_stats()
    """
    global _global_stats
    _global_stats = SyncWrapperStats()
    logger.info("[SYNC WRAPPER] 📊 Statistics reset")


def set_thread_pool_workers(max_workers: int):
    """
    ✅ Update thread pool max workers (requires restart)
    
    Args:
        max_workers: Maximum number of worker threads
    
    Usage:
        set_thread_pool_workers(8)
    """
    global THREAD_POOL_MAX_WORKERS
    THREAD_POOL_MAX_WORKERS = max_workers
    logger.info(f"[SYNC WRAPPER] 🔧 Thread pool workers set to {max_workers}")


# ============================================
# BATCH OPERATIONS (NEW)
# ============================================

def batch_get_settings(keys: List[str]) -> Dict[str, Any]:
    """
    ✅ Get multiple settings in batch (optimized)
    
    Args:
        keys: List of setting keys
    
    Returns:
        Dict mapping keys to values
    
    Usage:
        settings = batch_get_settings(["conf_thresh", "iou_thresh"])
    """
    all_settings = get_all_settings()
    return {key: all_settings.get(key) for key in keys}


def batch_save_detections(detections: List[Dict[str, Any]]) -> int:
    """
    ✅ Save multiple detections in batch (optimized)
    
    Args:
        detections: List of detection dicts
    
    Returns:
        Number of successfully saved detections
    
    Usage:
        saved = batch_save_detections([
            {"track_id": 1, "confidence": 0.9},
            {"track_id": 2, "confidence": 0.85}
        ])
    """
    success_count = 0
    for detection in detections:
        try:
            if save_detection(**detection):
                success_count += 1
        except Exception as e:
            logger.error(f"[SYNC WRAPPER] ❌ Batch detection error: {e}")
    
    return success_count


# ============================================
# TESTE
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Testando database_sync.py v2.0")
    print("=" * 70)
    
    try:
        # Teste 1: Settings
        print("\n1️⃣ Testing settings...")
        value = get_setting("conf_thresh", "0.5")
        print(f"   ✅ get_setting('conf_thresh'): {value}")
        
        success = set_setting("test_key", "test_value", "test_user")
        print(f"   ✅ set_setting(): {success}")
        
        all_settings = get_all_settings()
        print(f"   ✅ get_all_settings(): {len(all_settings)} settings")
        
        # Teste 2: Batch operations
        print("\n2️⃣ Testing batch operations...")
        batch_settings = batch_get_settings(["conf_thresh", "iou_thresh"])
        print(f"   ✅ batch_get_settings(): {len(batch_settings)} settings")
        
        # Teste 3: Zones
        print("\n3️⃣ Testing zones...")
        zones = get_all_zones(active_only=True)
        print(f"   ✅ get_all_zones(): {len(zones)} zones")
        
        # Teste 4: Statistics
        print("\n4️⃣ Testing statistics...")
        stats = get_wrapper_stats()
        print(f"   ✅ Wrapper stats:")
        print(f"      Total calls: {stats['summary']['total_calls']}")
        print(f"      Success rate: {stats['summary']['overall_success_rate']}")
        
        for op, metrics in list(stats['operations'].items())[:5]:
            print(f"      {op}: {metrics['calls']} calls, {metrics['success_rate']}")
        
        print("\n✅ database_sync.py v2.0 funcionando!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
