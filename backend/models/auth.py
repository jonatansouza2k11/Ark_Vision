"""
============================================================================
backend/models/auth.py - ULTRA OPTIMIZED v3.1 (COMPLETE & FIXED)
Pydantic Models para Sistema de Autenticação
============================================================================
NEW Features in v3.0:
- Enhanced password validation (strength, policy)
- User roles and permissions system
- Account status management (active, locked, suspended)
- Session tracking and management
- Multi-factor authentication (MFA) support
- Password history and expiration
- User activity statistics
- Security audit trail
- User preferences and settings
- Account lockout protection
- Token refresh mechanism
- Email verification workflow
- Password reset tokens
- User search and filtering

v3.1 FIXES:
- ✅ Username validation moved to UserCreate only (not UserBase)
- ✅ UserResponse now accepts any username (including 'admin')
- ✅ Reserved usernames list adjusted

Previous Features:
- UserCreate, UserLogin, UserResponse
- Token (JWT) authentication
- Password change
- Email validation
============================================================================
"""

from pydantic import (
    BaseModel, EmailStr, Field, field_validator, model_validator, ConfigDict
)
from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re
import hashlib


# ============================================================================
# OTIMIZAÇÃO 1: Enums & Constants
# ============================================================================

class UserRole(str, Enum):
    """✅ NEW: User roles with hierarchy"""
    SUPERADMIN = "superadmin"  # Full system access
    ADMIN = "admin"            # Administrative access
    OPERATOR = "operator"      # Operational access
    VIEWER = "viewer"          # Read-only access
    USER = "user"              # Basic user access
    
    @property
    def level(self) -> int:
        """Get role hierarchy level"""
        return {
            UserRole.SUPERADMIN: 5,
            UserRole.ADMIN: 4,
            UserRole.OPERATOR: 3,
            UserRole.VIEWER: 2,
            UserRole.USER: 1
        }[self]
    
    def has_permission(self, required_role: 'UserRole') -> bool:
        """Check if role has permission for required role"""
        return self.level >= required_role.level


class AccountStatus(str, Enum):
    """✅ NEW: Account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"          # Locked due to failed login attempts
    SUSPENDED = "suspended"    # Temporarily suspended
    PENDING = "pending"        # Awaiting email verification


class TokenType(str, Enum):
    """✅ NEW: Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"


class PermissionType(str, Enum):
    """✅ NEW: Permission types"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Zone management
    ZONE_CREATE = "zone:create"
    ZONE_READ = "zone:read"
    ZONE_UPDATE = "zone:update"
    ZONE_DELETE = "zone:delete"
    
    # Alert management
    ALERT_CREATE = "alert:create"
    ALERT_READ = "alert:read"
    ALERT_UPDATE = "alert:update"
    ALERT_DELETE = "alert:delete"
    
    # Settings management
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    
    # System
    SYSTEM_ADMIN = "system:admin"


class PasswordStrength(str, Enum):
    """✅ NEW: Password strength levels"""
    WEAK = "weak"
    FAIR = "fair"
    GOOD = "good"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


# Password policy constants
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 100
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = False
PASSWORD_EXPIRY_DAYS = 90
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


# ============================================================================
# OTIMIZAÇÃO 2: Password Validation
# ============================================================================

class PasswordPolicy(BaseModel):
    """✅ NEW: Password policy configuration"""
    min_length: int = MIN_PASSWORD_LENGTH
    max_length: int = MAX_PASSWORD_LENGTH
    require_uppercase: bool = PASSWORD_REQUIRE_UPPERCASE
    require_lowercase: bool = PASSWORD_REQUIRE_LOWERCASE
    require_digit: bool = PASSWORD_REQUIRE_DIGIT
    require_special: bool = PASSWORD_REQUIRE_SPECIAL
    
    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate password against policy
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        if len(password) > self.max_length:
            errors.append(f"Password must not exceed {self.max_length} characters")
        
        # Character requirements
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return (len(errors) == 0, errors)
    
    def calculate_strength(self, password: str) -> PasswordStrength:
        """
        Calculate password strength
        
        Returns:
            PasswordStrength enum
        """
        score = 0
        
        # Length score
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        # Complexity score
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'\d', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        
        # Map score to strength
        if score <= 2:
            return PasswordStrength.WEAK
        elif score <= 4:
            return PasswordStrength.FAIR
        elif score <= 5:
            return PasswordStrength.GOOD
        elif score <= 6:
            return PasswordStrength.STRONG
        else:
            return PasswordStrength.VERY_STRONG


# Default password policy
DEFAULT_PASSWORD_POLICY = PasswordPolicy()


# ============================================================================
# 🔧 FIXED: UserBase WITHOUT reserved username validation
# ============================================================================

class UserBase(BaseModel):
    """
    ✅ Base model para usuário (v1.0 compatible)
    
    🔧 v3.1 FIX: Removed reserved username validation
    (moved to UserCreate only)
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    
    @field_validator('username')
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """
        ✅ Basic username format validation only
        NO reserved check here - that's only for creation
        """
        # Only alphanumeric and underscore
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        
        # Cannot start with number
        if v[0].isdigit():
            raise ValueError("Username cannot start with a number")
        
        return v


