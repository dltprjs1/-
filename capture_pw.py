# === capture_pw_lite.py (FPS 최적화 버전) ===
import time, threading, os, gc
import cv2, sys, asyncio
import numpy as np
import ctypes, utils, win32gui
from utils import (log, 
    ocr_lie_detector,
    decide_arrow_and_monster_screen
)
from mss.exception import ScreenShotError
from settings_test import (
    SET_TELEGRAM,
    TELEGRAM_BOT,
    CHAT_ID,
    USER_ALERT,
    SKILL_RADIUS,
    MONSTER_BAND_TOP,
    MONSTER_BAND_BOTTOM
)
_last_ocr_ts = 0

# ---- DPI aware ----
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def _find_hwnd(title_substr: str):
    title_substr = (title_substr or "").lower()
    target = None
    def enum_handler(hwnd, _):
        nonlocal target
        if not win32gui.IsWindow(hwnd):
            return
        title = win32gui.GetWindowText(hwnd) or ""
        if title and title_substr in title.lower():
            target = hwnd
    win32gui.EnumWindows(enum_handler, None)
    return target

def _get_client_rect_screen(hwnd):
    try:
        if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd) or win32gui.IsIconic(hwnd):
            return None
        l, t, r, b = win32gui.GetClientRect(hwnd)
        w, h = (r - l), (b - t)
        if w <= 0 or h <= 0:
            return None
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        return {"left": int(left), "top": int(top), "width": int(w), "height": int(h)}
    except Exception:
        return None

def _capture_mss(sct, hwnd, client_only=True):
    # sct는 _loop 내부 with mss.mss()에서 생성된 지역변수여야 함
    if sct is None:
        return None, None, None
    try:
        monitors = sct.monitors
    except AttributeError as e:
        log(f"_capture_mss AttributeError Error: {e}", True)
        return None, None, None

    if not win32gui.IsWindow(hwnd) or win32gui.IsIconic(hwnd) or not win32gui.IsWindowVisible(hwnd):
        log(f"_capture_mss IsWindow, IsIconic, IsWindowVisible NotFound Error: {e}", True)
        return None, None, None

    if client_only:
        rect = _get_client_rect_screen(hwnd)
        if not rect:
            log(f"_capture_mss _get_client_rect_screen Error: {e}", True)
            return None, None, None
        region = rect
    else:
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            region = {"left": int(l), "top": int(t), "width": int(r-l), "height": int(b-t)}
        except Exception as e:
            log(f"_capture_mss GetWindowRect Error: {e}", True)
            return None, None, None

    # 가상 스크린으로 안전 클램프
    v = monitors[0]
    v_left, v_top = int(v["left"]), int(v["top"])
    v_right, v_bottom = v_left + int(v["width"]), v_top + int(v["height"])

    left   = max(v_left,   min(region["left"], v_right - 1))
    top    = max(v_top,    min(region["top"],  region["top"] + 0))  # 그냥 min 체크
    right  = min(v_right,  region["left"] + region["width"])
    bottom = min(v_bottom, region["top"]  + region["height"])

    if right <= left or bottom <= top:
        return None, None, None

    safe_region = {"left": int(left), "top": int(top),
                    "width": int(right - left), "height": int(bottom - top)}
    try:
        shot = sct.grab(safe_region)       # BGRA
        img = np.asarray(shot)[..., :3].copy()  # BGR
        return img, left, top
    except ScreenShotError as e:
        log(f"_capture_mss ScreenShot Error: {e}", True)
        return None, None, None
    except Exception:
        log(f"_capture_mss Error: {e}", True)
        return None, None, None

