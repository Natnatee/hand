#pragma once — Python Plugin Base Class
"""
Base class สำหรับ Mouse Plugin ทุกตัว
Plugin ใหม่ให้สืบทอดจาก class นี้และ implement ทุก method
"""
from abc import ABC, abstractmethod


class BaseMouse(ABC):
    """Interface สำหรับ Mouse Controller ทุกประเภท"""

    @abstractmethod
    def move_to(self, x, y):
        """ขยับเมาส์ไปที่พิกัด (x, y) บนหน้าจอ"""
        pass

    @abstractmethod
    def click(self):
        """คลิกซ้าย"""
        pass

    @abstractmethod
    def double_click(self):
        """ดับเบิลคลิก"""
        pass

    @abstractmethod
    def right_click(self):
        """คลิกขวา"""
        pass

    @abstractmethod
    def mouse_down(self):
        """กดเมาส์ซ้ายค้าง (เริ่มลาก)"""
        pass

    @abstractmethod
    def mouse_up(self):
        """ปล่อยเมาส์ซ้าย (หยุดลาก)"""
        pass

    @abstractmethod
    def scroll(self, amount):
        """เลื่อนลูกกลิ้ง (บวก=ขึ้น, ลบ=ลง)"""
        pass

    def cleanup(self):
        """เรียกตอนปิดโปรแกรม (ถ้าจำเป็น)"""
        pass
