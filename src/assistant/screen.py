"""Screen capture module."""

import base64
import io
import logging

import mss
from PIL import Image

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screenshots for AI vision analysis."""

    def __init__(self, monitor: int = 1):
        self.monitor = monitor

    def capture(self, max_width: int = 1920) -> Image.Image:
        """Take a screenshot and return as PIL Image, resized if needed."""
        with mss.mss() as sct:
            monitors = sct.monitors
            if self.monitor >= len(monitors):
                mon = monitors[0]  # fallback to all monitors
            else:
                mon = monitors[self.monitor]

            screenshot = sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

        # Resize if too large (saves tokens and latency)
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        logger.info("Captured screen: %dx%d", img.width, img.height)
        return img

    @staticmethod
    def image_to_base64(img: Image.Image, quality: int = 80) -> str:
        """Convert PIL Image to base64 JPEG string for API consumption."""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def capture_base64(self, max_width: int = 1920) -> str:
        """Capture screen and return as base64 JPEG."""
        img = self.capture(max_width)
        return self.image_to_base64(img)