class WindowCapturerPW:
    """
    최적화 포인트:
    - 저장/텔레그램/무거운 연산 제거(옵션)
    - 미니맵 탐지는 N프레임마다 (inner_detect_every)
    - 미리보기 표시 on/off
    """
    def __init__(self,
                    window_title_substr,
                    interval=0.0,             # 0: 가능한 한 빠르게(타임슬라이스만)
                    client_only=True,
                    region_pct=(0.0, 0.0, 1.0, 1.0),
                    region_px=None,

                    # ====== 옵션(성능 영향) ======
                    enable_preview=False,       # cv2.imshow 표시
                    preview_window_name="maple-capture",
                    preview_scale=0.5,          # 1.0 유지 권장 (리사이즈 비용 없음)

                    enable_inner_detect=False,  # 미니맵 노란점 탐지
                    inner_crop_px=None,         # (x,y,w,h) in ROI
                    inner_detect_every=3,       # N프레임마다 탐지

                    enable_red_detect=False,
                    chat_crop_px=None,           # 없으면 inner_crop_px 재사용
                    red_detect_every=3,

                    enable_save=False,          # 파일 저장(성능↓)
                    out_path="roi.png",         # 저장 경로

                    white_tol=8,                # 화이트 허용오차 (0~255, 클수록 느슨)
                    white_min_pixels=100,        # 화이트 픽셀 최소 개수(노이즈 방지)
                    white_alert_cooldown=10,
                    yellow_gui= False
                    ):
        self.title_sub   = window_title_substr
        self.interval    = float(interval)
        self.client_only = client_only

        self.region_pct  = tuple(region_pct)
        self.region_px   = tuple(region_px) if region_px else None

        self.enable_preview      = bool(enable_preview)
        self.preview_window_name = str(preview_window_name)
        self.preview_scale       = float(preview_scale)

        self.enable_inner_detect = bool(enable_inner_detect)
        self.inner_crop_px       = tuple(inner_crop_px) if inner_crop_px else None
        self.inner_detect_every  = int(inner_detect_every)

        self.enable_red_detect = bool(enable_red_detect)
        self.chat_crop_px       = tuple(chat_crop_px) if chat_crop_px else None
        self.red_detect_every  = int(red_detect_every)

        self.enable_save         = bool(enable_save)
        self.out_path            = str(out_path)

        self.white_tol          = int(white_tol)
        self.white_min_pixels   = int(white_min_pixels)
        self.white_alert_cooldown = float(white_alert_cooldown)
        
        self.stop_event = threading.Event()
        self._thr       = None
        self._hwnd      = None

        self._last_roi_screen_rect   = None
        self._last_inner_roi_rect    = None
        self._last_yellow_screen     = None
        self._monster_existence      = None
        self._monster_busy = False
        self._lock = threading.RLock()

        self._last_white_send_ts = 0.0
        self._frame_idx = 0
        self._ = 0.0
        self.yellow_gui = bool(yellow_gui)
        self._last_monster_ts = 0.0
        self.monster_cooldown = 0.25  # 0.15~0.5 사이 취향

    # --- getters (락 보호) ---
    def get_roi_screen_rect(self):
        with self._lock:
            return self._last_roi_screen_rect
    def get_last_yellow_screen(self):
        with self._lock:
            return self._last_yellow_screen
    def get_monster_existence(self):
        with self._lock:
            return self._monster_existence
    def get_last_inner_roi_rect(self):
        with self._lock:
            return self._last_inner_roi_rect
    def get_last_roi_frame(self):
        with self._lock:
            return None if getattr(self, "_last_roi_frame", None) is None else self._last_roi_frame.copy()
    def get_last_inner_frame(self):
        with self._lock:
            return None if getattr(self, "_last_inner_frame", None) is None else self._last_inner_frame.copy()
    def _async_update_monster(self, roi_gray, attack_range_px):
        try:
            result = decide_arrow_and_monster_screen(roi_gray, attack_range_px)
            with self._lock:
                self._monster_existence = result
        finally:
            self._monster_busy = False  # 끝났다고 표시
    # --- 가벼운 HSV 노란색 중심 검출 (모멘트) ---
    @staticmethod
    def _find_yellow_center_bgr(bgr):
        try:
            # 위 코드와 같은 기준: BGR ≈ (0, 255, 255)
            delta = int(30)
            lower = np.array([0, max(0, 255 - delta), max(0, 255 - delta)], dtype=np.uint8)
            upper = np.array([min(255, 0 + delta), 255, 255], dtype=np.uint8)
            mask = cv2.inRange(bgr, lower, upper)
            m = cv2.moments(mask)
            if m["m00"] > 0:
                cx = int(m["m10"] / m["m00"])
                cy = int(m["m01"] / m["m00"])
                return cx, cy
            return None
        except Exception as e:
            log(f"_find_yellow_center_bgr Error: {e}", True)
            return None

    @staticmethod
    def _find_red_user_bgr(bgr):
        try:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            lower = np.array([0, 0, 228], dtype=np.uint8)
            upper = np.array([10, 10, 248], dtype=np.uint8)
            mask = cv2.inRange(bgr, lower, upper)
            m = cv2.moments(mask)
            if m["m00"] > 0:
                return True
            return False
        except Exception as e:
            log(f"_find_red_user_bgr Error: {e}", True)
            return False

    @staticmethod
    def _get_chat_section(roi, chat_crop_px):
        try:
            rx, ry, rw, rh = chat_crop_px
            rx = max(0, rx); ry = max(0, ry)
            rxe = min(roi.shape[1], rx + rw)
            rye = min(roi.shape[0], ry + rh)
            if rxe > rx and rye > ry:
                return roi[ry:rye, rx:rxe]
            return None
        except Exception as e:
            log(f"_get_chat_section Error: {e}", True)
            return None

    # --- PNG 저장(옵션) ---
    @staticmethod
    def _save_png(path, img):
        try:
            d = os.path.dirname(path)
            if d: os.makedirs(d, exist_ok=True)
            cv2.imwrite(path, img)
            return True
        except Exception as e:
            log(f"_save_png Error: {e}", True)
            return False

    # --- 메인 루프 ---
    def _loop(self):
        try:
            import mss
            global _last_ocr_ts
            with mss.mss() as sct:
                while not self.stop_event.is_set():
                    chat_roi = None
                    # 1) HWND 확인/갱신
                    if not self._hwnd or not win32gui.IsWindow(self._hwnd):
                        self._hwnd = _find_hwnd(self.title_sub)
                        if not self._hwnd:
                            time.sleep(0.05); continue

                    # 2) 캡처
                    full, base_left, base_top = _capture_mss(sct, self._hwnd, self.client_only)
                    if full is None:
                        time.sleep(0.01); continue

                    h, w = full.shape[:2]
                    # 3) ROI 계산
                    if self.region_px:
                        rx, ry, rw, rh = self.region_px
                    else:
                        x1p, y1p, x2p, y2p = self.region_pct
                        rx = int(w * x1p); ry = int(h * y1p)
                        rw = int(w * (x2p - x1p)); rh = int(h * (y2p - y1p))

                    x1 = 0 if rx < 0 else rx
                    y1 = 0 if ry < 0 else ry
                    x2 = min(w, x1 + rw)
                    y2 = min(h, y1 + rh)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    roi = full[y1:y2, x1:x2]  # copy 제거(미리보기만이면 굳이 복사 X)

                    now = time.monotonic()
                    #roi_copy = roi[y1:y2, x1:x2].copy()
                    if now - _last_ocr_ts >= 1 and SET_TELEGRAM:
                        h = roi.shape[0]
                        cut = int(h * 0.725)
                        roi_for_ocr = roi[:cut, :].copy()
                        threading.Thread(
                            target=ocr_lie_detector,
                            args=(roi_for_ocr,),
                            daemon=True
                        ).start()
                        _last_ocr_ts = now  # 타임스탬프 업데이트

                    with self._lock:
                        self._last_roi_screen_rect = {
                            "left": base_left + x1, "top": base_top + y1,
                            "width": (x2 - x1), "height": (y2 - y1),
                        }

                    # 4) (옵션) 미니맵 노란점 탐지: N프레임마다
                    self._frame_idx += 1
                    if self.enable_inner_detect and self.inner_crop_px and (self._frame_idx % self.inner_detect_every == 0):
                        sx, sy, sw, sh = self.inner_crop_px
                        sx = max(0, sx); sy = max(0, sy)
                        ex = min(roi.shape[1], sx + sw)
                        ey = min(roi.shape[0], sy + sh)
                        if ex > sx and ey > sy:
                            inner = roi[sy:ey, sx:ex]
                            if self.yellow_gui:
                                inner_copy = roi[sy:ey, sx:ex].copy()
                                with self._lock:
                                    self._last_roi_frame = roi            # 전체 ROI
                                    self._last_inner_frame = inner_copy        # INNER
                            
                            cen = self._find_yellow_center_bgr(inner)
                            if cen:
                                cx, cy = cen
                               
                                with self._lock:
                                    self._last_inner_roi_rect = {
                                        "left": base_left + sx,
                                        "top":  base_top  + sy,
                                        "width": (ex - sx), "height": (ey - sy),
                                    }
                                    self._last_yellow_screen = (
                                        int(base_left + sx + cx),
                                        int(base_top  + sy + cy),
                                    )
                                now_m = time.monotonic()
                                if not self._monster_busy and (now_m - self._last_monster_ts >= self.monster_cooldown):
                                    self._monster_busy = True
                                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                    roi_copy = roi_gray.copy()
                                    threading.Thread(
                                        target=self._async_update_monster,
                                        args=(roi_copy, SKILL_RADIUS),
                                        daemon=True
                                    ).start()
                                with self._lock:
                                    cur = self._monster_existence
                            user = self._find_red_user_bgr(inner)
                            if user and SET_TELEGRAM and USER_ALERT:
                                chat_roi = WindowCapturerPW._get_chat_section(roi, self.chat_crop_px) \
                                    if (self.enable_red_detect and self.chat_crop_px and (self._frame_idx % self.red_detect_every == 0)) else None
                                now_ts = time.time()
                                try:
                                    if now_ts - self._last_white_send_ts >= self.white_alert_cooldown\
                                    and not chat_roi is None:
                                        # 메세지 내용은 원하는 대로                                        
                                        threading.Thread(
                                            target=lambda: asyncio.run(
                                                utils.send_photo_safe(
                                                    TELEGRAM_BOT, CHAT_ID,
                                                    chat_roi,
                                                    "미리보기"
                                                )
                                            ),
                                            daemon=True
                                        ).start()
                                        self._last_white_send_ts = now_ts
                                        threading.Thread(
                                            target=lambda: utils.recv_one_message_blocking(
                                                TELEGRAM_BOT,
                                                allowed_chat_ids=None,
                                                wait_for_next_only=True
                                            ),
                                            daemon=True
                                        ).start()
                                except Exception as _e:
                                    log(f"[WHITE] telegram err: {_e}", True)

                    # 5) (옵션) 저장 — 느리므로 필요할 때만
                    if self.enable_save:
                        _ = self._save_png(self.out_path, roi)

                    # 6) (옵션) 미리보기
                    if self.enable_preview:
                        preview_img = roi.copy()

                        # 공통 텍스트 옵션
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.5
                        thickness = 1

                        h_prev, w_prev = preview_img.shape[:2]

                        # ---- 몬스터 탐지 세로 띠 (Y 40% ~ 70%) + 라벨 ----
                        band_top = int(h_prev * MONSTER_BAND_TOP)
                        band_bottom = int(h_prev * MONSTER_BAND_BOTTOM)

                        cv2.rectangle(
                                preview_img,(0, band_top),(w_prev, band_bottom),(0, 255, 255),1
                            )
                        cv2.putText(
                                preview_img,"MONSTER BAND",(5, band_top - 5),font,font_scale,(0, 255, 255),thickness,cv2.LINE_AA
                            )

                        # ---- 몬스터 중앙 스킬 반경 (center_x ± SKILL_RADIUS) + 라벨 ----
                        center_x = w_prev // 2
                        x1_skill = max(0, center_x - SKILL_RADIUS)
                        x2_skill = min(w_prev, center_x + SKILL_RADIUS)

                        if x2_skill > x1_skill:
                            cv2.rectangle(
                                preview_img,(x1_skill, band_top),(x2_skill, band_bottom),(255, 255, 0),2
                            )
                            cv2.putText(
                                preview_img,"SKILL RANGE",(x1_skill + 5, band_top + 20),font,font_scale,(255, 255, 0),thickness,cv2.LINE_AA
                            )

                        # ---- roi_for_ocr rectangle (BLUE) + 라벨 ----
                        cut_h = int(preview_img.shape[0] * 0.725)
                        cv2.rectangle(
                                preview_img,(0, 0),(preview_img.shape[1], cut_h),(255, 0, 0),2
                            )
                        cv2.putText(
                                preview_img,"OCR",(5, 20),font,font_scale,(255, 0, 0),thickness,cv2.LINE_AA
                            )

                        # ---- inner rectangle (GREEN) + 라벨 ----
                        if self.enable_inner_detect and self.inner_crop_px:
                            sx, sy, sw, sh = self.inner_crop_px
                            ex = min(preview_img.shape[1], sx + sw)
                            ey = min(preview_img.shape[0], sy + sh)
                            cv2.rectangle(
                                    preview_img,(sx, sy),(ex, ey),(0, 255, 0),2
                                )
                            cv2.putText(
                                    preview_img,"INNER",(sx + 5, sy + 20),font,font_scale,(0, 255, 0),thickness,cv2.LINE_AA
                                )

                        # ---- chat_roi rectangle (RED) + 라벨 ----
                        if chat_roi is not None and self.chat_crop_px:
                            cx, cy, cw, ch = self.chat_crop_px
                            cv2.rectangle(
                                    preview_img,(cx, cy),(cx + cw, cy + ch),(0, 0, 255),2
                                )
                            cv2.putText(
                                    preview_img,"CHAT",(cx + 5, cy + 20),font,font_scale,(0, 0, 255),thickness,cv2.LINE_AA
                                )

                        # 최종 미리보기 이미지
                        view = preview_img

                        # scale option
                        if self.preview_scale != 1.0:
                            view = cv2.resize(
                                view,
                                (int(view.shape[1] * self.preview_scale),
                                int(view.shape[0] * self.preview_scale)),
                                interpolation=cv2.INTER_NEAREST
                            )

                        cv2.imshow(self.preview_window_name, view)
                        if cv2.waitKey(1) & 0xFF == 27:
                            break

                    # 7) 간격
                    if self.interval > 0:
                        time.sleep(self.interval)
        except Exception as e:
            log(f"Loop Error: {e}", True)
            return None   
    
        finally:
            if self.enable_preview:
                cv2.destroyAllWindows()

    def start(self):
        self.stop_event.clear()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()

    def stop(self):
        self.stop_event.set()
        if self._thr and self._thr.is_alive():
            self._thr.join(timeout=2.0)