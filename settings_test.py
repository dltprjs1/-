# settings.py
import json
from pathlib import Path
import sys

# 1) 경로 설정: GUI에서 저장한 JSON 파일 경로
#CONFIG_PATH = Path(__file__).with_name("config.json")   # 같은 폴더에 config.json

# 2) JSON 로드
#with CONFIG_PATH.open("r", encoding="utf-8") as f:
#    cfg = json.load(f)

def get_app_dir() -> Path:
    # PyInstaller로 빌드된 exe면 여기로 들어옴
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # 개발 환경(스크립트 실행)일 땐 .py가 있는 폴더
    return Path(__file__).parent

APP_DIR = get_app_dir()
CONFIG_PATH = APP_DIR / "config.json"   # exe 옆의 config.json

# 없으면 에러 대신 기본값 생성하고 싶다면 아래 주석 해제
# if not CONFIG_PATH.exists():
#     CONFIG_PATH.write_text("{}", encoding="utf-8")

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    cfg = json.load(f)

# 3) 공통 설정 (튜플은 tuple()로 변환)
PRESS_INTERVAL_RANGE         = tuple(cfg["PRESS_INTERVAL_RANGE"])
X_MOVE_INTERVAL_RANGE        = tuple(cfg["X_MOVE_INTERVAL_RANGE"])
SPECIAL_KEY_GAP              = tuple(cfg["SPECIAL_KEY_GAP"])
HIGH_PICK_UP_INTERVAL_RANGE  = tuple(cfg["HIGH_PICK_UP_INTERVAL_RANGE"])
LOW_PICK_UP_INTERVAL_RANGE   = tuple(cfg["LOW_PICK_UP_INTERVAL_RANGE"])
TARGET_Y                     = tuple(cfg["TARGET_Y"])
PIT_Y                        = int(cfg["PIT_Y"])   # PIT_Y 쓰시면 같이 매핑

# 표 데이터들
TASK_SPECS = []
for t, val, rng, enabled, mode in cfg["TASK_SPECS"]:
    TASK_SPECS.append((t, val, tuple(rng), bool(enabled), mode))

HIGH_PICKUP_STAGES = []
for y1, pair, type in cfg["HIGH_PICKUP_STAGES"]:
    HIGH_PICKUP_STAGES.append((int(y1),
                                (999, 999) if pair is None or int(pair[0]) == 0 else (int(pair[0]), int(pair[1])),
                                999 if type is None or int(type) == 0 else int(type)))

LOW_PICKUP_STAGES = []
for y1, pair, type in cfg["LOW_PICKUP_STAGES"]:
    LOW_PICKUP_STAGES.append((int(y1),
                                (999, 999) if pair is None or int(pair[0]) == 0 else (int(pair[0]), int(pair[1])),
                                999 if type is None or int(type) == 0 else int(type)))

HIGH_PICKUP_PATH = []
for x, jump in cfg["HIGH_PICKUP_PATH"]:
    HIGH_PICKUP_PATH.append((int(x), True if jump else False))

LOW_PICKUP_PATH = []
for x, jump in cfg["LOW_PICKUP_PATH"]:
    LOW_PICKUP_PATH.append((int(x), True if jump else False))

# Nudge DeadZone
MIDDLE_X   = tuple(cfg["MIDDLE_X"])
DEAD_BAND  = int(cfg["DEAD_BAND"])
TIMEOUT_S   = int(cfg["TIMEOUT_S"])

# 사냥 or Not
HUNT = bool(cfg["HUNT"])
SKILL_RADIUS = int(cfg["SKILL_RADIUS"])
# 확률 이벤트
MISC_JITTER_PROB      = float(cfg["MISC_JITTER_PROB"])
MISC_JITTER_COOLDOWN  = float(cfg["MISC_JITTER_COOLDOWN"])
MISC_JITTER_KEYS      = tuple(cfg["MISC_JITTER_KEYS"])   # tuple로

# main.py 관련
BASE_DIR = (None if not cfg["BASE_DIR"] else str(cfg["BASE_DIR"]))
INNER_CROP_PX = tuple(cfg["INNER_CROP_PX"])

# capture_pw.py (Telegram)
SET_TELEGRAM = bool(cfg["SET_TELEGRAM"])
TELEGRAM_BOT = str(cfg["TELEGRAM_BOT"])
CHAT_ID      = str(cfg["CHAT_ID"])
USER_ALERT = bool(cfg.get("SET_USER_ALERT", False))

DEBUG = bool(cfg["DEBUG"])
RANDOM_STAGE = bool(cfg["RANDOM_STAGE"])
RANDOM_PATH = bool(cfg["RANDOM_PATH"])

MONSTER_BAND_TOP = int(cfg["MONSTER_BAND_TOP"])
MONSTER_BAND_BOTTOM = int(cfg["MONSTER_BAND_BOTTOM"])
CHAT_CROP_PX = tuple(cfg["CHAT_CROP_PX"])
IMSHOW_SCALE = float(cfg["IMSHOW_SCALE"] / 100.0)
ATTACK_FOR_SEC = float(cfg["ATTACK_FOR_SEC"])

# === 아래는 기존 로직을 JSON 값으로 재생성 ===
TASK_SPECS.append(('call','x_move', X_MOVE_INTERVAL_RANGE, False, 'nudge_until_deadzone'))

PICK_UP_ON_START = True

if HUNT:
    TASK_SPECS.append(('call', 'pick_high', HIGH_PICK_UP_INTERVAL_RANGE, False, '_high_pick_up_time'))
else:
    TASK_SPECS.append(('call', 'pick_high', HIGH_PICK_UP_INTERVAL_RANGE, False, '_high_pick_up_time'))
    TASK_SPECS.append(('call', 'pick_low',  LOW_PICK_UP_INTERVAL_RANGE,  False, '_low_pick_up_time'))