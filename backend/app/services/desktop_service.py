import logging
from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image
import pyautogui

logger = logging.getLogger(__name__)

# Enforce pyautogui failsafe controls
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

class IDesktopService(ABC):
    @abstractmethod
    def click(self, x: int, y: int, double: bool = False) -> None:
        """Simulates a mouse click at coordinates (x, y)."""
        pass

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Simulates typing text via keyboard."""
        pass

    @abstractmethod
    def press_key(self, key_name: str) -> None:
        """Simulates pressing a specific key combination (e.g., 'enter', 'ctrl+c')."""
        pass

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Gets target resolution width and height."""
        pass

    @abstractmethod
    def take_screenshot(self) -> Image.Image:
        """Captures a screenshot of the primary display screen."""
        pass


class PyAutoGUIDesktopService(IDesktopService):
    def click(self, x: int, y: int, double: bool = False) -> None:
        try:
            logger.info(f"PyAutoGUI click at coords: ({x}, {y}), double={double}")
            if double:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)
        except Exception as e:
            logger.error(f"Failed mouse click operation: {e}")
            raise e

    def type_text(self, text: str) -> None:
        try:
            logger.info(f"PyAutoGUI typing text payload of size: {len(text)}")
            pyautogui.write(text, interval=0.01)
        except Exception as e:
            logger.error(f"Failed keyboard type operation: {e}")
            raise e

    def press_key(self, key_name: str) -> None:
        try:
            logger.info(f"PyAutoGUI hotkey sequence: {key_name}")
            # Handle hotkeys (e.g., 'ctrl+c') vs single keys (e.g., 'enter')
            keys = key_name.split("+")
            if len(keys) > 1:
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key_name)
        except Exception as e:
            logger.error(f"Failed key sequence press: {e}")
            raise e

    def get_screen_size(self) -> Tuple[int, int]:
        width, height = pyautogui.size()
        return int(width), int(height)

    def take_screenshot(self) -> Image.Image:
        try:
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            logger.error(f"Failed screen capture screenshot: {e}")
            raise e

# Export a single global instance using PyAutoGUI
desktop_service = PyAutoGUIDesktopService()