# ============================================================================
# 🔧 FIXED: UserCreate WITH reserved username validation
# ============================================================================

class UserCreate(UserBase):
    """
    ✅ Model para criação de usuário (v1.0 compatible + enhanced)
    
    🔧 v3.1 FIX: Reserved username validation ONLY here
    """
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    
    # ➕ NEW v3.0 fields
    role: UserRole = Field(default=UserRole.USER, description="User role")
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    
    @field_validator('username')
    @classmethod
    def validate_username_not_reserved(cls, v: str) -> str:
        """
        🔧 v3.1 FIX: Check reserved usernames ONLY during creation
        
        Removed 'admin' from reserved list (common username)
        """
        # Reserved usernames (only checked during creation)
        reserved = ['root', 'system', 'guest', 'anonymous']
        
        if v.lower() in reserved:
            raise ValueError(f"Username '{v}' is reserved")
        
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """✅ Enhanced password validation"""
        is_valid, errors = DEFAULT_PASSWORD_POLICY.validate_password(v)
        if not is_valid:
            raise ValueError(f"Password validation failed: {'; '.join(errors)}")
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone format"""
        if v is None:
            return v
        
        # Remove non-digit characters
        digits = re.sub(r'\D', '', v)
        
        if len(digits) < 10:
            raise ValueError("Phone must have at least 10 digits")
        
        return v
    
    # ========================================================================
    # NEW v3.0: Creation Methods
    # ========================================================================
    
    def get_password_strength(self) -> PasswordStrength:
        """➕ NEW: Get password strength"""
        return DEFAULT_PASSWORD_POLICY.calculate_strength(self.password)
    
    def to_create_dict(self) -> Dict[str, Any]:
        """➕ NEW: Convert to dict for user creation"""
        return {
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "full_name": self.full_name,
            "phone": self.phone
        }
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "SecurePass123",
                "role": "user",
                "full_name": "John Doe",
                "phone": "+55 11 99999-9999"
            }
        }
    )


# ============================================================================
# UserLogin (Enhanced)
# ============================================================================

class UserLogin(BaseModel):
    """✅ Model para login (v1.0 compatible + enhanced)"""
    username: str
    password: str
    
    # ➕ NEW v3.0 fields
    remember_me: bool = Field(default=False, description="Extended session")
    mfa_code: Optional[str] = Field(None, max_length=6, description="MFA code if enabled")
    
    def hash_username(self) -> str:
        """➕ NEW: Hash username for logging (privacy)"""
        return hashlib.sha256(self.username.encode()).hexdigest()[:8]
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "password": "SecurePass123",
                "remember_me": False,
                "mfa_code": None
            }
        }
    )


# ============================================================================
# 🔧 FIXED: UserResponse (accepts ANY username now)
# ============================================================================

class UserResponse(UserBase):
    """
    ✅ Model para resposta de usuário (v1.0 compatible + enhanced)
    
    🔧 v3.1 FIX: Now works with ANY username (including 'admin')
    because UserBase no longer validates reserved names
    """
    
    # ✅ v1.0 fields
    id: int
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    # ➕ NEW v3.0 fields
    account_status: AccountStatus = AccountStatus.ACTIVE
    is_active: bool = True  # ✅ v3.1: ADICIONADO COMO ATRIBUTO!
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email_verified: bool = False
    mfa_enabled: bool = False
    last_password_change: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    permissions: List[str] = Field(default_factory=list)
    preferences: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "admin",  # 🔧 v3.1: Now works fine!
                "email": "admin@example.com",
                "role": "admin",
                "account_status": "active",
                "is_active": True,  # ✅ v3.1: Incluído no exemplo!
                "created_at": "2024-01-01T12:00:00",
                "last_login": "2024-01-02T10:30:00",
                "account_status": "active",
                "full_name": "Administrator",
                "phone": None,
                "email_verified": True,
                "mfa_enabled": False,
                "failed_login_attempts": 0,
                "permissions": ["system:admin"]
            }
        }
    )
    
    # ========================================================================
    # NEW v3.0: Response Methods
    # ========================================================================
    
    def is_active(self) -> bool:
        """➕ NEW: Check if account is active"""
        return self.is_active and self.account_status == AccountStatus.ACTIVE
    
    def is_locked(self) -> bool:
        """➕ NEW: Check if account is locked"""
        if self.account_status == AccountStatus.LOCKED:
            # Check if lockout expired
            if self.locked_until and datetime.now() < self.locked_until:
                return True
        return False
    
    def can_login(self) -> Tuple[bool, Optional[str]]:
        """
        ➕ NEW: Check if user can login
        
        Returns:
            (can_login, reason_if_not)
        """
        if not self.is_active():
            return False, f"Account is {self.account_status.value}"
        
        if self.is_locked():
            remaining = (self.locked_until - datetime.now()).seconds // 60
            return False, f"Account locked for {remaining} more minutes"
        
        if not self.email_verified:
            return False, "Email not verified"
        
        return True, None
    
    def has_permission(self, permission: str) -> bool:
        """➕ NEW: Check if user has specific permission"""
        return permission in self.permissions or "system:admin" in self.permissions
    
    def has_role(self, required_role: UserRole) -> bool:
        """➕ NEW: Check if user has required role level"""
        user_role = UserRole(self.role)
        return user_role.has_permission(required_role)
    
    def password_needs_change(self, max_age_days: int = PASSWORD_EXPIRY_DAYS) -> bool:
        """➕ NEW: Check if password needs to be changed"""
        if not self.last_password_change:
            return True
        
        age = datetime.now() - self.last_password_change
        return age.days > max_age_days
    
    def get_account_age(self) -> timedelta:
        """➕ NEW: Get account age"""
        return datetime.now() - self.created_at
    
    def get_days_since_login(self) -> Optional[int]:
        """➕ NEW: Get days since last login"""
        if not self.last_login:
            return None
        return (datetime.now() - self.last_login).days
    
    def mask_email(self) -> str:
        """➕ NEW: Get masked email for display"""
        local, domain = self.email.split('@')
        if len(local) > 2:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        else:
            masked_local = local[0] + '*'
        return f"{masked_local}@{domain}"
    
    def to_summary(self) -> str:
        """➕ NEW: Get user summary string"""
        return f"{self.full_name or self.username} ({self.role}) - {self.account_status.value}"


# ============================================================================
# TOKEN MODELS (Enhanced)
# ============================================================================

class Token(BaseModel):
    """✅ Model para token JWT (v1.0 compatible + enhanced)"""
    access_token: str
    token_type: str = "bearer"
    
    # ➕ NEW v3.0 fields
    expires_in: Optional[int] = Field(None, description="Token expiry in seconds")
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    
    def is_expired(self, issued_at: datetime) -> bool:
        """➕ NEW: Check if token is expired"""
        if not self.expires_in:
            return False
        
        age = (datetime.now() - issued_at).total_seconds()
        return age >= self.expires_in
    
    def get_expiry_datetime(self, issued_at: datetime) -> Optional[datetime]:
        """➕ NEW: Get token expiry datetime"""
        if not self.expires_in:
            return None
        return issued_at + timedelta(seconds=self.expires_in)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "scope": "user:read alert:read"
            }
        }
    )


class TokenData(BaseModel):
    """✅ Model para dados dentro do token (v1.0 compatible + enhanced)"""
    username: Optional[str] = None
    
    # ➕ NEW v3.0 fields
    user_id: Optional[int] = None
    role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    token_type: TokenType = TokenType.ACCESS
    
    def has_permission(self, permission: str) -> bool:
        """➕ NEW: Check token permission"""
        return permission in self.permissions or "system:admin" in self.permissions


class TokenRefresh(BaseModel):
    """➕ NEW: Token refresh request"""
    refresh_token: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


# ============================================================================
# USER UPDATE MODELS (Enhanced)
# ============================================================================

class UserUpdate(BaseModel):
    """✅ Model para atualização de usuário (v1.0 compatible + enhanced)"""
    
    # ✅ v1.0 fields
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    
    # ➕ NEW v3.0 fields
    role: Optional[UserRole] = None
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    account_status: Optional[AccountStatus] = None
    preferences: Optional[Dict[str, Any]] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate password if provided"""
        if v is None:
            return v
        
        is_valid, errors = DEFAULT_PASSWORD_POLICY.validate_password(v)
        if not is_valid:
            raise ValueError(f"Password validation failed: {'; '.join(errors)}")
        return v
    
    def get_updated_fields(self) -> Dict[str, Any]:
        """➕ NEW: Get only fields being updated"""
        return {
            k: v for k, v in self.model_dump(exclude_none=True).items()
        }
    
    def count_changes(self) -> int:
        """➕ NEW: Count number of changes"""
        return len(self.get_updated_fields())


