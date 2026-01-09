### utils.py
import time, os, io
import cv2, easyocr, torch
import asyncio, telegram, threading, pyperclip, keyboard
import numpy as np
from PIL import Image
from typing import Optional, Set, Tuple
from settings_test import (TELEGRAM_BOT, CHAT_ID, MONSTER_BAND_BOTTOM, MONSTER_BAND_TOP)

LOG_FILE = os.path.join(os.getcwd(), "log.txt")
MAX_SIDE    = 10_000           # 텔레그램 한 변 최대
MAX_PIXELS  = 10_000_000       # 총 픽셀수 제한
MIN_PHOTO = 256
recv_lock = threading.Lock()
send_lock = threading.Lock()
ocr_status = False

# easyocr (광학 문자 감지 - Optimal Character Recognition) 설정
easyocr_reader = easyocr.Reader(['ko', 'en'], gpu=True)

sift = cv2.SIFT_create(nfeatures=600, contrastThreshold=0.02, edgeThreshold=10)
bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

MONSTER_DIR = "monster"
CHARACTER_DIR = "character"
THRESHOLD = 5
SIFT_SCALE = 0.5           # 0.5~0.75 추천 (작을수록 빠름)
RATIO_TEST = 0.75          # Lowe ratio
CHAR_MIN_SCORE = THRESHOLD // 2 if THRESHOLD >= 2 else 1  # 기존 로직 유지
monster_templates = {}
character_templates = {}
"""간단한 로그 함수: [HH:MM:SS] msg 형식으로 찍음 """

def log(msg: str, save = False):
    """간단한 로그 함수: [HH:MM:SS] msg 형식으로 찍음"""
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{t}] {msg}"
    print(formatted)
    if save:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
        except Exception as e:
            print(f"[LOG ERROR] 파일 저장 실패: {e}")

def debug_cuda():
    log(f"torch.cuda.is_available() = {torch.cuda.is_available()}", save=True)
    log(f"torch.version.cuda = {torch.version.cuda}", save=True)
    log(f"torch.cuda.device_count() = {torch.cuda.device_count()}", save=True)
    if torch.cuda.is_available():
        log(f"torch.cuda.get_device_name(0) = {torch.cuda.get_device_name(0)}", save=True)

"""easyocr: 거짓말 탐지기 감지 """
def ocr_lie_detector(roi_bgr: np.ndarray):
    """별도 스레드에서 실행: roi_bgr 는 BGR 이미지"""
    global ocr_status
    try:
        if ocr_status:
            return
        ocr_status = True
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        
        if gray.mean() > 127:
            gray = cv2.bitwise_not(gray)

        results = easyocr_reader.readtext(gray, detail=0)
        text = " ".join(results).strip()
        keywords = ["거짓말", "안전한", "장소", "클릭", "클리", "클렉", "클랙", "플리", "발동", "발등", "3번"]
        detected = any(key in text for key in keywords)
        #log(f"[EasyOCR] 결과: {detected} | 인식텍스트: {text}")

        if detected:
            log(f"{detected} | text: {text}", True)
            send_message("거짓말 탐지기 의심 단어 발생!!!")

        ocr_status = False

    except Exception as e:
        log(f"[OCR Error]: {e}", True)
        ocr_status = False

""" 
텔레그램 연동:
1. bgr(roi) to rgb(Pillow)
2. 텔레그램 이미지 전송
3. 텔레그램 메세지 전송
4. 텔레그램 메세지 반환 및 후처리
"""
def _to_pil(image_or_path):
    """
    str(Path-like) or np.ndarray(BGR/RGB) or PIL.Image -> PIL.Image(RGB)
    """
    if isinstance(image_or_path, Image.Image):
        im = image_or_path
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        return im

    if isinstance(image_or_path, (str, os.PathLike)):
        path = str(image_or_path)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise FileNotFoundError(f"file not ready: {path}")
        im = Image.open(path); im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        return im

    if isinstance(image_or_path, np.ndarray):
        arr = image_or_path
        if arr.ndim == 2:  # grayscale
            im = Image.fromarray(arr)
            return im.convert("RGB")
        if arr.ndim == 3 and arr.shape[2] == 3:
            # OpenCV BGR -> RGB
            im = Image.fromarray(arr[:, :, ::-1])
            return im
        raise ValueError("Unsupported ndarray shape for image")
    raise TypeError("image_or_path must be PIL.Image, np.ndarray, or file path (str)")

def _jpeg_bytes(pil_im, quality=85):
    bio = io.BytesIO()
    pil_im.save(bio, format="JPEG", quality=quality, optimize=True)
    bio.seek(0)
    return bio

