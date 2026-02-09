### main.py
import os
import keyboard  # 핫키 훅/대기용
from utils import log, monster_load, character_load
from settings_test import (BASE_DIR, INNER_CROP_PX, DEBUG, CHAT_CROP_PX, IMSHOW_SCALE)
from key_schedule import KeyScheduler
from capture_pw import WindowCapturerPW
import winsound

monster_load(); character_load()  # 몬스터/캐릭터 데이터 강제 로드

# 저장 경로: Temp 고정 (원본/inner 모두 여기로)
def safe_out_path(filename: str = "ocr_screenshot.png") -> str:
    if BASE_DIR is None:
        return filename
    os.makedirs(BASE_DIR, exist_ok=True)
    return os.path.join(BASE_DIR, filename)

def main():
    log("단일 프로세스 시작 (ESC 종료). '*' 시작/재개, '-' 일시정지",True)
    
    try:
        winsound.PlaySound(
            "alert1.wav",
            winsound.SND_FILENAME | winsound.SND_NODEFAULT
        )
        print("played OK (real wav)")
    except RuntimeError as e:
        print("FAILED:", e)

    # ===== 경로 설정 =====
    out_path = safe_out_path("ocr_screenshot.png")
    inner_out_path = safe_out_path("ocr_screenshot_inner.png")
    inner2_out_path = safe_out_path("ocr_screenshot_inner2.png")
    log(f"[PATH] ROI 저장:   {out_path}", True)

    # ===== 캡처 설정 =====
    WINDOW_TITLE = "maple"   # 창 제목 일부 (대소문자 무시)

    cap = WindowCapturerPW(
        window_title_substr=WINDOW_TITLE,
        interval=0.0,                   # 가능한 빠르게
        client_only=True,
        region_pct=(0,0,1,1),           # 전체 클라이언트
        enable_preview=DEBUG,           # 미리보기 ON
        preview_scale=IMSHOW_SCALE,     # 리사이즈 비용 없음
        enable_inner_detect=True,       # 노란점 탐지 켜기
        inner_crop_px=INNER_CROP_PX,    # 예: 미니맵 위치
        inner_detect_every=1,           # 3프레임마다만 탐지
        enable_red_detect=True,
        chat_crop_px=CHAT_CROP_PX,    # 없으면 inner_crop_px 재사용
        red_detect_every=3,
        enable_save=False,              # 저장 OFF (FPS↑)
    )
    cap.start()

    # ===== 키 입력 스케줄러 =====
    ks = KeyScheduler()
    ks.screenshot_path  = out_path
    ks.inner_image_path = inner_out_path
    ks.coord_provider = cap.get_last_yellow_screen  # 주입
    ks.monster_existence = cap.get_monster_existence  # 주입
    ks.inner_rect_provider = cap.get_last_inner_roi_rect   # inner 좌표계 기준 사각형

    # 핫키: '*' 시작/재개, '-' 일시정지
    def on_key(e: keyboard.KeyboardEvent):
        if e.event_type != keyboard.KEY_DOWN:
            return
        if e.name == '*':
            if not ks._started:
                ks.start()
                log("* → 키 스케줄러 시작", True)
            else:
                ks.resume()
                log("* → 키 스케줄러 재개", True)
        elif e.name == '-':
            ks.pause()
            log("- → 키 스케줄러 일시정지", True)

    keyboard.hook(on_key)

    try:
        keyboard.wait('esc')  # ESC 누르면 종료
    finally:
        log("0 수신 → 종료 정리", True)
        try:
            ks.stop()
        except Exception:
            pass
        try:
            cap.stop()
        except Exception:
            pass
        log("종료 완료", True)

if __name__ == "__main__":
    main()