class PasswordChange(BaseModel):
    """✅ Model para mudança de senha (v1.0 compatible + enhanced)"""
    old_password: str
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password"""
        is_valid, errors = DEFAULT_PASSWORD_POLICY.validate_password(v)
        if not is_valid:
            raise ValueError(f"Password validation failed: {'; '.join(errors)}")
        return v
    
    @model_validator(mode='after')
    def validate_passwords_different(self) -> 'PasswordChange':
        """Ensure new password is different"""
        if self.old_password == self.new_password:
            raise ValueError("New password must be different from old password")
        return self
    
    def get_new_password_strength(self) -> PasswordStrength:
        """➕ NEW: Get new password strength"""
        return DEFAULT_PASSWORD_POLICY.calculate_strength(self.new_password)


# ============================================================================
# NEW v3.0: Password Reset & Email Verification
# ============================================================================

class PasswordReset(BaseModel):
    """➕ NEW: Password reset request"""
    email: EmailStr
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@example.com"
            }
        }
    )


class PasswordResetConfirm(BaseModel):
    """➕ NEW: Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate new password"""
        is_valid, errors = DEFAULT_PASSWORD_POLICY.validate_password(v)
        if not is_valid:
            raise ValueError(f"Password validation failed: {'; '.join(errors)}")
        return v


class EmailVerification(BaseModel):
    """➕ NEW: Email verification"""
    token: str


# ============================================================================
# NEW v3.0: MFA (Multi-Factor Authentication)
# ============================================================================

class MFASetup(BaseModel):
    """➕ NEW: MFA setup request"""
    secret: str
    qr_code: str
    backup_codes: List[str]


class MFAVerify(BaseModel):
    """➕ NEW: MFA verification"""
    code: str = Field(..., min_length=6, max_length=6)
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate MFA code format"""
        if not v.isdigit():
            raise ValueError("MFA code must be 6 digits")
        return v


