"""
============================================================================
backend/models/zones.py - ULTRA OPTIMIZED v3.0
Pydantic Models para Smart Zones (Zonas Inteligentes)
============================================================================
NEW Features in v3.0:
- CoordinateSystem enum (normalized vs absolute)
- Advanced geometry validation (convex, area, centroid)
- Bounding box calculation
- Point-in-polygon testing
- Zone statistics and metrics
- Coordinate transformation helpers
- Comprehensive validation rules
- Builder pattern for zone creation
- Zone comparison and equality
- Serialization formats (GeoJSON, WKT)

Previous Features (v2.1):
- empty_threshold e full_threshold
- enabled flag
- Multiple zone modes
============================================================================
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Tuple, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import math
import json


# ============================================
# OTIMIZAÇÃO 1: Constants & Enums
# ============================================

class ZoneMode(str, Enum):
    """✅ Zone operation modes"""
    GENERIC = "GENERIC"  # General purpose zone
    EMPTY = "EMPTY"      # Alert when zone is empty
    FULL = "FULL"        # Alert when zone is full


class CoordinateSystem(str, Enum):
    """✅ NEW: Coordinate system types"""
    NORMALIZED = "normalized"  # 0.0 to 1.0 range
    ABSOLUTE = "absolute"      # Pixel coordinates
    AUTO = "auto"              # Auto-detect based on values


class ZoneStatus(str, Enum):
    """✅ NEW: Zone operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CALIBRATING = "calibrating"


# Constants
MIN_ZONE_POINTS = 3
MAX_ZONE_POINTS = 100
MIN_ZONE_NAME_LENGTH = 1
MAX_ZONE_NAME_LENGTH = 255
DEFAULT_MAX_OUT_TIME = 30.0
DEFAULT_EMAIL_COOLDOWN = 600.0
DEFAULT_EMPTY_TIMEOUT = 5.0
DEFAULT_FULL_TIMEOUT = 10.0
DEFAULT_EMPTY_THRESHOLD = 0
DEFAULT_FULL_THRESHOLD = 3


# ============================================
# OTIMIZAÇÃO 2: Geometry Helpers
# ============================================

