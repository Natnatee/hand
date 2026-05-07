"""
BLE Mouse Plugin — ส่งคำสั่งผ่าน Serial ไปยัง ESP32-C3 BLE Mouse
ให้คอมพิวเตอร์ปลายทางมองเห็นเป็นเมาส์บลูทูธจริงๆ (Hardware-level)
"""
import serial
import serial.tools.list_ports
import time
import pyautogui
from .base_mouse import BaseMouse


class BLEMouse(BaseMouse):
    """ควบคุมเมาส์ผ่าน ESP32-C3 BLE (Hardware-level)"""

    def __init__(self, port=None, baud=115200):
        self.screen_width, self.screen_height = pyautogui.size()
        self.prev_x = self.screen_width / 2
        self.prev_y = self.screen_height / 2
        self.ser = None

        # ถ้าไม่ระบุพอร์ต ให้ลองหาอัตโนมัติ
        if port is None:
            print("[Plugin] Searching for ESP32-C3 automatically...")
            port = self._find_esp32_port()

        if port:
            try:
                self.ser = serial.Serial(port, baud, timeout=0.05)
                time.sleep(2)  # รอให้บอร์ดพร้อม
                print(f"[Plugin] BLEMouse connected on {port}")
                # อ่านข้อความตอนเริ่มต้นออกให้หมด
                while self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"  ESP32: {line}")
            except Exception as e:
                print(f"[Plugin] BLEMouse FAILED to connect on {port}: {e}")
        else:
            print("[Plugin] BLEMouse: No port specified and no ESP32-C3 detected.")
            print("  -> Fallback: จะใช้ print() แทนเพื่อ debug (Dry Run)")

    def _find_esp32_port(self):
        """ค้นหาพอร์ตที่น่าจะเป็น ESP32-C3"""
        ports = serial.tools.list_ports.comports()
        
        # ค้นหาด้วย Keyword ที่เจาะจงสำหรับ ESP32-C3 (Internal USB)
        for p in ports:
            # เพิ่ม "USB Serial Device" เพราะเครื่องคุณโชว์ชื่อนี้ครับ
            if "USB JTAG/serial debug unit" in p.description or "USB Serial Device" in p.description:
                print(f"  -> Found ESP32-C3 (Match Description): {p.device}")
                return p.device
        
        # ค้นหาด้วย Keyword ทั่วไปถ้าหาแบบเจาะจงไม่เจอ
        for p in ports:
            if "ESP32" in p.description or "CP210" in p.description or "CH340" in p.description:
                print(f"  -> Found potential ESP device: {p.device} ({p.description})")
                return p.device
                
        return None

    def _send(self, cmd):
        """ส่งคำสั่งไปยัง ESP32"""
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + '\n').encode())
            # อ่าน response กลับมาแบบไม่บล็อก
            time.sleep(0.01)
            while self.ser.in_waiting:
                self.ser.readline()
        else:
            # Fallback สำหรับ debug โดยไม่ต้องต่อบอร์ด
            pass

    def move_to(self, x, y):
        # แปลง Absolute -> Relative (dx, dy)
        dx = int(x - self.prev_x)
        dy = int(y - self.prev_y)
        self.prev_x = x
        self.prev_y = y

        # ESP32 BLE Mouse รับค่า move ได้ทีละ -127 ถึง 127
        while dx != 0 or dy != 0:
            send_x = max(-127, min(127, dx))
            send_y = max(-127, min(127, dy))
            self._send(f"M {send_x} {send_y}")
            dx -= send_x
            dy -= send_y

    def click(self):
        self._send("C L")

    def double_click(self):
        self._send("C L")
        time.sleep(0.05)
        self._send("C L")

    def right_click(self):
        self._send("C R")

    def mouse_down(self):
        self._send("P L")

    def mouse_up(self):
        self._send("R L")

    def scroll(self, amount):
        scaled = max(-10, min(10, amount // 5)) if abs(amount) > 5 else amount
        self._send(f"S {scaled}")

    def cleanup(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[Plugin] BLEMouse serial closed.")
