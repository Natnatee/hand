"""
Software Mouse Plugin — ใช้ pyautogui ควบคุมเมาส์ผ่าน Software (แบบเดิม)
"""
import pyautogui
from .base_mouse import BaseMouse

pyautogui.PAUSE = 0


class SoftwareMouse(BaseMouse):
    """ควบคุมเมาส์ผ่าน pyautogui (Software-level)"""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        print("[Plugin] SoftwareMouse (pyautogui) loaded.")

    def move_to(self, x, y):
        pyautogui.moveTo(x, y, _pause=False)

    def click(self):
        pyautogui.click()

    def double_click(self):
        pyautogui.doubleClick()

    def right_click(self):
        pyautogui.rightClick()

    def mouse_down(self):
        pyautogui.mouseDown()

    def mouse_up(self):
        pyautogui.mouseUp()

    def scroll(self, amount):
        pyautogui.scroll(amount)
