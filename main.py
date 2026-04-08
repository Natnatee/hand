import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math
import time

# ตั้งค่า MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# ตั้งค่าหน้าจอและเมาส์
screen_width, screen_height = pyautogui.size()
cam_width, cam_height = 640, 480
pyautogui.PAUSE = 0

# --- [Smoothing Settings] ---
smoothening = 7
ploc_x, ploc_y = 0, 0
cloc_x, cloc_y = 0, 0
# ----------------------------

is_clicked = False
last_click_time = 0
pinch_start_time = None

# --- [Pause Toggle] ---
paused = False
thumbs_up_start_time = None
THUMBS_UP_HOLD_SEC = 2.0
TOGGLE_COOLDOWN_SEC = 5.0
toggle_cooldown_until = 0
# ----------------------

cap = cv2.VideoCapture(0)
cap.set(3, cam_width)
cap.set(4, cam_height)

# ============================================================
# HYBRID AUTO-CALIBRATION: เริ่มต้นปานกลางและขยายตามการขยับมือ
# ============================================================
# เริ่มต้นใช้พื้นที่ 60% ของกลางจอกล้อง
zone_x_min, zone_x_max = 160, 480
zone_y_min, zone_y_max = 120, 360

print("Starting Hand Mouse (Instant ON)... Press 'q' to quit. Press 'c' to reset zone.")

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

            # === ตรวจจับท่าชูนิ้วโป้ง (Thumbs Up) ===
            lm = hand_landmarks.landmark
            thumb_tip = lm[4]
            # เงื่อนไข 1: ปลายนิ้วโป้งอยู่เหนือทุกจุดในแกน Y
            all_landmarks_y = [l.y for l in lm]
            thumb_is_highest = thumb_tip.y <= min(all_landmarks_y) + 0.01

            # เงื่อนไข 2: ปลายนิ้วชี้/กลาง/นาง/ก้อย เข้าใกล้โคนมือ (wrist #0)
            wrist = lm[0]
            finger_tips = [lm[8], lm[12], lm[16], lm[20]]
            fingers_curled = all(
                math.hypot(ft.x - wrist.x, ft.y - wrist.y) < 0.25
                for ft in finger_tips
            )

            is_thumbs_up = thumb_is_highest and fingers_curled

            # เช็ค cooldown หลัง toggle
            cooldown_left = toggle_cooldown_until - time.time()
            if cooldown_left > 0:
                cv2.putText(img, f"COOLDOWN: {cooldown_left:.1f}s", (20, 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
                is_thumbs_up = False  # ไม่ให้ตรวจจับท่าระหว่าง cooldown

            if is_thumbs_up:
                if thumbs_up_start_time is None:
                    thumbs_up_start_time = time.time()
                held = time.time() - thumbs_up_start_time
                remaining = max(0, THUMBS_UP_HOLD_SEC - held)
                if held >= THUMBS_UP_HOLD_SEC:
                    paused = not paused
                    thumbs_up_start_time = None
                    toggle_cooldown_until = time.time() + TOGGLE_COOLDOWN_SEC
                    print(f">>> {'PAUSED' if paused else 'RESUMED'} <<<")
                    continue
                else:
                    cv2.putText(img, f"THUMBS UP: {remaining:.1f}s", (20, 130),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            else:
                thumbs_up_start_time = None

            # ถ้า paused ให้ข้ามการควบคุมเมาส์ทั้งหมด
            if paused:
                status = "PAUSED"
                color = (128, 128, 128)
                cv2.circle(img, (int(lm[8].x * cam_width), int(lm[8].y * cam_height)),
                           10, color, cv2.FILLED)
                continue

            # 1. พิกัดนิ้วชี้ (#8)
            index_8 = hand_landmarks.landmark[8]
            finger_x = index_8.x * cam_width
            finger_y = index_8.y * cam_height

            # แปลงพิกัด: จาก Calibrated Zone → หน้าจอจริง
            target_x = np.interp(finger_x, [zone_x_min, zone_x_max], [0, screen_width])
            target_y = np.interp(finger_y, [zone_y_min, zone_y_max], [0, screen_height])

            # --- [AUTO-EXPANSION Logic] ---
            # ถ้ามือขยับออกนอกกรอบ ให้กรอบขยายออกเพื่อคุมทั้งหน้าจอคอมได้
            if finger_x < zone_x_min: zone_x_min = finger_x
            if finger_x > zone_x_max: zone_x_max = finger_x
            if finger_y < zone_y_min: zone_y_min = finger_y
            if finger_y > zone_y_max: zone_y_max = finger_y
            # ------------------------------

            # 2. Smoothing
            cloc_x = ploc_x + (target_x - ploc_x) / smoothening
            cloc_y = ploc_y + (target_y - ploc_y) / smoothening

            pyautogui.moveTo(cloc_x, cloc_y, _pause=False)
            ploc_x, ploc_y = cloc_x, cloc_y

            # 3. คลิก (โป้ง #4 แตะโคนนิ้วชี้ #5)
            thumb_4 = hand_landmarks.landmark[4]
            index_5 = hand_landmarks.landmark[5]
            dist = math.hypot(thumb_4.x - index_5.x, thumb_4.y - index_5.y)
            dist_val = round(dist, 3)

            # ตรวจสอบจำนวนนิ้วที่ชูขึ้น (นิ้วชี้, กลาง, นาง, ก้อย)
            index_up = hand_landmarks.landmark[8].y < hand_landmarks.landmark[6].y
            middle_up = hand_landmarks.landmark[12].y < hand_landmarks.landmark[10].y
            ring_up = hand_landmarks.landmark[16].y < hand_landmarks.landmark[14].y
            pinky_up = hand_landmarks.landmark[20].y < hand_landmarks.landmark[18].y
            
            # นับจำนวนนิ้วที่ชู (ไม่รวมนิ้วโป้ง)
            finger_count = sum([index_up, middle_up, ring_up, pinky_up])

            if dist < 0.05:
                if pinch_start_time is None:
                    pinch_start_time = time.time()
                
                elapsed = time.time() - pinch_start_time

                if finger_count == 1: # โหมดคลิกซ้าย / ลาก
                    if elapsed >= 1.0:
                        if not is_clicked:
                            pyautogui.mouseDown()
                            is_clicked = True
                        status = "LEFT DRAGGING"
                        color = (0, 0, 255)
                    else:
                        status = f"LEFT PINCH ({1.0 - elapsed:.1f}s)"
                        color = (255, 255, 0)
                
                elif finger_count == 2: # โหมดคลิกขวา
                    if elapsed >= 1.0:
                        # คลิกขวารัวๆ เมื่อค้างเกิน 1 วิ
                        pyautogui.rightClick()
                        status = "RAPID RIGHT CLICK"
                        color = (255, 0, 0)
                    else:
                        status = f"RIGHT PINCH ({1.0 - elapsed:.1f}s)"
                        color = (0, 255, 255)

                elif finger_count == 3: # โหมดซูมเข้า
                    pyautogui.scroll(50)
                    status = "ZOOMING IN (SCROLL UP)"
                    color = (255, 0, 255)
                
                elif finger_count == 4: # โหมดซูมออก
                    pyautogui.scroll(-50)
                    status = "ZOOMING OUT (SCROLL DOWN)"
                    color = (255, 100, 0)
            else:
                if pinch_start_time is not None:
                    elapsed_pinch = time.time() - pinch_start_time
                    
                    if is_clicked: # ปล่อยจากการลากซ้าย
                        pyautogui.mouseUp()
                        is_clicked = False
                    elif elapsed_pinch < 1.0:
                        # ตัดสินใจว่าจะคลิกซ้ายหรือขวาตามจำนวนนิ้วตอนที่ "ปล่อย"
                        if finger_count == 1:
                            now = time.time()
                            if now - last_click_time < 1.0:
                                pyautogui.doubleClick()
                                last_click_time = 0
                            else:
                                pyautogui.click()
                                last_click_time = now
                        elif finger_count == 2:
                            pyautogui.rightClick()

                pinch_start_time = None
                status = "MOVING"
                color = (0, 255, 0)

            # วาด Calibrated Zone (สีชมพู)
            cv2.rectangle(img,
                          (int(zone_x_min), int(zone_y_min)),
                          (int(zone_x_max), int(zone_y_max)),
                          (255, 0, 255), 2)
            # วาดจุดนิ้วชี้
            cv2.circle(img, (int(finger_x), int(finger_y)), 10, color, cv2.FILLED)
            # วาดจุด thumb
            cv2.circle(img, (int(thumb_4.x*cam_width), int(thumb_4.y*cam_height)), 8, color, cv2.FILLED)

    cv2.putText(img, f"Status: {status}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, f"Dist: {dist_val}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.imshow("Hand Mouse Control", img)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        # รีเซ็ตกรอบสีชมพูใหม่
        zone_x_min, zone_x_max = 160, 480
        zone_y_min, zone_y_max = 120, 360
        print("Zone Reset!")

cap.release()
cv2.destroyAllWindows()