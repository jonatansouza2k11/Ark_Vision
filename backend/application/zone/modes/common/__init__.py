"""
Common utilities for zone mode handlers.
Provides shared geometry, state management, timers, and rendering.
"""

from .geometry import (
    point_in_polygon,
    get_objects_in_zone,
    get_zone_polygon,
    bbox_intersects_polygon,
    calculate_bbox_intersection_ratio,
)
from .state import ZoneState
from .timers import should_send_alert, should_auto_reset, calculate_elapsed_time

__all__ = [
    # Geometry
    "point_in_polygon",
    "get_objects_in_zone",
    "get_zone_polygon",
    "bbox_intersects_polygon",
    "calculate_bbox_intersection_ratio",
    # State
    "ZoneState",
    # Timers
    "should_send_alert",
    "should_auto_reset",
    "calculate_elapsed_time",
]