async def send_photo_safe(token: str, chat_id: int, image_or_path, caption: str | None = None):
    """
    image_or_path: 파일 경로(str/Path) 또는 이미지(np.ndarray BGR / PIL.Image)
    """
    if not send_lock.acquire(blocking=False):
        print("[send_photo_safe] 전송 중이므로 스킵(send_lock)")
        return False
    
    log(f"send_photo_safe Telegram Sending Caption: {caption}")
    im = _to_pil(image_or_path)
    w, h = im.size

    if w*h > MAX_PIXELS or max(w,h) > MAX_SIDE:
        s = min(MAX_SIDE / max(w,h), (MAX_PIXELS / (w*h)) ** 0.5)
        im = im.resize((max(1, int(w*s)), max(1, int(h*s))), Image.LANCZOS)
    
    bot = telegram.Bot(token=token)
    buf = _jpeg_bytes(im, quality=85)   # 반드시 io.BytesIO 반환
    buf.name = "image.jpg"
    
    try:
        await bot.send_photo(chat_id=chat_id, photo=buf, caption=caption)
        return
    except Exception as e:
        log(f"send_photo_safe Error :{e}", True)
        return
    finally:
        send_lock.release()

async def recv_one_message(
    token: str,
    allowed_chat_ids: Optional[Set[int]] = None,
    wait_for_next_only: bool = True,   # True이면 기존 대기열은 버리고 '다음 1건'만 받음
    long_poll_timeout: int = 5
) -> Tuple[int, str]:
    with recv_lock:
        bot = telegram.Bot(token=token)
        offset = 0
        if wait_for_next_only:
            past = await bot.get_updates(timeout=0)
            if past:
                offset = past[-1].update_id + 1  # 이후 것부터 받기

        while True:
            updates = await bot.get_updates(offset=offset, timeout=long_poll_timeout)
            if not updates:
                continue

            for u in updates:
                offset = u.update_id + 1
                msg = getattr(u, "message", None) or getattr(u, "edited_message", None) \
                    or getattr(u, "channel_post", None)
                if not msg:
                    continue

                chat_id = msg.chat.id
                text = msg.text or ""

                if (allowed_chat_ids is None) or (chat_id in allowed_chat_ids):
                    #print(f"[TG] from {chat_id}: {text!r}")
                    send_chat_copy(text)
                    return chat_id, text

def send_message(txt):
    try:
        bot = telegram.Bot(TELEGRAM_BOT)
        asyncio.run(bot.send_message(chat_id=CHAT_ID, text=txt))
    except Exception as e:
        log(f"[Telegram error]: {e}", True)

def send_chat_copy(text):
    keyboard.press_and_release('enter')
    time.sleep(0.5)
    pyperclip.copy(text)         # 클립보드에 텍스트 넣기
    keyboard.send('ctrl+v')
    time.sleep(0.5)
    keyboard.press_and_release('enter')

def recv_one_message_blocking(
    token: str,
    allowed_chat_ids: Optional[Set[int]] = None,
    wait_for_next_only: bool = True
):
    return asyncio.run(
        recv_one_message(token, allowed_chat_ids, wait_for_next_only)
    )

def monster_load():
    global monster_templates
    monster_templates = load_templates_from_dir(MONSTER_DIR)

def character_load():
    global character_templates
    character_templates = load_templates_from_dir(CHARACTER_DIR)