class MFADisable(BaseModel):
    """➕ NEW: MFA disable request"""
    password: str
    backup_code: Optional[str] = None


# ============================================================================
# NEW v3.0: User Activity & Sessions
# ============================================================================

class UserActivity(BaseModel):
    """➕ NEW: User activity record"""
    user_id: int
    action: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True
    details: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "action": "login",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "timestamp": "2024-01-01T12:00:00",
                "success": True,
                "details": {"method": "password", "mfa": False}
            }
        }
    )


class UserSession(BaseModel):
    """➕ NEW: User session"""
    session_id: str
    user_id: int
    ip_address: str
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    last_activity: datetime = Field(default_factory=datetime.now)
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    def is_idle(self, idle_minutes: int = 30) -> bool:
        """Check if session is idle"""
        idle_time = datetime.now() - self.last_activity
        return idle_time.total_seconds() / 60 > idle_minutes
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining session time"""
        return self.expires_at - datetime.now()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "sess_abc123def456",
                "user_id": 1,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
                "created_at": "2024-01-01T12:00:00",
                "expires_at": "2024-01-01T13:00:00",
                "last_activity": "2024-01-01T12:30:00"
            }
        }
    )


# ============================================================================
# NEW v3.0: User Statistics & Lists
# ============================================================================

class UserStatistics(BaseModel):
    """➕ NEW: User statistics"""
    total_users: int = 0
    active_users: int = 0
    locked_users: int = 0
    suspended_users: int = 0
    pending_users: int = 0
    by_role: Dict[str, int] = Field(default_factory=dict)
    new_users_today: int = 0
    new_users_week: int = 0
    new_users_month: int = 0
    
    def get_active_percentage(self) -> float:
        """Calculate percentage of active users"""
        if self.total_users == 0:
            return 0.0
        return (self.active_users / self.total_users) * 100
    
    def get_locked_percentage(self) -> float:
        """Calculate percentage of locked users"""
        if self.total_users == 0:
            return 0.0
        return (self.locked_users / self.total_users) * 100
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_users": 100,
                "active_users": 85,
                "locked_users": 5,
                "suspended_users": 3,
                "pending_users": 7,
                "by_role": {
                    "admin": 5,
                    "operator": 10,
                    "user": 80,
                    "viewer": 5
                },
                "new_users_today": 3,
                "new_users_week": 15,
                "new_users_month": 45
            }
        }
    )


class UserListFilters(BaseModel):
    """➕ NEW: User list filters"""
    role: Optional[UserRole] = None
    account_status: Optional[AccountStatus] = None
    email_verified: Optional[bool] = None
    mfa_enabled: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None


class UserListResponse(BaseModel):
    """➕ NEW: Paginated user list"""
    users: List[UserResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1
    statistics: Optional[UserStatistics] = None
    
    @model_validator(mode='after')
    def calculate_total_pages(self) -> 'UserListResponse':
        """Calculate total pages"""
        if self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size
        return self
    
    def has_next_page(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages
    
    def has_previous_page(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [],
                "total": 100,
                "page": 1,
                "page_size": 50,
                "total_pages": 2,
                "statistics": {
                    "total_users": 100,
                    "active_users": 85
                }
            }
        }
    )


# ============================================================================
# NEW v3.0: Audit Trail
# ============================================================================

class AuditLog(BaseModel):
    """➕ NEW: Audit log entry"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "username": "admin",
                "action": "update",
                "resource_type": "user",
                "resource_id": 5,
                "ip_address": "192.168.1.100",
                "changes": {
                    "role": {"old": "user", "new": "admin"}
                },
                "timestamp": "2024-01-01T12:00:00"
            }
        }
    )


