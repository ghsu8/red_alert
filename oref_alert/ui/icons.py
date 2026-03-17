"""Icon creation utilities."""

from PySide6.QtGui import QPixmap, QColor, QImage
from PySide6.QtCore import Qt


def create_lamp_icon(size: int = 64) -> QPixmap:
    """Create a red lamp/alert icon."""
    # Create image and fill it
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(QColor(255, 255, 255, 0))  # Transparent background
    
    # Draw red bulb (center circle)
    center = size // 2
    radius = size // 4
    
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center - 4
            # Draw red circle for bulb
            if dx * dx + dy * dy <= radius * radius:
                image.setPixelColor(x, y, QColor("#EF4444"))
            # Draw dark base
            elif size * 2 // 3 <= y < size * 2 // 3 + size // 6 and \
                 size // 3 <= x < size * 2 // 3:
                image.setPixelColor(x, y, QColor("#333333"))
    
    return QPixmap.fromImage(image)