def load_templates_from_dir(base_dir):
    templates = {}

    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        if not os.path.isdir(path):
            continue

        templates[name] = []

        for file in os.listdir(path):
            if not file.lower().endswith(".png"):
                continue

            img_path = os.path.join(path, file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            # 원본 + 좌우 플립
            variants = [img, cv2.flip(img, 1)]

            for var in variants:
                kp, des = sift.detectAndCompute(var, None)
                if des is None or len(kp) == 0:
                    continue

                h, w = var.shape[:2]

                templates[name].append({
                    "kp": kp,
                    "des": des,
                    "shape": (h, w),
                    "file": file
                })

    print("로드 완료:", {k: len(v) for k, v in templates.items()})
    return templates

def _sift_compute(gray):
    """다운스케일 후 SIFT. (kp 좌표는 스케일된 이미지 기준)"""
    if SIFT_SCALE != 1.0:
        gray = cv2.resize(gray, None, fx=SIFT_SCALE, fy=SIFT_SCALE, interpolation=cv2.INTER_AREA)
    kp, des = sift.detectAndCompute(gray, None)
    return gray, kp, des

def _match_score_and_best_trainidx(des_tpl, des_roi, ratio=RATIO_TEST, early_stop=None):
    """
    des_tpl vs des_roi knnMatch 결과에서:
    - good 개수만 카운트
    - good 중 가장 distance 작은 match의 trainIdx 반환
    - early_stop 이상이면 즉시 중단 (속도↑)
    """
    matches = bf.knnMatch(des_tpl, des_roi, k=2)
    good_count = 0
    best_train_idx = None
    best_dist = 1e9

    for m, n in matches:
        if m.distance < ratio * n.distance:
            good_count += 1
            if m.distance < best_dist:
                best_dist = m.distance
                best_train_idx = m.trainIdx
            if early_stop is not None and good_count >= early_stop:
                break

    return good_count, best_train_idx


def decide_arrow_and_monster_screen(full_gray, attack_range_px: int):
    h, w = full_gray.shape

    # 화면 크롭 (네 로직 유지)
    y1 = int(h * 0.4)
    y2 = int(h * 0.8)
    x1 = int(w * 0.1)
    x2 = int(w * 0.9)
    full_crop = full_gray[y1:y2, x1:x2]
    if full_crop.size == 0:
        return None

    # 캐릭터 찾기 (크롭 기준 좌표)
    character_point = character_match_point(full_crop)
    if character_point is None:
        return None

    cx = int(character_point[0])
    cy = int(character_point[1])
    ch, cw = full_crop.shape

    # 몬스터 밴드 ROI (주의: MONSTER_BAND_*이 픽셀 값이라는 전제)
    top    = max(0, cy - MONSTER_BAND_TOP)
    bottom = min(ch, cy + MONSTER_BAND_BOTTOM)

    left   = max(0, cx - attack_range_px)
    right  = min(cw, cx + attack_range_px)

    if bottom <= top or right <= left:
        return None

    roi = full_crop[top:bottom, left:right]
    return monster_match_direction(roi)


def character_match_point(roi_gray):
    """
    캐릭터 템플릿과 매칭해서 캐릭터 포인트 반환.
    최적화:
    - 다운스케일 SIFT
    - good 리스트 미생성(카운트+best만)
    """
    img_s, kp_roi, des_roi = _sift_compute(roi_gray)
    if des_roi is None or not kp_roi:
        return None

    best_score = 0
    best_point = None

    # 템플릿 순회
    for _, templates in character_templates.items():
        for tpl in templates:
            des_tpl = tpl["des"]
            # 캐릭터는 점수가 낮을 수 있으니 early_stop은 조금 느슨하게
            score, best_train_idx = _match_score_and_best_trainidx(
                des_tpl, des_roi, ratio=RATIO_TEST, early_stop=None
            )

            if score > best_score and best_train_idx is not None:
                best_score = score
                best_point = kp_roi[best_train_idx].pt

    if best_score <= CHAR_MIN_SCORE or best_point is None:
        return None

    # 스케일 좌표 -> 원본 roi_gray 좌표로 복구
    if SIFT_SCALE != 1.0:
        return (best_point[0] / SIFT_SCALE, best_point[1] / SIFT_SCALE)
    return best_point


def monster_match_direction(roi_gray, debug=False):
    """
    몬스터 템플릿과 매칭해서 left/right 반환.
    최적화:
    - 다운스케일 SIFT
    - THRESHOLD 도달 시 즉시 return (early stop)
    - good 리스트 미생성(카운트+best만)
    """
    img_s, kp_roi, des_roi = _sift_compute(roi_gray)
    if des_roi is None or not kp_roi:
        return None

    h, w = img_s.shape
    center_x = w // 2

    best_score = 0
    best_point_x = None

    # 템플릿 순회
    for monster_name, templates in monster_templates.items():
        for tpl in templates:
            des_tpl = tpl["des"]

            # THRESHOLD만 넘기면 방향 판단 가능 → early_stop=THRESHOLD
            score, best_train_idx = _match_score_and_best_trainidx(
                des_tpl, des_roi, ratio=RATIO_TEST, early_stop=THRESHOLD
            )

            if debug:
                print(f"{monster_name:15s} / {tpl.get('file','?'):15s}  good={score}")

            # 최고점 갱신
            if score > best_score and best_train_idx is not None:
                best_score = score
                best_point_x, _ = kp_roi[best_train_idx].pt

                # 임계치 넘으면 즉시 방향 반환
                if best_score >= THRESHOLD:
                    return "right" if best_point_x > center_x else "left"

    return None

debug_cuda()