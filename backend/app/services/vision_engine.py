import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image
from app.services.desktop_service import desktop_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class VisionEngine:
    def __init__(self):
        self._reader = None
        self._initialized = False

    def _lazy_init(self):
        """Initializes EasyOCR reader lazily to avoid startup delays."""
        if self._initialized:
            return
        
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader engine...")
            self._reader = easyocr.Reader(
                lang_list=settings.OCR_LANGUAGES,
                gpu=settings.OCR_GPU
            )
            self._initialized = True
            logger.info("EasyOCR reader engine successfully initialized.")
        except ImportError:
            logger.warning("easyocr library not found. Vision Engine will operate in simulation mode.")
            self._reader = None
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self._reader = None
            self._initialized = True

    async def capture_and_process(self) -> List[Dict[str, Any]]:
        """
        Captures a fresh screenshot and runs OCR parsing to extract screen elements.
        Returns a list of structured items: {"text": str, "center": (x, y), "box": [...]}
        """
        self._lazy_init()
        
        # 1. Capture screen screenshot using Desktop Service
        screenshot = desktop_service.take_screenshot()
        temp_path = "temp_screenshot.png"
        screenshot.save(temp_path)

        elements = []

        try:
            # 2. Run OCR on screenshot
            if self._reader:
                # EasyOCR readtext expects file path or numpy array
                results = self._reader.readtext(temp_path)
                for bbox, text, confidence in results:
                    # bbox format: [[top_left], [top_right], [bottom_right], [bottom_left]]
                    xs = [point[0] for point in bbox]
                    ys = [point[1] for point in bbox]
                    center_x = sum(xs) // 4
                    center_y = sum(ys) // 4

                    elements.append({
                        "text": text,
                        "confidence": float(confidence),
                        "center": (int(center_x), int(center_y)),
                        "box": [[int(pt[0]), int(pt[1])] for pt in bbox]
                    })
            else:
                # Mock simulation mode if EasyOCR is not available
                logger.info("Simulation mode: generating mock screen elements.")
                elements = [
                    {"text": "File", "confidence": 0.99, "center": (20, 15), "box": [[10, 10], [30, 10], [30, 20], [10, 20]]},
                    {"text": "Edit", "confidence": 0.99, "center": (60, 15), "box": [[50, 10], [70, 10], [70, 20], [50, 20]]},
                    {"text": "Submit", "confidence": 0.95, "center": (500, 400), "box": [[470, 385], [530, 385], [530, 415], [470, 415]]}
                ]
        except Exception as e:
            logger.error(f"Error during OCR execution: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return elements

    async def find_element(self, query: str) -> Optional[Tuple[int, int]]:
        """
        Finds the coordinates of the target element by matching text.
        Performs case-insensitive substring searching.
        """
        elements = await self.capture_and_process()
        query_lower = query.lower()
        for element in elements:
            if query_lower in element["text"].lower():
                logger.info(f"Target '{query}' matched with text '{element['text']}' at {element['center']}")
                return element["center"]
        logger.warning(f"Could not locate element with text query '{query}' on screen.")
        return None

vision_engine = VisionEngine()
