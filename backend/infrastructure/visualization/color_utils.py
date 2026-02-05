"""
Utilitários de cor
Responsabilidade: Conversões de formato de cor
"""
from typing import Tuple


class ColorUtils:
    """Conversões de cor para OpenCV"""
    
    @staticmethod
    def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
        """
        Converte HEX → BGR (OpenCV).
        
        Args:
            hex_color: "#3B82F6" ou "3B82F6"
        
        Returns:
            (B, G, R) tuple
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)
    
    @staticmethod
    def get_status_color(mode: str, status: str) -> Tuple[int, int, int]:
        """
        Retorna cor BGR baseada em modo e status.
        
        Args:
            mode: "capacity", "occupancy", "alert", etc.
            status: "NORMAL", "WARNING", "CRITICAL", etc.
        
        Returns:
            (B, G, R) tuple
        """
        # Capacity mode colors
        if mode == "capacity":
            if status == "CRITICAL":
                return (0, 0, 255)  # Red
            elif status == "WARNING":
                return (0, 165, 255)  # Orange
            else:
                return (0, 255, 0)  # Green
        
        # Occupancy mode colors
        if mode == "occupancy":
            if status == "FULL":
                return (0, 0, 255)  # Red
            elif status == "OCCUPIED":
                return (0, 255, 255)  # Yellow
            else:
                return (128, 128, 128)  # Gray
        
        # Alert mode colors
        if mode == "alert":
            if status == "ALERT":
                return (0, 0, 255)  # Red
            elif status == "PENDING":
                return (0, 165, 255)  # Orange
            else:
                return (0, 255, 0)  # Green
        
        # Default: blue
        return (255, 130, 0)
