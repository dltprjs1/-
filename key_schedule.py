### key_schedule.py
import time, threading, random
import keyboard
from utils import log
from settings_test import (
    SPECIAL_KEY_GAP,
    TARGET_Y,
    TASK_SPECS,
    HIGH_PICKUP_STAGES,
    LOW_PICKUP_STAGES,
    HIGH_PICKUP_PATH,
    LOW_PICKUP_PATH,
    PICK_UP_ON_START,
    MIDDLE_X,
    DEAD_BAND,
    MISC_JITTER_PROB,
    MISC_JITTER_COOLDOWN,
    MISC_JITTER_KEYS,
    HUNT,
    PIT_Y,
    ATTACK_FOR_SEC,
    RANDOM_STAGE,
    RANDOM_PATH,
)

LOPE = False
KEY_TASK = []
class KeyScheduler:
    def __init__(self):
        self.stop_event = threading.Event()
        self.suspend_event = threading.Event()
        self._thr = None
        self._started = False

        # 왕복 이동 상태
        self._last_arrow = None
        self._arrow_lock = threading.Lock()

        # 좌표 읽기 관련 설정
        self.pickup_poll_interval = 0.06

        # 내부 상태
        self._held = set()  # 현재 누르고 있는 키들

        self._last_misc_key_ts = 0.0
        self.input_lock = threading.Lock()
        
    def _schedule(self, r):
        return time.monotonic() + random.uniform(*r)

    def _get_random(self, target):
        return random.randint(*target)

    # 안전 키 조작 (예외 삼키기)
    def _press(self, key):
        try:    keyboard.press(key)
        except: pass

    def _release(self, key):
        try:    keyboard.release(key)
        except: pass

    def _tap(self, key):
        try:    keyboard.press_and_release(key)
        except: pass

    # hold 관리
    def _hold(self, key: str):
        if key not in self._held:
            #log(f"{key} key Press and _held set!")
            self._press(key); self._held.add(key)
        if not keyboard.is_pressed(key):
            self._press(key)
            pass

    def _release_held(self, key: str):
        if key in self._held:
            self._release(key); self._held.remove(key)

    def _release_all(self):
        for k in list(self._held):
            self._release(k)
        self._held.clear()

    def _hard_free_lr(self):
        """좌/우 키를 완전히 풀어주는 짧은 해제 루틴."""
        for _ in range(2):
            self._release_held('left'); self._release_held('right')
            time.sleep(0.005)

    def _ensure_exclusive_lr(self, direction: str):
        """좌/우를 동시에 누르지 않도록 한쪽만 홀드."""
        other = 'right' if direction == 'left' else 'left'
        if not keyboard.is_pressed(direction) or keyboard.is_pressed(other):
            self._hold(direction); self._release_held(other)
        time.sleep(0.05)

    # ------------------------------
    # 몬스터 인식 (return: None, right, left)
    # ------------------------------
    def get_monster_existence(self):
        if not hasattr(self, "monster_existence") or not callable(self.monster_existence):
            log("[PICK] monster_existence 없음 (cap.get_monster_existence 바인드 필요)")
            return None
        try:
            return self.monster_existence()  # left, right, None
        except Exception as e:
            log(f"[PICK] monster_existence 에러: {e}")
            return None

    # ------------------------------
    # 좌표 → inner 좌표 변환
    # ------------------------------
    def get_inner_xy(self):
        global LOPE, KEY_TASK
        """
        coord_provider() 로 (sx,sy) 얻고,
        inner_rect_provider() 가 있으면 inner 좌표 (cx,cy) 로 변환.
        """
        if not hasattr(self, "coord_provider") or not callable(self.coord_provider):
            log("[PICK] coord_provider 없음 (cap.get_last_yellow_screen 바인드 필요)")
            return None

        inner_rect_provider = getattr(self, "inner_rect_provider", None)

        try:
            pos = self.coord_provider()  # (sx, sy) or None
        except Exception as e:
            log(f"[PICK] coord_provider 에러: {e}")
            return None

        if not pos:
            return None
        sx, sy = pos
        cx, cy = sx, sy
        if callable(inner_rect_provider):
            rect = inner_rect_provider()
            if rect and isinstance(rect, dict) and 'left' in rect and 'top' in rect:
                cx = sx - int(rect['left'])
                cy = sy - int(rect['top'])

        # --- 간단 샘플링 로그 ---
        now = time.monotonic()
        if now - getattr(self, "_last_gi_log", 0) > 1.5:
            self._run_task_list_once(KEY_TASK, now)
            log(f"[PICK] pos screen=({sx},{sy}) inner=({cx},{cy})")
            self._fall_into_pit(cy)
            self._last_gi_log = now

        return cx-1, cy-1

    # ------------------------------
    # 특수 시퀀스
    # ------------------------------
    def _async_key_press(self, k):
        with self.input_lock:
            time.sleep(random.uniform(*SPECIAL_KEY_GAP))
            log(f"특수키: {k}")
            self._tap(k)
    
    def _unsync_key_press(self, k):
        log(f"특수키(unsync): {k}")
        self._tap(k)

    def _fall_into_pit(self, cy):
        global LOPE
        if cy == PIT_Y or (not (TARGET_Y[0] <= cy <= TARGET_Y[1]) and not LOPE):
            time.sleep(2)
            keyboard.press('down'); keyboard.press('alt')
            time.sleep(random.uniform(*SPECIAL_KEY_GAP))
            keyboard.release('down'); keyboard.release('alt')

    def _seq_alt(self, direction, target_x, target_y, stage_y, stage_key, poll, hunt):
        log(f"_seq_alt -> direction: {direction}, target_y: {target_y}")
        self._ensure_exclusive_lr(direction); time.sleep(poll); self._tap(stage_key); self._hold('up')
        if self._position_correction(target_x, target_y, stage_y, direction, poll):
            log(f"_seq_alt 완료: 목표=({target_y})")
            return True
        log(f"_seq_alt 미완료: 목표=({target_y})")
        self._ensure_exclusive_lr(direction); self._tap('alt'); self._hold('up')
        self._release_held(direction); self._release_held('up')
        return False

    def _seq_space(self, target_y, target_x, stage_y, stage_key, poll):
        log(f"_seq_space -> target_y: {target_y}, target_x: {target_x}")
        p = self.get_inner_xy()
        if not p:
            return False
        cx, cy = p
        if not stage_y - 1 <= cy <=stage_y + 1:
            log(f"_seq_space 완료: ({cx},{cy}) 목표=({target_x},{target_y})")
            return True
        self._hold('up'); time.sleep(0.15); self._tap(stage_key)
        self._release_held('up')
        time.sleep(poll)
        p = self.get_inner_xy()
        if not p:
            return False
        cx, cy = p
        if not stage_y - 1 <= cy <=stage_y + 1:
            log(f"_seq_space 완료: ({cx},{cy}) 목표=({target_x},{target_y})")
            return True
        log(f"_seq_space 미완료: ({cx},{cy}) 목표=({target_x},{target_y})")
        return False

    def _position_correction(self, target_x, target_y, stage_y, arrow, poll: float):
        time.sleep(2)
        p = self.get_inner_xy()
        if not p:
            time.sleep(poll); return False
        cx, cy = p

        while cy != target_y:
            if keyboard.is_pressed(arrow):
                self._release_held(arrow)
            self._hold('up')
            p = self.get_inner_xy()
            if not p:
                time.sleep(poll)
                continue
            cx, cy = p
            if TARGET_Y[0] <= cy <= TARGET_Y[1]:
                self._release_all();time.sleep(poll*3)
                self._ensure_exclusive_lr('left' if arrow == 'right' else 'right'); self._tap('alt'); self._hold('up')
                return False
            log(f"y 보정 진행: cy={cy} 목표={target_y}")
            time.sleep(poll)  # 너무 빠르게 반복하지 않도록
        return True

    def _hunt(self, arrow, current_arrow):
        if ATTACK_FOR_SEC > 0:
            start = time.monotonic()
            end = start + ATTACK_FOR_SEC
            tap = (0.05, 0.15)

            self._ensure_exclusive_lr(arrow)
            while time.monotonic() < end:
                self._hold('ctrl')
                if not keyboard.is_pressed('ctrl'):
                    self._tap('ctrl')
                time.sleep(random.uniform(*tap))  # CPU 너무 먹지 않도록 짧게 쉬기

            self._release_held('ctrl')
        
        #exists = self.get_monster_existence()
        #while exists is not None:
        #    self._ensure_exclusive_lr(exists);time.sleep(0.05)
        #    self._hold('ctrl')
        #    time.sleep(0.1)
        #    exists = self.get_monster_existence()
        
        if keyboard.is_pressed('ctrl'):
            self._release_held('ctrl')
        
        self._ensure_exclusive_lr(current_arrow)

    def _build_tasks(self):
        key_tasks = []
        other_tasks = []

        for kind, name, interval, preempt, extra in TASK_SPECS:
            if kind == 'key':
                press_fn = self._async_key_press if extra == 'async' else self._unsync_key_press
                func = (lambda n=name, pf=press_fn: pf(n))
                cond = (lambda: True)

                key_tasks.append({
                    "kind": kind,
                    "name": name,
                    "due": self._schedule(interval),
                    "range": interval,
                    "preempt": preempt,
                    "cond": cond,
                    "func": func,
                })

            elif kind == 'call':
                func = getattr(self, extra)
                cond = (lambda: True)

                other_tasks.append({
                    "kind": kind,
                    "name": name,
                    "due": self._schedule(interval),
                    "range": interval,
                    "preempt": preempt,
                    "cond": cond,
                    "func": func,
                })

        return key_tasks, other_tasks

    def _resched(self, task):
        task["due"] = self._schedule(task["range"])

    def _run_task_list_once(self, tasks, now):
        """기존 (A)(B) 로직을 재사용: preempt 전부, 일반 첫 번째"""
        did = False

        # (A) preempt 작업: due면 전부 수행
        for t in tasks:
            if t["preempt"] and t["cond"]() and now >= t["due"]:
                t["func"]()
                self._resched(t)
                did = True

        # (B) 일반 작업: due인 첫 번째만 수행
        if not did:
            for t in tasks:
                if (not t["preempt"]) and t["cond"]() and now >= t["due"]:
                    t["func"]()
                    self._resched(t)
                    did = True
                    break

        return did
    def _cross_x(self, target_x: int, poll: float, jump: bool = False, hysteresis: int = 0):
        log(f"_cross_x -> target_x: {target_x} (hysteresis={hysteresis})")
        stop_ev, suspend_ev = self.stop_event, self.suspend_event

        p = self.get_inner_xy()
        if not p:
            return
        cx, cy = p

        # 진행 루프
        while not stop_ev.is_set():
            if suspend_ev.is_set():
                time.sleep(0.1); continue

            p = self.get_inner_xy()
            if not p:
                time.sleep(poll); continue
            cx, cy = p

            go_right = (cx < target_x)
            current_arrow = 'right' if go_right else 'left'
            self._ensure_exclusive_lr(current_arrow)
            if target_x - DEAD_BAND < cx < target_x + DEAD_BAND:
                if jump:
                    log(f"_cross_x 점프 실행! target_x:{target_x}")
                    time.sleep(1)
                    self._hold('down');self._hold('alt');time.sleep(poll)
                    self._release_held('down');self._release_held('alt')
                break

            if HUNT:
                arrow = self.get_monster_existence()
                if arrow is not None:
                    self._hunt(arrow, current_arrow)
                self._tap('space')

            now = time.monotonic()
            if (now - self._last_misc_key_ts) >= MISC_JITTER_COOLDOWN :
                if random.random() < MISC_JITTER_PROB :
                    time.sleep(0.5)
                    self._tap(random.choice(MISC_JITTER_KEYS))
                    self._last_misc_key_ts = now
            time.sleep(poll)

        # 진행키 해제(혹시 남아 있으면)
        self._release_all()

    # 상향(밧줄 타기) 단계 루틴
    def _look_up_to_stage(self, stage_y, target_x, target_y, poll, nudge_type):
        stage_key = 'space' if nudge_type == 2 else 'alt'
        log(f"_look_up_to_stage ->  stage_y:{stage_y}, target:({target_x},{target_y}), nudge_type:{stage_key}")
        stop_ev, suspend_ev = self.stop_event, self.suspend_event
        while not stop_ev.is_set():
            if suspend_ev.is_set():
                time.sleep(0.1); continue

            p = self.get_inner_xy()
            if not p:
                time.sleep(poll); continue
            cx, cy = p

            # 단계가 바뀌면 메인 루프로 넘겨 재매칭
            if not stage_y - 5 <= cy <= stage_y + 5 or target_y is None:
                self._hard_free_lr()
                return

            # x 근접 → nudge
            if target_x - 10 <= cx <= target_x + 10:
                self._release_all()
                time.sleep(0.05)
                handlers = {
                    'alt': lambda: self._seq_alt('right' if cx < target_x else 'left', target_x ,target_y, stage_y, stage_key, poll, HUNT),
                    'space': lambda: self._seq_space(target_y, target_x, stage_y, stage_key, poll)
                }
                # 실행
                if handlers.get(stage_key, lambda: False)():
                    break
            else:
                now = time.monotonic()
                current_arrow = 'right' if cx < target_x else 'left'
                self._ensure_exclusive_lr(current_arrow)
                if HUNT:
                    arrow = self.get_monster_existence()
                    if arrow is not None:
                        self._hunt(arrow, current_arrow)
                    self._tap('space')
                if (now - self._last_misc_key_ts) >= MISC_JITTER_COOLDOWN :
                    if random.random() < MISC_JITTER_PROB :
                        time.sleep(0.5)
                        self._tap(random.choice(MISC_JITTER_KEYS))
                        self._last_misc_key_ts = now
            time.sleep(poll)

    def _run_stages_once(self, stages, poll: float, fallback_up: float = 0.12):
        log(f"_run_stage_once")
        """
        stages: [(stage_y, (tx, ty), nudge_type), ...]
        - 현재 cy를 읽어 해당 stage를 1회 처리.
        - 마지막 단계(ty is None)면 True 반환(완료), 계속 진행이면 False 반환.
        - 매칭 실패 시 가벼운 fallback(up) 1회만 수행.
        """
        if self.stop_event.is_set():
            self._release_all()
            return True  # 호출부가 즉시 종료하도록

        p = self.get_inner_xy()
        if not p:
            time.sleep(poll)
            return False
        cx, cy = p

        if RANDOM_STAGE:
            shuffled = random.sample(stages, len(stages))
            match = min(shuffled, key=lambda item: abs(item[0] - cy))
        else:
            match = min(stages, key=lambda item: abs(item[0] - cy))

        if match:
            stage_y, (tx, ty), nudge_type = match
            if ty == 999:
                log(f"[PICK] 마지막 단계 도달: {stage_y}")
                self._release_all()
                return True  # 완료
            log(f"Match! 밧줄 y: {stage_y} → {ty} 밧줄 x: {ty}")
            self._look_up_to_stage(stage_y, tx, ty, poll, nudge_type)
            return False

        log(f"Match Fail매칭되는 Stage y1이 없습니다. 현재 y:{cy}")
        self._hold('down'); self._tap('alt'); time.sleep(0.3); self._release_held('down')
        return False

    # ------------------------------
    # 픽업 시퀀스(상세/경량)
    # ------------------------------
    def _high_pick_up_time(self):
        log(f"_high_pick_up_time start!")
        global LOPE
        LOPE = True
        poll = float(self.pickup_poll_interval)

        while True:
            if self._run_stages_once(HIGH_PICKUP_STAGES, poll):
                break  # 마지막 단계 or stop_event

        if RANDOM_PATH:
            path = random.sample(HIGH_PICKUP_PATH, len(HIGH_PICKUP_PATH))
        else:
            path = HIGH_PICKUP_PATH

        for x, jump in path:
            self._cross_x(x, poll, jump)

        LOPE = False
        self._release_all()

    def _low_pick_up_time(self):
        log(f"_low_pick_up_time start!")
        global LOPE
        LOPE = True
        poll = float(self.pickup_poll_interval)
        

        for x, jump in LOW_PICKUP_PATH:
            self._cross_x(x, poll, jump)

        while True:
            if self._run_stages_once(LOW_PICKUP_STAGES, poll):
                break
            time.sleep(0.25)

        # 위치 추가 조정
        #self._cross_x(self._get_random(MIDDLE_X),  poll)
        if self.stop_event.is_set():
            self._release_all(); return

        LOPE = False
        self._release_all()

    # ------------------------------
    # 이동/정렬 루틴
    # ------------------------------
    def nudge_until_deadzone(self):
        global LOPE
        LOPE = True
        """중앙 데드존(MIDDLE_X±DEAD_BAND)에 들어갈 때까지 x축 정렬."""
        poll = float(self.pickup_poll_interval)
        mid = self._get_random(MIDDLE_X)    # 호출 시 1회 픽스
        log(f"nudge_until_deadzone mid: {mid}")

        while True:
            if keyboard.is_pressed('0'):
                log("0 눌림: 중단"); return

            p = self.get_inner_xy()
            if not p:
                log(f"노란 블롭 없음");time.sleep(poll)
                return False
            cx, cy = p

            # y 보정
            while not (TARGET_Y[0] <= cy <= TARGET_Y[1]):
                log(f"y 보정 필요: cy={cy:.1f} ∉ ({TARGET_Y[0]},{TARGET_Y[1]})")
                p = self.get_inner_xy()
                if not p:
                    log(f"노란 블롭 없음");time.sleep(poll)
                    return False
                cx, cy =  p
                
                LOPE = True
                if HUNT:
                    if self._run_stages_once(HIGH_PICKUP_STAGES, poll):
                        break
                else:
                    if self._run_stages_once(LOW_PICKUP_STAGES, poll):
                        break

            # 데드존 도달?
            if mid - DEAD_BAND <= cx <= mid + DEAD_BAND:
                log(f"데드존 진입: cx={cx:.1f} ∈ ({mid - DEAD_BAND},{mid + DEAD_BAND})")
                LOPE = False
                self._release_all()
                return
            current_arrow = 'right' if cx < mid else 'left'
            self._ensure_exclusive_lr(current_arrow)
            if HUNT:
                arrow = self.get_monster_existence()
                if arrow is not None:
                    self._hunt(arrow, current_arrow)
                self._tap('space')

    # ------------------------------
    # 메인 스케줄 루프
    # ------------------------------
    def _key_loop(self, key_tasks):
        log("키(task=kind:key) 스레드 시작")
        try:
            while not self.stop_event.is_set():
                if self.suspend_event.is_set():
                    time.sleep(0.1)
                    continue

                now = time.monotonic()
                self._run_task_list_once(key_tasks, now)
                time.sleep(0.01)  # 키는 더 촘촘히(원하면 0.05로)
        except Exception as e:
            log(f"[KeyScheduler-KeyThread] 에러: {e}")
        finally:
            # 키쪽만 release_all을 해도 되고, 전체 종료 시 한 번만 해도 됨
            log("키(task=kind:key) 스레드 종료")


    def _loop(self):
        log("키 스케줄러 시작")
        global KEY_TASK
        KEY_TASK, other_tasks = self._build_tasks()

        # ✅ key task 전용 스레드 시작
        #self._key_thread = threading.Thread(
        #    target=self._key_loop,
        #    args=(key_tasks,),
        #    daemon=True
        #)
        #self._key_thread.start()

        try:
            while not self.stop_event.is_set():
                if self.suspend_event.is_set():
                    time.sleep(0.1)
                    continue

                now = time.monotonic()
                self._run_task_list_once(other_tasks, now)

                time.sleep(0.05)
        except Exception as e:
            log(f"[KeyScheduler-Main] 에러: {e}")
        finally:
            self._release_all()
            log("키 스케줄러 종료")

    # ------------------------------
    # 라이프사이클
    # ------------------------------
    def start(self):
        if self._started:
            return
        if PICK_UP_ON_START:
            try:
                time.sleep(5)
                self._high_pick_up_time()
            except Exception:
                pass
        self.stop_event.clear(); self.suspend_event.clear()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()
        self._started = True

    def pause(self):
        self.suspend_event.set()
        log("일시정지")

    def resume(self):
        self.suspend_event.clear()
        log("재개")

    def stop(self):
        self.stop_event.set()
        self.suspend_event.clear()
        if self._thr and self._thr.is_alive():
            self._thr.join(timeout=2.0)
        self._release_all()
        self._started = False