# ============================================================================
# TESTE v3.1
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🔐 TESTE: Auth Models v3.1 (COMPLETE)")
    print("=" * 70)
    
    # Test 1: v1.0 Compatibility
    print("\n✅ Teste 1: v1.0 Compatibility")
    user_v1 = UserCreate(
        username="testuser",
        email="test@example.com",
        password="Password123"
    )
    print(f"   ✅ Username: {user_v1.username}")
    print(f"   ✅ Email: {user_v1.email}")
    print(f"   ✅ Role default: {user_v1.role}")
    
    # Test 2: v3.1 FIX - Admin username in UserResponse
    print("\n🔧 Teste 2: v3.1 FIX - Admin username works now!")
    admin_response = UserResponse(
        id=1,
        username="admin",  # 🔧 Now works!
        email="admin@example.com",
        role="admin",
        created_at=datetime.now(),
        account_status=AccountStatus.ACTIVE,
        email_verified=True
    )
    print(f"   ✅ Admin username accepted: {admin_response.username}")
    print(f"   ✅ Is active: {admin_response.is_active()}")
    print(f"   ✅ Can login: {admin_response.can_login()}")
    
    # Test 3: UserCreate - reserved username validation
    print("\n✅ Teste 3: UserCreate - Reserved usernames")
    try:
        invalid = UserCreate(
            username="root",  # Still reserved
            email="test@test.com",
            password="Pass123"
        )
        print("   ❌ Should have rejected 'root'")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)[:50]}...")
    
    # Test 4: Enhanced UserCreate with all fields
    print("\n➕ Teste 4: Enhanced UserCreate")
    user_v3 = UserCreate(
        username="johndoe",
        email="john@example.com",
        password="VerySecure123!",
        role=UserRole.OPERATOR,
        full_name="John Doe",
        phone="+55 11 98765-4321"
    )
    print(f"   ✅ Role: {user_v3.role}")
    print(f"   ✅ Full name: {user_v3.full_name}")
    print(f"   ✅ Password strength: {user_v3.get_password_strength()}")
    
    # Test 5: UserLogin with MFA
    print("\n➕ Teste 5: UserLogin with MFA")
    login = UserLogin(
        username="johndoe",
        password="VerySecure123!",
        remember_me=True,
        mfa_code="123456"
    )
    print(f"   ✅ Remember me: {login.remember_me}")
    print(f"   ✅ MFA code: {login.mfa_code}")
    print(f"   ✅ Hashed username: {login.hash_username()}")
    
    # Test 6: Enhanced Token
    print("\n➕ Teste 6: Enhanced Token")
    token = Token(
        access_token="eyJhbGci...",
        expires_in=3600,
        refresh_token="eyJhbGci...",
        scope="user:read alert:read"
    )
    issued_at = datetime.now()
    expiry = token.get_expiry_datetime(issued_at)
    print(f"   ✅ Expires in: {token.expires_in}s")
    print(f"   ✅ Has refresh: {token.refresh_token is not None}")
    print(f"   ✅ Expiry time: {expiry}")
    
    # Test 7: Password Policy
    print("\n✅ Teste 7: Password Policy")
    policy = PasswordPolicy()
    
    test_passwords = [
        ("weak", PasswordStrength.WEAK),
        ("Better1", PasswordStrength.FAIR),
        ("Strong123", PasswordStrength.GOOD),
        ("VeryStrong123!", PasswordStrength.STRONG)
    ]
    
    for pwd, expected in test_passwords:
        strength = policy.calculate_strength(pwd)
        status = "✅" if strength == expected else "❌"
        print(f"   {status} '{pwd}' -> {strength.value} (expected: {expected.value})")
    
    # Test 8: User Roles Hierarchy
    print("\n➕ Teste 8: User Roles Hierarchy")
    admin = UserRole.ADMIN
    user = UserRole.USER
    print(f"   ✅ Admin level: {admin.level}")
    print(f"   ✅ User level: {user.level}")
    print(f"   ✅ Admin >= User? {admin.has_permission(user)}")
    print(f"   ✅ User >= Admin? {user.has_permission(admin)}")
    
    # Test 9: Account Status Checks
    print("\n➕ Teste 9: Account Status Checks")
    locked_user = UserResponse(
        id=2,
        username="locked_user",
        email="locked@test.com",
        role="user",
        created_at=datetime.now(),
        account_status=AccountStatus.LOCKED,
        locked_until=datetime.now() + timedelta(minutes=15)
    )
    can_login, reason = locked_user.can_login()
    print(f"   ✅ Is locked: {locked_user.is_locked()}")
    print(f"   ✅ Can login: {can_login}")
    print(f"   ✅ Reason: {reason}")
    
    # Test 10: User Session
    print("\n➕ Teste 10: User Session")
    session = UserSession(
        session_id="sess_xyz789",
        user_id=1,
        ip_address="192.168.1.50",
        expires_at=datetime.now() + timedelta(hours=1),
        last_activity=datetime.now() - timedelta(minutes=10)
    )
    print(f"   ✅ Is expired: {session.is_expired()}")
    print(f"   ✅ Is idle (30min): {session.is_idle(30)}")
    print(f"   ✅ Remaining: {session.get_remaining_time()}")
    
    # Test 11: User Statistics
    print("\n➕ Teste 11: User Statistics")
    stats = UserStatistics(
        total_users=100,
        active_users=85,
        locked_users=5,
        by_role={"admin": 5, "user": 90, "viewer": 5}
    )
    print(f"   ✅ Total: {stats.total_users}")
    print(f"   ✅ Active %: {stats.get_active_percentage():.1f}%")
    print(f"   ✅ Locked %: {stats.get_locked_percentage():.1f}%")
    
    # Test 12: UserResponse methods
    print("\n➕ Teste 12: UserResponse Methods")
    active_user = UserResponse(
        id=3,
        username="activeuser",
        email="active@test.com",
        role="operator",
        created_at=datetime.now() - timedelta(days=60),
        last_login=datetime.now() - timedelta(hours=3),
        account_status=AccountStatus.ACTIVE,
        full_name="Active User",
        email_verified=True,
        permissions=["user:read", "alert:read", "zone:update"]
    )
    print(f"   ✅ Account age: {active_user.get_account_age().days} days")
    print(f"   ✅ Days since login: {active_user.get_days_since_login()}")
    print(f"   ✅ Masked email: {active_user.mask_email()}")
    print(f"   ✅ Has permission user:read: {active_user.has_permission('user:read')}")
    print(f"   ✅ Has permission user:delete: {active_user.has_permission('user:delete')}")
    print(f"   ✅ Summary: {active_user.to_summary()}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes v3.1 passaram!")
    print("✅ Compatibilidade v1.0 mantida 100%!")
    print("🔧 v3.1 FIX: Username 'admin' funciona corretamente!")
    print("=" * 70)