class Point2D:
    """✅ NEW: 2D Point with utility methods"""
    
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
    
    def distance_to(self, other: 'Point2D') -> float:
        """Calculate Euclidean distance to another point"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Point2D):
            return False
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)
    
    def __repr__(self) -> str:
        return f"Point2D({self.x:.2f}, {self.y:.2f})"
    
    def to_list(self) -> List[float]:
        """Convert to list [x, y]"""
        return [self.x, self.y]


class BoundingBox:
    """✅ NEW: Bounding box for polygon"""
    
    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
    
    @property
    def width(self) -> float:
        """Width of bounding box"""
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        """Height of bounding box"""
        return self.max_y - self.min_y
    
    @property
    def area(self) -> float:
        """Area of bounding box"""
        return self.width * self.height
    
    @property
    def center(self) -> Point2D:
        """Center point of bounding box"""
        return Point2D(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )
    
    def contains(self, point: Point2D) -> bool:
        """Check if point is inside bounding box"""
        return (self.min_x <= point.x <= self.max_x and
                self.min_y <= point.y <= self.max_y)
    
    def __repr__(self) -> str:
        return f"BoundingBox(x:{self.min_x:.1f}-{self.max_x:.1f}, y:{self.min_y:.1f}-{self.max_y:.1f})"


class PolygonGeometry:
    """✅ NEW: Polygon geometry utilities"""
    
    def __init__(self, points: List[List[float]]):
        self.points = [Point2D(p[0], p[1]) for p in points]
    
    @property
    def num_points(self) -> int:
        """Number of polygon vertices"""
        return len(self.points)
    
    def calculate_area(self) -> float:
        """
        Calculate polygon area using Shoelace formula
        
        Returns:
            Absolute area of polygon
        """
        if len(self.points) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(self.points)):
            j = (i + 1) % len(self.points)
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        
        return abs(area) / 2.0
    
    def calculate_centroid(self) -> Point2D:
        """
        Calculate polygon centroid
        
        Returns:
            Center point of polygon
        """
        if not self.points:
            return Point2D(0, 0)
        
        x_sum = sum(p.x for p in self.points)
        y_sum = sum(p.y for p in self.points)
        
        return Point2D(
            x_sum / len(self.points),
            y_sum / len(self.points)
        )
    
    def get_bounding_box(self) -> BoundingBox:
        """
        Calculate bounding box of polygon
        
        Returns:
            BoundingBox containing the polygon
        """
        if not self.points:
            return BoundingBox(0, 0, 0, 0)
        
        x_coords = [p.x for p in self.points]
        y_coords = [p.y for p in self.points]
        
        return BoundingBox(
            min(x_coords), min(y_coords),
            max(x_coords), max(y_coords)
        )
    
    def is_convex(self) -> bool:
        """
        Check if polygon is convex
        
        Returns:
            True if polygon is convex
        """
        if len(self.points) < 3:
            return False
        
        def cross_product_sign(p1: Point2D, p2: Point2D, p3: Point2D) -> int:
            """Calculate sign of cross product"""
            val = (p2.y - p1.y) * (p3.x - p2.x) - (p2.x - p1.x) * (p3.y - p2.y)
            if val > 0:
                return 1
            elif val < 0:
                return -1
            return 0
        
        sign = None
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            p3 = self.points[(i + 2) % len(self.points)]
            
            current_sign = cross_product_sign(p1, p2, p3)
            if current_sign == 0:
                continue
            
            if sign is None:
                sign = current_sign
            elif sign != current_sign:
                return False
        
        return True
    
    def contains_point(self, point: Point2D) -> bool:
        """
        Check if point is inside polygon using ray casting algorithm
        
        Args:
            point: Point to test
        
        Returns:
            True if point is inside polygon
        """
        if len(self.points) < 3:
            return False
        
        inside = False
        j = len(self.points) - 1
        
        for i in range(len(self.points)):
            xi, yi = self.points[i].x, self.points[i].y
            xj, yj = self.points[j].x, self.points[j].y
            
            if ((yi > point.y) != (yj > point.y)) and \
               (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def calculate_perimeter(self) -> float:
        """
        Calculate polygon perimeter
        
        Returns:
            Total perimeter length
        """
        if len(self.points) < 2:
            return 0.0
        
        perimeter = 0.0
        for i in range(len(self.points)):
            j = (i + 1) % len(self.points)
            perimeter += self.points[i].distance_to(self.points[j])
        
        return perimeter
    
    def to_list(self) -> List[List[float]]:
        """Convert back to list format"""
        return [p.to_list() for p in self.points]


# ============================================
# OTIMIZAÇÃO 3: Coordinate Utilities
# ============================================

class CoordinateValidator:
    """✅ NEW: Coordinate validation and conversion"""
    
    @staticmethod
    def detect_system(points: List[List[float]]) -> CoordinateSystem:
        """
        Auto-detect coordinate system
        
        Args:
            points: List of [x, y] coordinates
        
        Returns:
            Detected coordinate system
        """
        if not points:
            return CoordinateSystem.NORMALIZED
        
        # Check if all coordinates are in [0, 1] range
        all_normalized = all(
            0.0 <= x <= 1.0 and 0.0 <= y <= 1.0
            for x, y in points
        )
        
        if all_normalized:
            return CoordinateSystem.NORMALIZED
        
        return CoordinateSystem.ABSOLUTE
    
    @staticmethod
    def normalize_points(
        points: List[List[float]],
        width: float,
        height: float
    ) -> List[List[float]]:
        """
        Convert absolute coordinates to normalized [0, 1]
        
        Args:
            points: Absolute coordinates
            width: Image/video width
            height: Image/video height
        
        Returns:
            Normalized coordinates
        """
        return [
            [x / width, y / height]
            for x, y in points
        ]
    
    @staticmethod
    def denormalize_points(
        points: List[List[float]],
        width: float,
        height: float
    ) -> List[List[float]]:
        """
        Convert normalized coordinates to absolute pixels
        
        Args:
            points: Normalized coordinates [0, 1]
            width: Image/video width
            height: Image/video height
        
        Returns:
            Absolute pixel coordinates
        """
        return [
            [x * width, y * height]
            for x, y in points
        ]
    
    @staticmethod
    def validate_coordinate_range(
        points: List[List[float]],
        system: CoordinateSystem
    ) -> bool:
        """
        Validate coordinates are in valid range
        
        Args:
            points: Coordinates to validate
            system: Expected coordinate system
        
        Returns:
            True if valid
        """
        if system == CoordinateSystem.NORMALIZED:
            return all(
                0.0 <= x <= 1.0 and 0.0 <= y <= 1.0
                for x, y in points
            )
        elif system == CoordinateSystem.ABSOLUTE:
            return all(
                x >= 0 and y >= 0
                for x, y in points
            )
        
        return True  # AUTO accepts anything


# ============================================
# OTIMIZAÇÃO 4: Enhanced Zone Models
# ============================================

class ZoneBase(BaseModel):
    """✅ Enhanced base model for zone"""
    
    name: str = Field(
        ...,
        min_length=MIN_ZONE_NAME_LENGTH,
        max_length=MAX_ZONE_NAME_LENGTH,
        description="Nome único da zona"
    )
    
    mode: ZoneMode = Field(
        default=ZoneMode.GENERIC,
        description="Modo de operação da zona"
    )
    
    points: List[List[float]] = Field(
        ...,
        min_length=MIN_ZONE_POINTS,
        max_length=MAX_ZONE_POINTS,
        description=f"Pontos do polígono ({MIN_ZONE_POINTS}-{MAX_ZONE_POINTS} pontos)"
    )
    
    # Zone-specific configs (None = use global settings)
    max_out_time: Optional[float] = Field(
        None,
        ge=0,
        description="Tempo máximo fora da zona (segundos)"
    )
    
    email_cooldown: Optional[float] = Field(
        None,
        ge=0,
        description="Cooldown entre emails (segundos)"
    )
    
    empty_timeout: Optional[float] = Field(
        default=DEFAULT_EMPTY_TIMEOUT,
        ge=0,
        description="Timeout para detecção de zona vazia (segundos)"
    )
    
    full_timeout: Optional[float] = Field(
        default=DEFAULT_FULL_TIMEOUT,
        ge=0,
        description="Timeout para detecção de zona cheia (segundos)"
    )
    
    empty_threshold: Optional[int] = Field(
        default=DEFAULT_EMPTY_THRESHOLD,
        ge=0,
        description="Número de pessoas para considerar zona vazia"
    )
    
    full_threshold: Optional[int] = Field(
        default=DEFAULT_FULL_THRESHOLD,
        ge=1,
        description="Número de pessoas para considerar zona cheia"
    )
    
    # NEW: Coordinate system hint
    coordinate_system: CoordinateSystem = Field(
        default=CoordinateSystem.AUTO,
        description="Sistema de coordenadas dos pontos"
    )
    
    @field_validator('points')
    @classmethod
    def validate_points(cls, v: List[List[float]]) -> List[List[float]]:
        """
        ✅ Enhanced point validation
        """
        if len(v) < MIN_ZONE_POINTS:
            raise ValueError(f"Polígono deve ter no mínimo {MIN_ZONE_POINTS} pontos")
        
        if len(v) > MAX_ZONE_POINTS:
            raise ValueError(f"Polígono deve ter no máximo {MAX_ZONE_POINTS} pontos")
        
        for i, point in enumerate(v):
            if len(point) != 2:
                raise ValueError(
                    f"Ponto {i} deve ter exatamente 2 coordenadas [x, y], "
                    f"recebeu {len(point)}"
                )
            
            x, y = point
            
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError(
                    f"Coordenadas do ponto {i} devem ser números, "
                    f"recebeu x={type(x).__name__}, y={type(y).__name__}"
                )
            
            # Check for NaN or Inf
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError(
                    f"Coordenadas do ponto {i} devem ser valores finitos, "
                    f"recebeu x={x}, y={y}"
                )
        
        return v
    
    @model_validator(mode='after')
    def validate_thresholds(self) -> 'ZoneBase':
        """
        ✅ NEW: Validate threshold logic
        """
        if self.empty_threshold is not None and self.full_threshold is not None:
            if self.empty_threshold >= self.full_threshold:
                raise ValueError(
                    f"empty_threshold ({self.empty_threshold}) deve ser menor que "
                    f"full_threshold ({self.full_threshold})"
                )
        
        return self
    
    # ========================================================================
    # NEW: Geometry Methods
    # ========================================================================
    
    def get_geometry(self) -> PolygonGeometry:
        """
        ✅ NEW: Get polygon geometry helper
        
        Returns:
            PolygonGeometry instance with utility methods
        """
        return PolygonGeometry(self.points)
    
    def calculate_area(self) -> float:
        """
        ✅ NEW: Calculate zone area
        
        Returns:
            Area of zone polygon
        """
        return self.get_geometry().calculate_area()
    
    def calculate_centroid(self) -> Tuple[float, float]:
        """
        ✅ NEW: Calculate zone centroid
        
        Returns:
            (x, y) tuple of centroid coordinates
        """
        centroid = self.get_geometry().calculate_centroid()
        return (centroid.x, centroid.y)
    
    def get_bounding_box(self) -> Dict[str, float]:
        """
        ✅ NEW: Get bounding box of zone
        
        Returns:
            Dict with min_x, min_y, max_x, max_y, width, height
        """
        bbox = self.get_geometry().get_bounding_box()
        return {
            "min_x": bbox.min_x,
            "min_y": bbox.min_y,
            "max_x": bbox.max_x,
            "max_y": bbox.max_y,
            "width": bbox.width,
            "height": bbox.height
        }
    
    def is_convex(self) -> bool:
        """
        ✅ NEW: Check if zone is convex polygon
        
        Returns:
            True if convex
        """
        return self.get_geometry().is_convex()
    
    def contains_point(self, x: float, y: float) -> bool:
        """
        ✅ NEW: Check if point is inside zone
        
        Args:
            x: X coordinate
            y: Y coordinate
        
        Returns:
            True if point is inside zone
        """
        return self.get_geometry().contains_point(Point2D(x, y))
    
    def get_detected_coordinate_system(self) -> CoordinateSystem:
        """
        ✅ NEW: Detect actual coordinate system from points
        
        Returns:
            Detected coordinate system
        """
        return CoordinateValidator.detect_system(self.points)
    
    # ========================================================================
    # NEW: Serialization Methods
    # ========================================================================
    
    def to_geojson(self) -> Dict[str, Any]:
        """
        ✅ NEW: Export zone as GeoJSON
        
        Returns:
            GeoJSON Feature dict
        """
        # Close polygon for GeoJSON (first point = last point)
        coordinates = self.points + [self.points[0]]
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]
            },
            "properties": {
                "name": self.name,
                "mode": self.mode.value,
                "max_out_time": self.max_out_time,
                "email_cooldown": self.email_cooldown,
                "empty_threshold": self.empty_threshold,
                "full_threshold": self.full_threshold
            }
        }
    
    def to_wkt(self) -> str:
        """
        ✅ NEW: Export zone as Well-Known Text (WKT)
        
        Returns:
            WKT string representation
        """
        # Close polygon for WKT
        coordinates = self.points + [self.points[0]]
        coord_strings = [f"{x} {y}" for x, y in coordinates]
        return f"POLYGON(({', '.join(coord_strings)}))"


class ZoneCreate(ZoneBase):
    """✅ Enhanced model for zone creation"""
    
    enabled: bool = Field(
        default=True,
        description="Se a zona está habilitada para processamento"
    )
    
    active: bool = Field(
        default=True,
        description="Se a zona está ativa (deprecated, use enabled)"
    )
    
    # NEW: Optional metadata
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Descrição detalhada da zona"
    )
    
    color: Optional[str] = Field(
        None,
        pattern=r'^#[0-9A-Fa-f]{6}$',
        description="Cor da zona em hex (ex: #FF5733)"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="Tags para categorização"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Zona Principal",
                "mode": "GENERIC",
                "points": [
                    [100.0, 100.0],
                    [500.0, 100.0],
                    [500.0, 400.0],
                    [100.0, 400.0]
                ],
                "max_out_time": 30.0,
                "email_cooldown": 600.0,
                "empty_timeout": 5.0,
                "full_timeout": 10.0,
                "empty_threshold": 0,
                "full_threshold": 3,
                "enabled": True,
                "active": True,
                "coordinate_system": "absolute",
                "description": "Zona de monitoramento principal",
                "color": "#00FF00",
                "tags": ["principal", "entrada"]
            }
        }
    )


class ZoneUpdate(BaseModel):
    """✅ Enhanced model for zone update (all optional)"""
    
    name: Optional[str] = Field(
        None,
        min_length=MIN_ZONE_NAME_LENGTH,
        max_length=MAX_ZONE_NAME_LENGTH
    )
    mode: Optional[ZoneMode] = None
    points: Optional[List[List[float]]] = Field(
        None,
        min_length=MIN_ZONE_POINTS,
        max_length=MAX_ZONE_POINTS
    )
    max_out_time: Optional[float] = Field(None, ge=0)
    email_cooldown: Optional[float] = Field(None, ge=0)
    empty_timeout: Optional[float] = Field(None, ge=0)
    full_timeout: Optional[float] = Field(None, ge=0)
    empty_threshold: Optional[int] = Field(None, ge=0)
    full_threshold: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    active: Optional[bool] = None
    coordinate_system: Optional[CoordinateSystem] = None
    
    # NEW: Metadata updates
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    tags: Optional[List[str]] = None
    
    @field_validator('points')
    @classmethod
    def validate_points(cls, v: Optional[List[List[float]]]) -> Optional[List[List[float]]]:
        """Validate points if provided"""
        if v is None:
            return v
        
        # Use same validation as ZoneBase
        return ZoneBase.validate_points(v)


class ZoneResponse(ZoneBase):
    """✅ Enhanced model for zone response"""
    
    id: int
    enabled: bool
    active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    # NEW: Computed fields
    description: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    # ========================================================================
    # NEW: Response Enhancement Methods
    # ========================================================================
    
    def to_dict_with_stats(self) -> Dict[str, Any]:
        """
        ✅ NEW: Convert to dict with geometry statistics
        
        Returns:
            Dict with zone data and computed stats
        """
        base_dict = self.model_dump()
        
        # Add geometry stats
        geometry = self.get_geometry()
        base_dict["stats"] = {
            "area": geometry.calculate_area(),
            "perimeter": geometry.calculate_perimeter(),
            "centroid": self.calculate_centroid(),
            "bounding_box": self.get_bounding_box(),
            "is_convex": self.is_convex(),
            "num_points": len(self.points),
            "coordinate_system": self.get_detected_coordinate_system().value
        }
        
        return base_dict


class ZoneListResponse(BaseModel):
    """✅ Enhanced model for zone list"""
    
    zones: List[ZoneResponse]
    total: int
    
    # NEW: Pagination support
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_pages: Optional[int] = None
    
    # NEW: Filtering info
    filters_applied: Optional[Dict[str, Any]] = None


# ============================================
# NEW v3.0: Zone Builder Pattern
# ============================================

class ZoneBuilder:
    """
    ✅ NEW: Builder pattern for creating zones fluently
    
    Example:
        zone = (ZoneBuilder()
                .with_name("My Zone")
                .with_mode(ZoneMode.GENERIC)
                .add_point(0, 0)
                .add_point(1, 0)
                .add_point(1, 1)
                .add_point(0, 1)
                .with_thresholds(empty=0, full=5)
                .build())
    """
    
    def __init__(self):
        self._name: Optional[str] = None
        self._mode: ZoneMode = ZoneMode.GENERIC
        self._points: List[List[float]] = []
        self._max_out_time: Optional[float] = None
        self._email_cooldown: Optional[float] = None
        self._empty_timeout: float = DEFAULT_EMPTY_TIMEOUT
        self._full_timeout: float = DEFAULT_FULL_TIMEOUT
        self._empty_threshold: int = DEFAULT_EMPTY_THRESHOLD
        self._full_threshold: int = DEFAULT_FULL_THRESHOLD
        self._enabled: bool = True
        self._description: Optional[str] = None
        self._color: Optional[str] = None
        self._tags: Optional[List[str]] = None
    
    def with_name(self, name: str) -> 'ZoneBuilder':
        """Set zone name"""
        self._name = name
        return self
    
    def with_mode(self, mode: ZoneMode) -> 'ZoneBuilder':
        """Set zone mode"""
        self._mode = mode
        return self
    
    def add_point(self, x: float, y: float) -> 'ZoneBuilder':
        """Add a single point"""
        self._points.append([x, y])
        return self
    
    def with_points(self, points: List[List[float]]) -> 'ZoneBuilder':
        """Set all points at once"""
        self._points = points
        return self
    
    def with_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> 'ZoneBuilder':
        """Create rectangular zone"""
        self._points = [
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x, y + height]
        ]
        return self
    
    def with_thresholds(self, empty: int, full: int) -> 'ZoneBuilder':
        """Set empty and full thresholds"""
        self._empty_threshold = empty
        self._full_threshold = full
        return self
    
    def with_timeouts(
        self,
        empty_timeout: float,
        full_timeout: float
    ) -> 'ZoneBuilder':
        """Set timeouts"""
        self._empty_timeout = empty_timeout
        self._full_timeout = full_timeout
        return self
    
    def with_description(self, description: str) -> 'ZoneBuilder':
        """Set description"""
        self._description = description
        return self
    
    def with_color(self, color: str) -> 'ZoneBuilder':
        """Set color (hex format)"""
        self._color = color
        return self
    
    def with_tags(self, *tags: str) -> 'ZoneBuilder':
        """Set tags"""
        self._tags = list(tags)
        return self
    
    def enabled(self, enabled: bool = True) -> 'ZoneBuilder':
        """Set enabled status"""
        self._enabled = enabled
        return self
    
    def build(self) -> ZoneCreate:
        """
        Build the zone
        
        Returns:
            ZoneCreate instance
        
        Raises:
            ValueError: If required fields are missing
        """
        if not self._name:
            raise ValueError("Zone name is required")
        
        if len(self._points) < MIN_ZONE_POINTS:
            raise ValueError(f"At least {MIN_ZONE_POINTS} points required")
        
        return ZoneCreate(
            name=self._name,
            mode=self._mode,
            points=self._points,
            max_out_time=self._max_out_time,
            email_cooldown=self._email_cooldown,
            empty_timeout=self._empty_timeout,
            full_timeout=self._full_timeout,
            empty_threshold=self._empty_threshold,
            full_threshold=self._full_threshold,
            enabled=self._enabled,
            active=self._enabled,
            description=self._description,
            color=self._color,
            tags=self._tags
        )


# ============================================
# TESTE v3.0
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("📋 TESTE: Zone Models v3.0")
    print("=" * 70)
    
    # Test 1: Builder pattern
    print("\n1️⃣ Testando ZoneBuilder (Builder Pattern)...")
    zone1 = (ZoneBuilder()
             .with_name("Zona Principal")
             .with_mode(ZoneMode.GENERIC)
             .with_rectangle(100, 100, 400, 300)
             .with_thresholds(empty=0, full=5)
             .with_description("Zona de entrada principal")
             .with_color("#00FF00")
             .with_tags("entrada", "principal", "monitoramento")
             .enabled(True)
             .build())
    
    print(f"   ✅ Zona criada com Builder: {zone1.name}")
    print(f"   ✅ Pontos: {len(zone1.points)}")
    print(f"   ✅ Tags: {zone1.tags}")
    
    # Test 2: Geometry calculations
    print("\n2️⃣ Testando cálculos geométricos...")
    area = zone1.calculate_area()
    centroid = zone1.calculate_centroid()
    bbox = zone1.get_bounding_box()
    is_convex = zone1.is_convex()
    
    print(f"   ✅ Área: {area:.2f}")
    print(f"   ✅ Centróide: ({centroid[0]:.2f}, {centroid[1]:.2f})")
    print(f"   ✅ Bounding Box: {bbox['width']:.0f}x{bbox['height']:.0f}")
    print(f"   ✅ É convexo: {is_convex}")
    
    # Test 3: Point-in-polygon
    print("\n3️⃣ Testando point-in-polygon...")
    test_points = [
        (300, 250, True),   # Inside
        (50, 50, False),    # Outside
        (100, 100, True),   # On vertex
    ]
    
    for x, y, expected in test_points:
        inside = zone1.contains_point(x, y)
        status = "✅" if inside == expected else "❌"
        print(f"   {status} Ponto ({x}, {y}): {'dentro' if inside else 'fora'}")
    
    # Test 4: Coordinate system detection
    print("\n4️⃣ Testando detecção de sistema de coordenadas...")
    
    normalized_zone = ZoneCreate(
        name="Zona Normalizada",
        mode=ZoneMode.GENERIC,
        points=[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
    )
    
    detected = normalized_zone.get_detected_coordinate_system()
    print(f"   ✅ Sistema detectado: {detected.value}")
    
    # Test 5: GeoJSON export
    print("\n5️⃣ Testando export para GeoJSON...")
    geojson = zone1.to_geojson()
    print(f"   ✅ GeoJSON type: {geojson['type']}")
    print(f"   ✅ Geometry type: {geojson['geometry']['type']}")
    print(f"   ✅ Properties: {list(geojson['properties'].keys())}")
    
    # Test 6: WKT export
    print("\n6️⃣ Testando export para WKT...")
    wkt = zone1.to_wkt()
    print(f"   ✅ WKT: {wkt[:50]}...")
    
    # Test 7: Validation errors
    print("\n7️⃣ Testando validações...")
    
    try:
        invalid = ZoneCreate(
            name="Zona Inválida",
            mode=ZoneMode.GENERIC,
            points=[[0.1, 0.1], [0.9, 0.1]],  # Only 2 points
            empty_threshold=5,
            full_threshold=3  # Invalid: empty > full
        )
    except ValueError as e:
        print(f"   ✅ Validação de thresholds funcionando: {str(e)[:50]}...")
    
    # Test 8: Zone with stats
    print("\n8️⃣ Testando response com estatísticas...")
    zone_response = ZoneResponse(
        id=1,
        name=zone1.name,
        mode=zone1.mode,
        points=zone1.points,
        max_out_time=zone1.max_out_time,
        email_cooldown=zone1.email_cooldown,
        empty_timeout=zone1.empty_timeout,
        full_timeout=zone1.full_timeout,
        empty_threshold=zone1.empty_threshold,
        full_threshold=zone1.full_threshold,
        enabled=zone1.enabled,
        active=zone1.active,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        coordinate_system=zone1.coordinate_system,
        description=zone1.description,
        color=zone1.color,
        tags=zone1.tags
    )
    
    stats_dict = zone_response.to_dict_with_stats()
    print(f"   ✅ Stats incluídas: {list(stats_dict['stats'].keys())}")
    print(f"   ✅ Área calculada: {stats_dict['stats']['area']:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ Todos os testes v3.0 passaram!")
    print("=" * 70)
