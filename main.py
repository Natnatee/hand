import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time
import sys

# === เลือก Plugin ตรงนี้ ===
from plugins import SoftwareMouse, BLEMouse

if len(sys.argv) > 1 and sys.argv[1].lower() == 'ble':
    port = sys.argv[2] if len(sys.argv) > 2 else None
    mouse = BLEMouse(port=port)
else:
    mouse = SoftwareMouse()

# --- [Sensitivity & Smoothing Settings] ---
# ปรับความไว (ยิ่งตัวเลขมาก เมาส์ยิ่งขยับไกล)
sensitivity_x = 2.0  
sensitivity_y = 2.5  

# การหน่วงเมาส์ (ยิ่งมากยิ่งนุ่มแต่จะรู้สึกหน่วงขึ้น)
smoothening = 5
ploc_x, ploc_y = 0, 0
cloc_x, cloc_y = 0, 0
# ------------------------------------------

# ตั้งค่า MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# ตั้งค่าหน้าจอ
screen_width, screen_height = pyautogui.size()
cam_width, cam_height = 640, 480

is_clicked = False
last_click_time = 0
pinch_start_time = None

# --- [Pause Toggle] ---
paused = False
thumbs_up_start_time = None
THUMBS_UP_HOLD_SEC = 2.0
TOGGLE_COOLDOWN_SEC = 5.0
toggle_cooldown_until = 0

cap = cv2.VideoCapture(0)
cap.set(3, cam_width)
cap.set(4, cam_height)

print("Starting Hand Mouse (Full Camera Mode)... Press 'q' to quit.")

while cap.isOpened():
    success, img = cap.read()
    if not success: break

    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    status = "Searching..."
    dist_val = 0

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            lm = hand_landmarks.landmark
            
            # === ตรวจจับท่าชูนิ้วโป้ง (Pause/Resume) ===
            thumb_tip = lm[4]
            all_landmarks_y = [l.y for l in lm]
            thumb_is_highest = thumb_tip.y <= min(all_landmarks_y) + 0.01
            wrist = lm[0]
            finger_tips = [lm[8], lm[12], lm[16], lm[20]]
            fingers_curled = all(math.hypot(ft.x - wrist.x, ft.y - wrist.y) < 0.25 for ft in finger_tips)
            is_thumbs_up = thumb_is_highest and fingers_curled

            cooldown_left = toggle_cooldown_until - time.time()
            if cooldown_left > 0:
                cv2.putText(img, f"COOLDOWN: {cooldown_left:.1f}s", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
                is_thumbs_up = False

            if is_thumbs_up:
                if thumbs_up_start_time is None: thumbs_up_start_time = time.time()
                held = time.time() - thumbs_up_start_time
                remaining = max(0, THUMBS_UP_HOLD_SEC - held)
                if held >= THUMBS_UP_HOLD_SEC:
                    paused = not paused
                    thumbs_up_start_time = None
                    toggle_cooldown_until = time.time() + TOGGLE_COOLDOWN_SEC
                    print(f">>> {'PAUSED' if paused else 'RESUMED'} <<<")
                    continue
                else:
                    cv2.putText(img, f"THUMBS UP: {remaining:.1f}s", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            else:
                thumbs_up_start_time = None

            if paused:
                status = "PAUSED"
                color = (128, 128, 128)
                continue

            color = (0, 255, 0)  # สีเริ่มต้น (เขียว)

            # 1. คำนวณพิกัด (Center-based Mapping)
            index_8 = hand_landmarks.landmark[8]
            
            # อ้างอิงจากจุดศูนย์กลางจอ (0.5, 0.5) และคูณด้วยความไว
            # สูตร: (ตำแหน่งนิ้ว - 0.5) * ความไว * ขนาดจอ + (ขนาดจอ / 2)
            target_x = (index_8.x - 0.5) * sensitivity_x * screen_width + (screen_width / 2)
            target_y = (index_8.y - 0.5) * sensitivity_y * screen_height + (screen_height / 2)

            # 2. Smoothing
            cloc_x = ploc_x + (target_x - ploc_x) / smoothening
            cloc_y = ploc_y + (target_y - ploc_y) / smoothening

            mouse.move_to(cloc_x, cloc_y)
            ploc_x, ploc_y = cloc_x, cloc_y

            # 3. คลิกและท่าทางอื่นๆ
            thumb_4 = hand_landmarks.landmark[4]
            index_5 = hand_landmarks.landmark[5]
            dist = math.hypot(thumb_4.x - index_5.x, thumb_4.y - index_5.y)
            dist_val = round(dist, 3)

            index_up = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
            middle_up = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
            ring_up = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
            pinky_up = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y
            finger_count = sum([index_up, middle_up, ring_up, pinky_up])

            if dist < 0.05:
                if pinch_start_time is None: pinch_start_time = time.time()
                elapsed = time.time() - pinch_start_time
                if finger_count == 1:
                    if elapsed >= 1.0:
                        if not is_clicked:
                            mouse.mouse_down()
                            is_clicked = True
                        status = "LEFT DRAGGING"
                        color = (0, 0, 255)
                    else:
                        status = f"LEFT PINCH ({1.0 - elapsed:.1f}s)"
                        color = (255, 255, 0)
                elif finger_count == 2:
                    if elapsed >= 1.0:
                        mouse.right_click()
                        status = "RAPID RIGHT CLICK"
                        color = (255, 0, 0)
                    else:
                        status = f"RIGHT PINCH ({1.0 - elapsed:.1f}s)"
                        color = (0, 255, 255)
                elif finger_count == 3:
                    mouse.scroll(30)
                    status = "SCROLL UP"
                    color = (255, 0, 255)
                elif finger_count == 4:
                    mouse.scroll(-30)
                    status = "SCROLL DOWN"
                    color = (255, 100, 0)
            else:
                if pinch_start_time is not None:
                    elapsed_pinch = time.time() - pinch_start_time
                    if is_clicked:
                        mouse.mouse_up()
                        is_clicked = False
                    elif elapsed_pinch < 1.0:
                        if finger_count == 1:
                            now = time.time()
                            if now - last_click_time < 1.0:
                                mouse.double_click()
                                last_click_time = 0
                            else:
                                mouse.click()
                                last_click_time = now
                        elif finger_count == 2:
                            mouse.right_click()
                pinch_start_time = None
                status = "MOVING"
                color = (0, 255, 0)

            # วาดจุดสถานะ
            cv2.circle(img, (int(index_8.x * cam_width), int(index_8.y * cam_height)), 10, color, cv2.FILLED)

    cv2.putText(img, f"Status: {status}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow("Hand Mouse Control (No Boundaries)", img)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break

mouse.cleanup()
cap.release()
cv2.destroyAllWindows()