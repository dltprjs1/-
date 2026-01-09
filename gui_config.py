#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import platform
import random
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, asdict, field
from typing import Tuple, Dict, Any, List, Optional

# =========================
# 설정 데이터
# =========================
@dataclass
class Config:
    # 기존 범위(초)
    PRESS_INTERVAL_RANGE: Tuple[float, float] = (0.5, 2.0)
    X_MOVE_INTERVAL_RANGE: Tuple[float, float] = (2.0, 3.0)
    SPECIAL_KEY_GAP: Tuple[float, float] = (2.0, 2.0)
    HIGH_PICK_UP_INTERVAL_RANGE: Tuple[float, float] = (80.0, 150.0)
    LOW_PICK_UP_INTERVAL_RANGE: Tuple[float, float] = (140.0, 180.0)
    TARGET_Y: Tuple[int, int] = (90, 90)
    SET_USER_ALERT: bool = False
    SKILL_RADIUS: int = 200
    
    DEBUG: bool = False
    MONSTER_BAND_TOP: float = 40
    MONSTER_BAND_BOTTOM: float = 73
    CHAT_CROP_PX: Tuple[int, int, int, int] = (0, 500, 500, 200)
    IMSHOW_SCALE: int = 50
    ATTACK_FOR_SEC: int = 3

    # 좌표(px)
    PIT_Y: int = 90

    # 리스트/표 데이터
    TASK_SPECS: list = field(default_factory=lambda: [
        ('key',  'pagedown',  (60, 80),    True,   'async'),
        ('key',  'del',       (100, 120),  False,  'async'),
        ('key',  'home',      (150, 180),  False,  'async'),
        ('key',  'insert',    (780, 900),  False,  'unsync'),
    ])

    HIGH_PICKUP_STAGES: list = field(default_factory=lambda: [
        (113, (64, 90), 1),
        (90,  (119, 73), 1),
        (73,  (99, 55), 1),
        (55,  None, None),
    ])

    LOW_PICKUP_STAGES: list = field(default_factory=lambda: [
        (113, (64, 90), 1),
        (90,  None, None),
    ])

    HIGH_PICKUP_PATH: list = field(default_factory=lambda: [(81, False), (127, False), (100, False)])
    LOW_PICKUP_PATH: list = field(default_factory=lambda: [(146, True)])

    # ── Nudge DeadZone / Loop / Timeout ──
    MIDDLE_X: Tuple[int, int] = (95, 100)
    DEAD_BAND: int = 5
    TIMEOUT_S: int = 10

    # 사냥 여부
    HUNT: bool = False

    # Misc 확률 이벤트
    MISC_JITTER_PROB: float = 0.00
    MISC_JITTER_COOLDOWN: float = 0.5
    MISC_JITTER_KEYS: List[str] = field(default_factory=lambda: ['space', 'alt'])

    # ── main.py ──
    BASE_DIR: Optional[str] = None
    INNER_CROP_PX: Tuple[int, int, int, int] = (0, 0, 200, 120)

    # ── capture_pw.py (Telegram) ──
    SET_TELEGRAM: bool = True
    TELEGRAM_BOT: str = ""
    CHAT_ID: str = ""

    def to_serializable(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Config":
        base = Config()
        merged: Dict[str, Any] = {}
        for field_name in base.__dataclass_fields__.keys():
            merged[field_name] = data.get(field_name, getattr(base, field_name))

        def _tuple2float(v):
            if isinstance(v, (list, tuple)) and len(v) == 2:
                return (float(v[0]), float(v[1]))
            raise ValueError("범위값은 [min,max] 형태여야 합니다.")

        def _tuple2int(v):
            if isinstance(v, (list, tuple)) and len(v) == 2:
                return (int(float(v[0])), int(float(v[1])))
            raise ValueError("픽셀 범위는 [min,max] 형태여야 합니다.")

        for k in [
            "PRESS_INTERVAL_RANGE","X_MOVE_INTERVAL_RANGE","SPECIAL_KEY_GAP",
            "HIGH_PICK_UP_INTERVAL_RANGE","LOW_PICK_UP_INTERVAL_RANGE"
        ]:
            merged[k] = _tuple2float(merged[k])

        # ✨ 여기!
        merged["TARGET_Y"] = _tuple2int(merged["TARGET_Y"])
        merged["PIT_Y"] = int(merged.get("PIT_Y", base.PIT_Y))
        merged["DEAD_BAND"] = int(merged["DEAD_BAND"])
        merged["TIMEOUT_S"] = int(merged["TIMEOUT_S"])
        merged["SKILL_RADIUS"] = int(merged.get("SKILL_RADIUS", base.SKILL_RADIUS))
        merged["HUNT"] = bool(merged["HUNT"])
        merged["SET_USER_ALERT"] = bool(merged.get("SET_USER_ALERT", base.SET_USER_ALERT))

        # 튜플/리스트
        mx = merged["MIDDLE_X"]
        if not (isinstance(mx, (list, tuple)) and len(mx) == 2):
            raise ValueError("MIDDLE_X는 (minX,maxX) 2정수여야 합니다.")
        merged["MIDDLE_X"] = (int(mx[0]), int(mx[1]))

        ic = merged["INNER_CROP_PX"]
        if not (isinstance(ic, (list, tuple)) and len(ic) == 4):
            raise ValueError("INNER_CROP_PX는 (left, top, right, bottom) 4정수여야 합니다.")
        merged["INNER_CROP_PX"] = (int(ic[0]), int(ic[1]), int(ic[2]), int(ic[3]))

        # 리스트/표 검증
        def _validate_task(row):
            if not (isinstance(row, (list, tuple)) and len(row) == 5):
                raise ValueError("TASK_SPECS 각 항목은 (type, value, (min,max), enabled, mode) 이어야 합니다.")
            t, val, rng, en, mode = row
            if not isinstance(t, str) or not isinstance(val, str) or not isinstance(mode, str):
                raise ValueError("TASK_SPECS: type/value/mode는 문자열이어야 합니다.")
            if not (isinstance(rng, (list, tuple)) and len(rng) == 2):
                raise ValueError("TASK_SPECS: 간격은 (min,max) 튜플이어야 합니다.")
            float(rng[0]); float(rng[1])
            if not isinstance(en, bool):
                raise ValueError("TASK_SPECS: enabled는 bool이어야 합니다.")
            return (t, val, (float(rng[0]), float(rng[1])), bool(en), mode)

        merged["TASK_SPECS"] = [_validate_task(r) for r in merged["TASK_SPECS"]]

        def _validate_stage(row):
            if not (isinstance(row, (list, tuple)) and len(row) == 3):
                raise ValueError("STAGES 항목은 (y1, (x,y)|None, type|None) 이어야 합니다.")
            y1, pair, type = row
            y1 = int(y1)
            if pair is None:
                pair_ok = None
            else:
                if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                    raise ValueError("STAGES: (x,y)는 길이 2여야 합니다.")
                pair_ok = (int(pair[0]), int(pair[1]))
            if type is None:
                type_ok = None
            else:
                type_ok = int(type)
            return (y1, pair_ok, type_ok)

        merged["HIGH_PICKUP_STAGES"] = [_validate_stage(r) for r in merged["HIGH_PICKUP_STAGES"]]
        merged["LOW_PICKUP_STAGES"]  = [_validate_stage(r) for r in merged["LOW_PICKUP_STAGES"]]

        def _normalize_path_with_flag(seq):
            out = []
            for v in seq:
                # 허용: 146  또는  [146, true]  또는  (146, True)
                if isinstance(v, (list, tuple)):
                    if len(v) == 2:
                        y = int(v[0]); flag = bool(v[1])
                        out.append((y, flag))
                    elif len(v) == 1:
                        out.append((int(v[0]), True))
                    else:
                        raise ValueError("PICKUP_PATH 항목은 (x) 또는 (x, enabled)여야 합니다.")
                elif isinstance(v, (int, float, str)):
                    out.append((int(float(v)), True))
                else:
                    raise ValueError("PICKUP_PATH에 지원되지 않는 형식이 있습니다.")
            return out

        merged["HIGH_PICKUP_PATH"] = _normalize_path_with_flag(merged["HIGH_PICKUP_PATH"])
        merged["LOW_PICKUP_PATH"]  = _normalize_path_with_flag(merged["LOW_PICKUP_PATH"])

        # Misc 확률
        merged["MISC_JITTER_PROB"] = float(merged["MISC_JITTER_PROB"])
        merged["MISC_JITTER_COOLDOWN"] = float(merged["MISC_JITTER_COOLDOWN"])
        keys = merged["MISC_JITTER_KEYS"]
        if isinstance(keys, str):
            keys = [s.strip() for s in keys.split(",") if s.strip()]
        merged["MISC_JITTER_KEYS"] = [str(k) for k in list(keys)]

        # BASE_DIR
        bd = merged["BASE_DIR"]
        merged["BASE_DIR"] = None if (bd is None or str(bd).strip()=="") else str(bd)

        # Telegram
        merged["SET_TELEGRAM"] = bool(merged["SET_TELEGRAM"])
        merged["TELEGRAM_BOT"] = str(merged["TELEGRAM_BOT"] or "")
        merged["CHAT_ID"] = str(merged["CHAT_ID"] or "")

        # ── DEBUG / MONSTER_BAND / CHAT_CROP / IMSHOW / ATTACK ──
        merged["DEBUG"] = bool(merged.get("DEBUG", base.DEBUG))

        merged["MONSTER_BAND_TOP"] = float(merged.get("MONSTER_BAND_TOP", base.MONSTER_BAND_TOP))
        merged["MONSTER_BAND_BOTTOM"] = float(merged.get("MONSTER_BAND_BOTTOM", base.MONSTER_BAND_BOTTOM))

        cc = merged.get("CHAT_CROP_PX", base.CHAT_CROP_PX)
        if not (isinstance(cc, (list, tuple)) and len(cc) == 4):
            raise ValueError("CHAT_CROP_PX는 (left, top, right, bottom) 4정수여야 합니다.")
        merged["CHAT_CROP_PX"] = (int(cc[0]), int(cc[1]), int(cc[2]), int(cc[3]))

        merged["IMSHOW_SCALE"] = int(merged.get("IMSHOW_SCALE", base.IMSHOW_SCALE))
        merged["ATTACK_FOR_SEC"] = int(merged.get("ATTACK_FOR_SEC", base.ATTACK_FOR_SEC))

        return Config(**merged)

# =========================
# 공용 위젯들
# =========================
class RangeEntry(ttk.Frame):
    LABEL_MIN = 180
    ENTRY_MIN = 120
    GAP_MIN   = 18
    UNIT_MIN  = 26
    def __init__(self, master, label: str, default: Tuple[float, float], unit: str="초"):
        super().__init__(master)
        self.unit = unit

        self.columnconfigure(0, minsize=self.LABEL_MIN)
        self.columnconfigure(1, weight=1, minsize=self.ENTRY_MIN)
        self.columnconfigure(2, minsize=self.GAP_MIN)
        self.columnconfigure(3, weight=1, minsize=self.ENTRY_MIN)
        self.columnconfigure(4, minsize=self.UNIT_MIN)

        self.label_text = label
        self.var_min = tk.StringVar(value=str(default[0]))
        self.var_max = tk.StringVar(value=str(default[1]))

        ttk.Label(self, text=label).grid(row=0, column=0, sticky="w", padx=(0,12), pady=2)

        self.entry_min = ttk.Entry(self, textvariable=self.var_min, width=10, justify="right")
        self.entry_min.grid(row=0, column=1, sticky="ew", padx=(0,8), pady=2)

        ttk.Label(self, text=" ~ ").grid(row=0, column=2, sticky="w", padx=(0,8), pady=2)

        self.entry_max = ttk.Entry(self, textvariable=self.var_max, width=10, justify="right")
        self.entry_max.grid(row=0, column=3, sticky="ew", padx=(0,8), pady=2)

        ttk.Label(self, text=self.unit).grid(row=0, column=4, sticky="w", padx=(0,0), pady=2)

    def get(self) -> Tuple[float, float]:
        try:
            mn = float(self.var_min.get().strip())
            mx = float(self.var_max.get().strip())
        except ValueError:
            raise ValueError(f"[{self.label_text}] 숫자를 입력하세요.")
        if mn > mx:
            raise ValueError(f"[{self.label_text}] 최소값({mn})이 최대값({mx})보다 큽니다.")
        if mn < 0 or mx < 0:
            raise ValueError(f"[{self.label_text}] 음수는 허용되지 않습니다.")
        return (mn, mx)

    def set(self, val: Tuple[float, float]):
        self.var_min.set(str(val[0]))
        self.var_max.set(str(val[1]))

class SingleIntEntry(ttk.Frame):
    def __init__(self, master, label: str, default: int, unit: str = ""):
        super().__init__(master)
        self.label_text = label
        self.var = tk.StringVar(value=str(default))
        ttk.Label(self, text=label).pack(side="left", padx=(0,8))
        ttk.Entry(self, textvariable=self.var, width=10, justify="right").pack(side="left")
        if unit: ttk.Label(self, text=unit).pack(side="left", padx=(6,0))
    def get(self) -> int:
        return int(float(self.var.get().strip()))
    def set(self, v: int):
        self.var.set(str(int(v)))

class SingleFloatEntry(ttk.Frame):
    def __init__(self, master, label: str, default: float, unit: str = ""):
        super().__init__(master)
        self.label_text = label
        self.var = tk.StringVar(value=str(default))
        ttk.Label(self, text=label).pack(side="left", padx=(0,8))
        ttk.Entry(self, textvariable=self.var, width=10, justify="right").pack(side="left")
        if unit: ttk.Label(self, text=unit).pack(side="left", padx=(6,0))
    def get(self) -> float:
        return float(self.var.get().strip())
    def set(self, v: float):
        self.var.set(str(float(v)))

class BoolEntry(ttk.Frame):
    def __init__(self, master, label: str, default: bool):
        super().__init__(master)
        self.var = tk.BooleanVar(value=bool(default))
        ttk.Checkbutton(self, text=label, variable=self.var).pack(anchor="w")
    def get(self) -> bool:
        return bool(self.var.get())
    def set(self, v: bool):
        self.var.set(bool(v))

class Tuple2IntEntry(ttk.Frame):
    def __init__(self, master, label: str, default: Tuple[int,int], unit:str=""):
        super().__init__(master)
        self.label_text = label
        self.v1 = tk.StringVar(value=str(default[0]))
        self.v2 = tk.StringVar(value=str(default[1]))
        ttk.Label(self, text=label).grid(row=0, column=0, padx=(0,8), sticky="w")
        ttk.Entry(self, textvariable=self.v1, width=8, justify="right").grid(row=0, column=1)
        ttk.Label(self, text=",").grid(row=0, column=2, padx=4)
        ttk.Entry(self, textvariable=self.v2, width=8, justify="right").grid(row=0, column=3)
        if unit: ttk.Label(self, text=unit).grid(row=0, column=4, padx=(6,0))
    def get(self)->Tuple[int,int]:
        return (int(float(self.v1.get().strip())), int(float(self.v2.get().strip())))
    def set(self, val:Tuple[int,int]):
        self.v1.set(str(int(val[0]))); self.v2.set(str(int(val[1])))

class Tuple4IntEntry(ttk.Frame):
    def __init__(self, master, label: str, default: Tuple[int,int,int,int], unit:str=""):
        super().__init__(master)
        self.label_text=label
        self.v = [tk.StringVar(value=str(x)) for x in default]
        ttk.Label(self, text=label).grid(row=0, column=0, padx=(0,8), sticky="w")
        for i in range(4):
            ttk.Entry(self, textvariable=self.v[i], width=8, justify="right").grid(row=0, column=1+2*i)
            if i<3: ttk.Label(self, text=",").grid(row=0, column=2+2*i, padx=4)
        if unit: ttk.Label(self, text=unit).grid(row=0, column=9, padx=(6,0))
    def get(self)->Tuple[int,int,int,int]:
        return tuple(int(float(s.get().strip())) for s in self.v)  # type: ignore
    def set(self, val:Tuple[int,int,int,int]):
        for i in range(4): self.v[i].set(str(int(val[i])))

class StringEntry(ttk.Frame):
    def __init__(self, master, label: str, default: str, width:int=34, placeholder:str=""):
        super().__init__(master)
        self.var = tk.StringVar(value=str(default or ""))
        ttk.Label(self, text=label).pack(side="left", padx=(0,8))
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        if placeholder:
            self.entry.insert(0, self.entry.get() or placeholder)
    def get(self)->str:
        return str(self.var.get())
    def set(self, v:str):
        self.var.set("" if v is None else str(v))

class StringListEntry(ttk.Frame):
    def __init__(self, master, label:str, default:List[str], width:int=34):
        super().__init__(master)
        self.var = tk.StringVar(value=",".join(default))
        ttk.Label(self, text=label).pack(side="left", padx=(0,8))
        ttk.Entry(self, textvariable=self.var, width=width).pack(side="left", fill="x", expand=True)
        ttk.Label(self, text="(쉼표로 구분)").pack(side="left", padx=(6,0))
    def get(self)->List[str]:
        return [s.strip() for s in str(self.var.get()).split(",") if s.strip()]
    def set(self, vals:List[str]):
        self.var.set(",".join(vals))

# =========================
# 표 에디터(완전 교체 버전)
# =========================
class RowDialog(tk.Toplevel):
    """
    행 추가/수정 다이얼로그.
    fields: [{"name":..., "type":"int|float|bool|str|combo", "choices":[...], "default": ...}, ...]
    확인 시 self.result(dict)를 반환하고 각 필드는 지정된 type에 맞게 즉시 캐스팅됨.
    """
    def __init__(self, master, title: str, fields: List[Dict[str, Any]], init_values: Dict[str, Any] = None):
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.resizable(False, False)
        self.result = None

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)

        self.vars: Dict[str, Any] = {}
        self._field_types: Dict[str, str] = {}
        self._field_choices: Dict[str, List[str]] = {}

        row = 0
        for spec in fields:
            f_type = spec.get("type", "str")
            name = spec["name"]
            label = spec.get("label", name)
            choices = spec.get("choices")
            default = (init_values or {}).get(name, spec.get("default"))

            self._field_types[name] = f_type
            if choices:
                self._field_choices[name] = choices

            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", padx=(0,8), pady=4)

            if f_type == "bool":
                var = tk.BooleanVar(value=bool(default))
                w = ttk.Checkbutton(body, variable=var)
                w.grid(row=row, column=1, sticky="w")
            elif f_type == "combo":
                var = tk.StringVar(value=str(default) if default is not None else "")
                w = ttk.Combobox(body, textvariable=var, values=choices, state="readonly")
                w.grid(row=row, column=1, sticky="ew")
            else:
                var = tk.StringVar(value="" if default is None else str(default))
                w = ttk.Entry(body, textvariable=var, width=18, justify="right")
                w.grid(row=row, column=1, sticky="ew")

            self.vars[name] = var
            row += 1

        body.columnconfigure(1, weight=1)

        btns = ttk.Frame(self, padding=(12,0,12,12))
        btns.pack(fill="x")
        ttk.Button(btns, text="확인", command=self.on_ok).pack(side="right")
        ttk.Button(btns, text="취소", command=self.on_cancel).pack(side="right", padx=(0,8))

        # 단축키
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

        self.grab_set()
        self.wait_visibility()
        self.focus()
        self.lift()

    def _cast_value(self, name: str, val_any) -> Any:
        """fields의 type에 따라 즉시 캐스팅."""
        ftype = self._field_types.get(name, "str")
        # tk.Variable이면 .get(), 아니면 그대로
        val = val_any.get() if isinstance(val_any, tk.Variable) else val_any
        s = "" if val is None else str(val).strip()

        try:
            if ftype == "int":
                return int(float(s)) if s != "" else 0
            elif ftype == "float":
                return float(s) if s != "" else 0.0
            elif ftype == "bool":
                if isinstance(val_any, tk.BooleanVar):
                    return bool(val_any.get())
                return s.lower() in ("1","true","y","yes","on")
            elif ftype == "combo":
                choices = self._field_choices.get(name)
                return s if (not choices or s in choices) else s
            else:
                return s
        except Exception:
            return s

    def on_ok(self):
        out = {}
        for k, v in self.vars.items():
            out[k] = self._cast_value(k, v)
        self.result = out
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

class TableEditor(ttk.Frame):
    """
    범용 테이블 에디터.
    columns: [
        {
            "key": "y1",
            "label": "y1(px)",
            "width": 90,
            "anchor": "center",
            "editor": {"name":"y1","type":"int","default":"113"}
        },
        ...
    ]
    row_to_values(py_row) -> [str,...] : 파이썬 자료 → 트리뷰 표시 문자열들
    values_to_row(str_values) -> py_row : 트리뷰 문자열들 → 파이썬 자료
    """
    def __init__(self, master, columns: List[Dict[str, Any]], title: str, row_to_values, values_to_row):
        super().__init__(master)
        self.columns_spec = columns
        self.row_to_values = row_to_values
        self.values_to_row = values_to_row

        ttk.Label(self, text=title, font=("", 11, "bold")).pack(anchor="w", pady=(0,6))

        cols = [c["key"] for c in columns]
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=8, selectmode="browse")
        for c in columns:
            self.tree.heading(c["key"], text=c.get("label", c["key"]))
            self.tree.column(
                c["key"],
                width=c.get("width", 100),
                anchor=c.get("anchor", "center"),
                stretch=True
            )
        self.tree.pack(fill="x", expand=False)

        # 더블클릭: 클릭 위치의 행을 식별 → 선택 후 편집
        def _on_dbl(e):
            row = self.tree.identify_row(e.y)
            if row:
                self.tree.selection_set(row)
                self.tree.focus(row)
                self.on_edit()
        self.tree.bind("<Double-1>", _on_dbl)

        # 단축키
        self.tree.bind("<Return>", lambda e: self.on_edit())
        self.tree.bind("<Delete>", lambda e: self.on_delete())

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="추가", command=self.on_add).pack(side="left")
        ttk.Button(btns, text="수정", command=self.on_edit).pack(side="left", padx=6)
        ttk.Button(btns, text="삭제", command=self.on_delete).pack(side="left")

    def load_data(self, py_rows: list):
        self.tree.delete(*self.tree.get_children())
        for r in py_rows:
            self.tree.insert("", "end", values=self.row_to_values(r))

    def get_all_rows(self) -> list:
        out = []
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            try:
                out.append(self.values_to_row(vals))
            except Exception as e:
                messagebox.showerror("테이블 변환 오류", f"values_to_row 변환 중 오류:\n{e}")
                # 실패 행은 스킵하거나, 원문을 그대로 넣고 싶으면 아래 주석 해제
                # out.append(vals)
        return out

    def _open_editor(self, title: str, init_values: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        dlg = RowDialog(self, title, [c["editor"] for c in self.columns_spec], init_values=init_values)
        # 다이얼로그가 닫힐 때까지 블록
        self.wait_window(dlg)
        return dlg.result

    def on_add(self):
        res = self._open_editor("추가")
        if res is None:
            return
        # 결과를 컬럼 순서대로 문자열화하여 트리에 넣기 (표시는 문자열이므로)
        vals = []
        for c in self.columns_spec:
            name = c["editor"]["name"]
            v = res.get(name, "")
            vals.append("" if v is None else str(v))
        self.tree.insert("", "end", values=vals)

    def on_edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        cur_vals = list(self.tree.item(iid, "values"))
        init = {}
        # 트리뷰의 현재 문자열 값을 에디터 초기값에 주입
        for i, c in enumerate(self.columns_spec):
            init[c["editor"]["name"]] = cur_vals[i]

        res = self._open_editor("수정", init_values=init)
        if res is None:
            return

        new_vals = []
        for c in self.columns_spec:
            name = c["editor"]["name"]
            v = res.get(name, "")
            new_vals.append("" if v is None else str(v))
        self.tree.item(iid, values=new_vals)

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            self.tree.delete(iid)

# =========================
# 메인 앱
# =========================
class App(tk.Tk):
    def __init__(self, default_path=None):
        super().__init__()
        self.default_save_path = default_path  # ← 기본 저장 파일 경로 기억
        self.lift()
        self.title("Chrome")
        self.geometry("1000x820"); self.minsize(960, 760)

        style = ttk.Style()
        if platform.system() == "Darwin" and "aqua" in style.theme_names():
            style.theme_use("aqua")
            try: self.tk.call("tk", "scaling", 2.0)
            except Exception: pass

        container = ttk.Frame(self, padding=14); container.pack(fill="both", expand=True)
        nb = ttk.Notebook(container); nb.pack(fill="both", expand=True)

        # ------- 탭 1: 기본 범위/좌표 -------
        tab_basic = ttk.Frame(nb); nb.add(tab_basic, text="기본 설정")
        ttk.Label(tab_basic, text="범위(초)와 목표 좌표(px)를 설정하세요.", foreground="red", font=("", 9, "bold")).pack(anchor="w", pady=(8,8), padx=8)
        frm = ttk.Frame(tab_basic); frm.pack(fill="x", padx=8)
        self.default_cfg = Config()
        self.widgets: Dict[str, Any] = {}

            
        def add_range(label, key):
            w = RangeEntry(frm, label, getattr(self.default_cfg, key))
            w.pack(fill="x", padx=12, pady=6); self.widgets[key] = w

        add_range("CTRL 입력 주기", "PRESS_INTERVAL_RANGE")
        add_range("랜덤 이동 주기", "X_MOVE_INTERVAL_RANGE")
        add_range("특수키 간격", "SPECIAL_KEY_GAP")
        add_range("상단 이동 간격", "HIGH_PICK_UP_INTERVAL_RANGE")
        add_range("하단 이동 간격", "LOW_PICK_UP_INTERVAL_RANGE")

        xyfrm = ttk.Frame(tab_basic); xyfrm.pack(fill="x", padx=8, pady=6)

        # ✨ TARGET_Y를 범위 입력으로
        sy = RangeEntry(xyfrm, "목표 Y", self.default_cfg.TARGET_Y, unit="px")
        sy.pack(side="left")
        self.widgets["TARGET_Y"] = sy

        sy2 = SingleIntEntry(xyfrm, "PIT Y", self.default_cfg.PIT_Y, "px")
        sy2.pack(side="left", padx=(12,0))
        self.widgets["PIT_Y"] = sy2

        # 하단 버튼 + 미리보기
        btm = ttk.Frame(tab_basic); btm.pack(fill="x", padx=8, pady=(8,8))
        ttk.Button(btm, text="샘플 생성", command=self.preview_sample).pack(side="left")
        ttk.Button(btm, text="JSON 저장", command=self.save_json).pack(side="left")
        ttk.Button(btm, text="JSON 불러오기", command=self.load_json).pack(side="left", padx=8)
        if self.default_save_path:
            ttk.Button(btm, text=f"빠른 저장({self.default_save_path.name})",
                        command=lambda: self.save_json(self.default_save_path)).pack(side="left", padx=8)
            ttk.Button(btm, text="앱 기본 불러오기",
                        command=lambda: self.load_json(self.default_save_path)).pack(side="left")
        ttk.Button(btm, text="기본값 복원", command=self.reset_defaults).pack(side="right")
        

        self.preview_box = tk.Text(tab_basic, height=10, wrap="word")
        self.preview_box.pack(fill="both", expand=True, padx=8, pady=(4,8))
        if platform.system() == "Darwin":
            self.preview_box.configure(background="white", foreground="black", insertbackground="black")
        self.preview_box.insert("end", "여기에 샘플 출력이 표시됩니다.\n")

        # ------- 탭 2: TASK_SPECS -------
        tab_task = ttk.Frame(nb); nb.add(tab_task, text="SCHEDULE")
        self.task_editor = TableEditor(
            tab_task,
            columns=[
                {"key":"type",   "label":"type",   "width":90,  "editor":{"name":"type","type":"str","default":"key"}},
                {"key":"value",  "label":"value",  "width":120, "editor":{"name":"value","type":"str","default":"pagedown"}},
                {"key":"min",    "label":"min(s)", "width":90,  "editor":{"name":"min","type":"float","default":"60"}},
                {"key":"max",    "label":"max(s)", "width":90,  "editor":{"name":"max","type":"float","default":"80"}},
                {"key":"enabled","label":"enabled","width":90,  "editor":{"name":"enabled","type":"bool","default":True}},
                {"key":"mode",   "label":"mode",   "width":100, "editor":{"name":"mode","type":"combo","choices":["async","unsync"],"default":"async"}},
            ],
            title="키/작업 스펙",
            row_to_values=lambda row: [row[0], row[1], str(row[2][0]), str(row[2][1]), "True" if row[3] else "False", row[4]],
            values_to_row=lambda vals: (str(vals[0]), str(vals[1]), (float(vals[2]), float(vals[3])),
                                        True if str(vals[4]).lower() in ("true","1","yes","y") else False, str(vals[5]))
        )
        self.task_editor.pack(fill="x", padx=8, pady=8)

        # ------- 탭 3: STAGES (HIGH / LOW) -------
        tab_stage = ttk.Frame(nb); nb.add(tab_stage, text="STAGES")
        ttk.Label(tab_stage, text="HIGH_STAGES (마지막은 y1만 작성 必)", font=("", 11, "bold")).pack(anchor="w", padx=8, pady=(8,0))
        self.high_stage_editor = TableEditor(
            tab_stage,
            columns=[
                {"key":"y1",     "label":"y1(px)",   "width":90,  "editor":{"name":"y1","type":"int","default":"113"}},
                {"key":"rope_x", "label":"rope_x(px)","width":100, "editor":{"name":"rope_x","type":"int","default":"64"}},
                {"key":"y2",     "label":"y2(px)",   "width":90,  "editor":{"name":"y2","type":"int","default":"90"}},
                {"key":"type",    "label":"type",      "width":90,  "editor":{"name":"type","type":"int","default":"1"}},
            ],
            title="",
            row_to_values=lambda row: [str(row[0]), "" if row[1] is None else str(row[1][0]),
                                       "" if row[1] is None else str(row[1][1]), "" if row[2] is None else str(row[2])],
            values_to_row=lambda vals: (int(float(vals[0])) if str(vals[0]).strip()!="" else 0,
                                        None if (str(vals[1]).strip()=="" and str(vals[2]).strip()=="")
                                        else (int(float(vals[1])), int(float(vals[2]))),
                                        None if str(vals[3]).strip()=="" else float(vals[3]))
        )
        self.high_stage_editor.pack(fill="x", padx=8, pady=(0,12))

        ttk.Label(tab_stage, text="LOW_STAGES (마지막은 y1만 작성 必)", font=("", 11, "bold")).pack(anchor="w", padx=8)
        self.low_stage_editor = TableEditor(
            tab_stage,
            columns=[
                {"key":"y1",     "label":"y1(px)",   "width":90,  "editor":{"name":"y1","type":"int","default":"113"}},
                {"key":"rope_x", "label":"rope_x(px)","width":100, "editor":{"name":"rope_x","type":"int","default":"64"}},
                {"key":"y2",     "label":"y2(px)",   "width":90,  "editor":{"name":"y2","type":"int","default":"90"}},
                {"key":"type",    "label":"type",      "width":90,  "editor":{"name":"type","type":"int","default":"1"}},
            ],
            title="",
            row_to_values=lambda row: [str(row[0]), "" if row[1] is None else str(row[1][0]),
                                       "" if row[1] is None else str(row[1][1]), "" if row[2] is None else str(row[2])],
            values_to_row=lambda vals: (int(float(vals[0])) if str(vals[0]).strip()!="" else 0,
                                        None if (str(vals[1]).strip()=="" and str(vals[2]).strip()=="")
                                        else (int(float(vals[1])), int(float(vals[2]))),
                                        None if str(vals[3]).strip()=="" else float(vals[3]))
        )
        self.low_stage_editor.pack(fill="x", padx=8, pady=(0,8))

        # ------- 탭 4: PATHS -------
        tab_path = ttk.Frame(nb); nb.add(tab_path, text="PATHS")
        self.high_path_editor = TableEditor(
            tab_path,
            columns=[
                {"key":"x",       "label":"TOP_DOWN_PATH (x px)", "width":180, "editor":{"name":"x","type":"int","default":"146"}},
                {"key":"jump", "label":"jump",                "width":100, "editor":{"name":"jump","type":"bool","default":True}},
            ],
            title="TOP_DOWN_PATH",
            row_to_values=lambda row: [str(row[0]), "True" if (len(row)>1 and bool(row[1])) else "False"],
            values_to_row=lambda vals: (int(float(vals[0])) if str(vals[0]).strip()!="" else 0,
                                        True if str(vals[1]).lower() in ("true","1","yes","y","on") else False)
        )
        self.high_path_editor.pack(fill="x", padx=8, pady=(8,12))
        self.low_path_editor = TableEditor(
            tab_path,
            columns=[
                {"key":"x",       "label":"BOTTOM_UP_PATH (x px)", "width":180, "editor":{"name":"x","type":"int","default":"146"}},
                {"key":"jump", "label":"jump",                "width":100, "editor":{"name":"jump","type":"bool","default":True}},
            ],
            title="BOTTOM_UP_PATH",
            row_to_values=lambda row: [str(row[0]), "True" if (len(row)>1 and bool(row[1])) else "False"],
            values_to_row=lambda vals: (int(float(vals[0])) if str(vals[0]).strip()!="" else 0,
                                        True if str(vals[1]).lower() in ("true","1","yes","y","on") else False)
        )
        self.low_path_editor.pack(fill="x", padx=8, pady=(0,8))

        # ------- 탭 5: Nudge/Loop/Timeout/Hunt/Misc -------
        tab_nudge = ttk.Frame(nb); nb.add(tab_nudge, text="NUDGE & MISC")
        block1 = ttk.LabelFrame(tab_nudge, text="Nudge DeadZone / Loop / Timeout"); block1.pack(fill="x", padx=8, pady=(8,6))
        self.widgets["MIDDLE_X"] = Tuple2IntEntry(block1, "X 좌표", self.default_cfg.MIDDLE_X, "px"); self.widgets["MIDDLE_X"].pack(fill="x", padx=8, pady=4)
        rowA = ttk.Frame(block1); rowA.pack(fill="x", padx=8, pady=4)
        self.widgets["DEAD_BAND"] = SingleIntEntry(rowA, "DEAD_BAND (± 반폭)", self.default_cfg.DEAD_BAND, "px"); self.widgets["DEAD_BAND"].pack(side="left", padx=(0,12))
        rowB = ttk.Frame(block1); rowB.pack(fill="x", padx=8, pady=4)
        self.widgets["TIMEOUT_S"] = SingleIntEntry(rowB, "TIMEOUT_S", self.default_cfg.TIMEOUT_S, "s"); self.widgets["TIMEOUT_S"].pack(side="left", padx=(0,12))

        block2 = ttk.LabelFrame(tab_nudge, text="사냥 이벤트"); block2.pack(fill="x", padx=8, pady=(6,8))
        self.widgets["HUNT"] = BoolEntry(block2, "HUNT (사냥 모드)", self.default_cfg.HUNT); self.widgets["HUNT"].pack(anchor="w", padx=8, pady=6)
        row_skill = ttk.Frame(block2)
        row_skill.pack(fill="x", padx=8, pady=4)

        self.widgets["SKILL_RADIUS"] = SingleIntEntry(row_skill,"스킬 반경",self.default_cfg.SKILL_RADIUS,"px")
        self.widgets["SKILL_RADIUS"].pack(side="left")
        
        block5 = ttk.LabelFrame(tab_nudge, text="확률 이벤트"); block5.pack(fill="x", padx=8, pady=(6,8))
        rowC = ttk.Frame(block5); rowC.pack(fill="x", padx=8, pady=4)

        self.widgets["MISC_JITTER_PROB"] = SingleFloatEntry(rowC, "확률", self.default_cfg.MISC_JITTER_PROB); self.widgets["MISC_JITTER_PROB"].pack(side="left", padx=(0,12))
        self.widgets["MISC_JITTER_COOLDOWN"] = SingleFloatEntry(rowC, "확률 평가 주기", self.default_cfg.MISC_JITTER_COOLDOWN, "s"); self.widgets["MISC_JITTER_COOLDOWN"].pack(side="left")
        self.widgets["MISC_JITTER_KEYS"] = StringListEntry(block5, "확률 이벤트", self.default_cfg.MISC_JITTER_KEYS); self.widgets["MISC_JITTER_KEYS"].pack(fill="x", padx=8, pady=4)

        # === 여기부터 추가 ===
        block_dbg = ttk.LabelFrame(tab_nudge, text="DEBUG / 몬스터 밴드"); 
        block_dbg.pack(fill="x", padx=8, pady=(6,8))

        self.widgets["DEBUG"] = BoolEntry(block_dbg, "DEBUG 모드", self.default_cfg.DEBUG)
        self.widgets["DEBUG"].pack(anchor="w", padx=8, pady=4)

        row_band = ttk.Frame(block_dbg); row_band.pack(fill="x", padx=8, pady=4)
        self.widgets["MONSTER_BAND_TOP"] = SingleFloatEntry(row_band, "MONSTER_BAND_TOP", self.default_cfg.MONSTER_BAND_TOP, "px")
        self.widgets["MONSTER_BAND_TOP"].pack(side="left", padx=(0,12))
        self.widgets["MONSTER_BAND_BOTTOM"] = SingleFloatEntry(row_band, "MONSTER_BAND_BOTTOM", self.default_cfg.MONSTER_BAND_BOTTOM, "px")
        self.widgets["MONSTER_BAND_BOTTOM"].pack(side="left")

        block_chat = ttk.LabelFrame(tab_nudge, text="캡처 / 공격 설정")
        block_chat.pack(fill="x", padx=8, pady=(6,8))

        self.widgets["CHAT_CROP_PX"] = Tuple4IntEntry(block_chat, "CHAT_CROP (L,T,R,B)", self.default_cfg.CHAT_CROP_PX, "px")
        self.widgets["CHAT_CROP_PX"].pack(fill="x", padx=8, pady=4)

        row_im = ttk.Frame(block_chat); row_im.pack(fill="x", padx=8, pady=4)
        self.widgets["IMSHOW_SCALE"] = SingleIntEntry(row_im, "IMSHOW_SCALE", self.default_cfg.IMSHOW_SCALE, "%")
        self.widgets["IMSHOW_SCALE"].pack(side="left", padx=(0,12))

        self.widgets["ATTACK_FOR_SEC"] = SingleIntEntry(row_im, "ATTACK_FOR_SEC", self.default_cfg.ATTACK_FOR_SEC, "s")
        self.widgets["ATTACK_FOR_SEC"].pack(side="left")
        # === 추가 끝 ===
        
        # ------- 탭 6: main.py / capture_pw.py -------
        tab_files = ttk.Frame(nb); nb.add(tab_files, text="DIR & TELEGRAM")
        block3 = ttk.LabelFrame(tab_files, text="DIR"); block3.pack(fill="x", padx=8, pady=(8,6))
        self.widgets["BASE_DIR"] = StringEntry(block3, "DIR (비우면 None)", self.default_cfg.BASE_DIR or "", width=40); self.widgets["BASE_DIR"].pack(fill="x", padx=8, pady=6)
        self.widgets["INNER_CROP_PX"] = Tuple4IntEntry(block3, "미니맵 (L,T,R,B)", self.default_cfg.INNER_CROP_PX, "px"); self.widgets["INNER_CROP_PX"].pack(fill="x", padx=8, pady=6)
        block4 = ttk.LabelFrame(tab_files, text="Telegram"); block4.pack(fill="x", padx=8, pady=(6,8))
        self.widgets["SET_TELEGRAM"] = BoolEntry(block4, "SET_TELEGRAM", self.default_cfg.SET_TELEGRAM); self.widgets["SET_TELEGRAM"].pack(anchor="w", padx=8, pady=6)
        self.widgets["SET_USER_ALERT"] = BoolEntry(block4, "유저 인입 알림", self.default_cfg.SET_USER_ALERT);self.widgets["SET_USER_ALERT"].pack(anchor="w", padx=8, pady=6)
        self.widgets["TELEGRAM_BOT"] = StringEntry(block4, "BOT", self.default_cfg.TELEGRAM_BOT, width=46); self.widgets["TELEGRAM_BOT"].pack(fill="x", padx=8, pady=4)
        self.widgets["CHAT_ID"] = StringEntry(block4, "ID", self.default_cfg.CHAT_ID, width=46); self.widgets["CHAT_ID"].pack(fill="x", padx=8, pady=4)

        # 초기 표 데이터 로드
        self.load_defaults_into_tables()

        # 하단 공통 버튼
        bottom = ttk.Frame(container); bottom.pack(fill="x", pady=(10,0))
        ttk.Button(bottom, text="JSON 저장", command=self.save_json).pack(side="left")
        ttk.Button(bottom, text="JSON 불러오기", command=self.load_json).pack(side="left", padx=8)
        ttk.Button(bottom, text="기본값 복원", command=self.reset_defaults).pack(side="right")

    # ---------- 내부 유틸 ----------
    def load_defaults_into_tables(self):
        cfg = self.default_cfg
        self.task_editor.load_data(cfg.TASK_SPECS)
        self.high_stage_editor.load_data(cfg.HIGH_PICKUP_STAGES)
        self.low_stage_editor.load_data(cfg.LOW_PICKUP_STAGES)
        self.high_path_editor.load_data(cfg.HIGH_PICKUP_PATH)
        self.low_path_editor.load_data(cfg.LOW_PICKUP_PATH)

    def collect_config(self) -> Config:
        d: Dict[str, Any] = {}
        # 기본 범위
        for key in ("PRESS_INTERVAL_RANGE","X_MOVE_INTERVAL_RANGE","SPECIAL_KEY_GAP",
                    "HIGH_PICK_UP_INTERVAL_RANGE","LOW_PICK_UP_INTERVAL_RANGE"):
            d[key] = self.widgets[key].get()
        # 좌표
        d["TARGET_Y"] = self.widgets["TARGET_Y"].get()
        d["PIT_Y"] = self.widgets["PIT_Y"].get()  # ← 추가
        # 표
        d["TASK_SPECS"] = self.task_editor.get_all_rows()
        d["HIGH_PICKUP_STAGES"] = self.high_stage_editor.get_all_rows()
        d["LOW_PICKUP_STAGES"]  = self.low_stage_editor.get_all_rows()
        d["HIGH_PICKUP_PATH"]   = self.high_path_editor.get_all_rows()
        d["LOW_PICKUP_PATH"]    = self.low_path_editor.get_all_rows()
        # Nudge/Loop/Timeout/Hunt/Misc
        d["MIDDLE_X"] = self.widgets["MIDDLE_X"].get()
        d["DEAD_BAND"] = self.widgets["DEAD_BAND"].get()
        d["TIMEOUT_S"] = self.widgets["TIMEOUT_S"].get()
        d["HUNT"] = self.widgets["HUNT"].get()
        d["SKILL_RADIUS"] = self.widgets["SKILL_RADIUS"].get()
        d["MISC_JITTER_PROB"] = self.widgets["MISC_JITTER_PROB"].get()
        d["MISC_JITTER_COOLDOWN"] = self.widgets["MISC_JITTER_COOLDOWN"].get()
        d["MISC_JITTER_KEYS"] = self.widgets["MISC_JITTER_KEYS"].get()
        # ── 새로 추가된 항목들 ──
        d["DEBUG"] = self.widgets["DEBUG"].get()
        d["MONSTER_BAND_TOP"] = self.widgets["MONSTER_BAND_TOP"].get()
        d["MONSTER_BAND_BOTTOM"] = self.widgets["MONSTER_BAND_BOTTOM"].get()
        d["CHAT_CROP_PX"] = self.widgets["CHAT_CROP_PX"].get()
        d["IMSHOW_SCALE"] = self.widgets["IMSHOW_SCALE"].get()
        d["ATTACK_FOR_SEC"] = self.widgets["ATTACK_FOR_SEC"].get()
        # main.py / capture_pw.py
        base_dir = self.widgets["BASE_DIR"].get().strip()
        d["BASE_DIR"] = None if base_dir=="" else base_dir
        d["INNER_CROP_PX"] = self.widgets["INNER_CROP_PX"].get()
        d["SET_TELEGRAM"] = self.widgets["SET_TELEGRAM"].get()
        d["TELEGRAM_BOT"] = self.widgets["TELEGRAM_BOT"].get()
        d["CHAT_ID"] = self.widgets["CHAT_ID"].get()
        d["SET_USER_ALERT"] = self.widgets["SET_USER_ALERT"].get()
        return Config.from_dict(d)

    def preview_sample(self):
        try:
            cfg = self.collect_config()
        except Exception as e:
            messagebox.showerror("입력 오류", str(e)); return

        def pick(rng: Tuple[float,float]) -> float:
            if abs(rng[0]-rng[1])<1e-12: return rng[0]
            return round(random.uniform(rng[0], rng[1]), 5)

        lines = [
            "[샘플 미리보기]",
            f"CTRL: {pick(cfg.PRESS_INTERVAL_RANGE)} s",
            f"NUDGE: {pick(cfg.X_MOVE_INTERVAL_RANGE)} s",
            f"NUDGE TIMEOUT: {cfg.TIMEOUT_S}s",
            f"SKILL GAP: {pick(cfg.SPECIAL_KEY_GAP)} s",
            f"상단 이동: {pick(cfg.HIGH_PICK_UP_INTERVAL_RANGE)} s",
            f"하단 이동: {pick(cfg.LOW_PICK_UP_INTERVAL_RANGE)} s",
            f"목표 Y좌표: ({cfg.TARGET_Y})",
            f"구덩이 Y좌표: ({cfg.PIT_Y})",  # ← 변경/추가
            f"사냥 모드: {cfg.HUNT}",
            f"확률 이벤트 : {cfg.MISC_JITTER_PROB*100}%", 
            f"확률 이벤트 판단 주기: {cfg.MISC_JITTER_COOLDOWN}s",
            f"확률 이벤트 키: {cfg.MISC_JITTER_KEYS}",
            f"BASE_DIR: {cfg.BASE_DIR}", 
            f"미니맵(L,T,R,B): {cfg.INNER_CROP_PX}",
            f"TELEGRAM: set={cfg.SET_TELEGRAM}",
            f"bot={'***' if cfg.TELEGRAM_BOT else ''}", 
            f"chat_id={'***' if cfg.CHAT_ID else ''}",
            f"TASK_SPECS count: {len(cfg.TASK_SPECS)}",
            f"HIGH_STAGES: {len(cfg.HIGH_PICKUP_STAGES)}",
            f"LOW_STAGES: {len(cfg.LOW_PICKUP_STAGES)}",
            f"PATHS: HIGH={cfg.HIGH_PICKUP_PATH}",
            f"PATHS: LOW={cfg.LOW_PICKUP_PATH}",
            f"DEBUG: {cfg.DEBUG}",
            f"몬스터 밴드: top={cfg.MONSTER_BAND_TOP}, bottom={cfg.MONSTER_BAND_BOTTOM}",
            f"CHAT_CROP_PX: {cfg.CHAT_CROP_PX}",
            f"IMSHOW_SCALE: {cfg.IMSHOW_SCALE}",
            f"ATTACK_FOR_SEC: {cfg.ATTACK_FOR_SEC}",
        ]
        self.preview_box.delete("1.0","end"); self.preview_box.insert("end", "\n".join(lines)+"\n")

    def save_json(self, to_path: Optional[Path] = None):
        try:
            cfg = self.collect_config()
        except Exception as e:
            messagebox.showerror("입력 오류", str(e))
            return

        # 우선순위: 전달인자 → self.default_save_path → 파일 대화상자
        if to_path is None:
            to_path = self.default_save_path
        if to_path is None:
            p = filedialog.asksaveasfilename(title="설정 저장", defaultextension=".json",
                                            filetypes=[("JSON 파일","*.json")])
            if not p:
                return
            to_path = Path(p)

        try:
            to_path.parent.mkdir(parents=True, exist_ok=True)
            with to_path.open("w", encoding="utf-8") as f:
                json.dump(cfg.to_serializable(), f, ensure_ascii=False, indent=2)
            messagebox.showinfo("저장 완료", str(to_path))
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    def load_json(self, from_path: Optional[Path] = None):
        # 우선순위: 전달인자 → self.default_save_path(존재 시) → 파일 대화상자
        if from_path is None:
            if self.default_save_path and self.default_save_path.exists():
                from_path = self.default_save_path
            else:
                p = filedialog.askopenfilename(title="설정 불러오기",
                                            filetypes=[("JSON 파일","*.json")])
                if not p:
                    return
                from_path = Path(p)

        try:
            with from_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            cfg = Config.from_dict(raw)

            # 위젯 반영 (당신 코드 그대로)
            for key in ("PRESS_INTERVAL_RANGE","X_MOVE_INTERVAL_RANGE","SPECIAL_KEY_GAP",
                        "HIGH_PICK_UP_INTERVAL_RANGE","LOW_PICK_UP_INTERVAL_RANGE"):
                self.widgets[key].set(getattr(cfg, key))
            self.widgets["TARGET_Y"].set(cfg.TARGET_Y)
            self.widgets["PIT_Y"].set(cfg.PIT_Y)
            self.task_editor.load_data(cfg.TASK_SPECS)
            self.high_stage_editor.load_data(cfg.HIGH_PICKUP_STAGES)
            self.low_stage_editor.load_data(cfg.LOW_PICKUP_STAGES)
            self.high_path_editor.load_data(cfg.HIGH_PICKUP_PATH)
            self.low_path_editor.load_data(cfg.LOW_PICKUP_PATH)
            self.widgets["MIDDLE_X"].set(cfg.MIDDLE_X)
            self.widgets["DEAD_BAND"].set(cfg.DEAD_BAND)
            self.widgets["TIMEOUT_S"].set(cfg.TIMEOUT_S)
            self.widgets["HUNT"].set(cfg.HUNT)
            self.widgets["SKILL_RADIUS"].set(cfg.SKILL_RADIUS)
            self.widgets["MISC_JITTER_PROB"].set(cfg.MISC_JITTER_PROB)
            self.widgets["MISC_JITTER_COOLDOWN"].set(cfg.MISC_JITTER_COOLDOWN)
            self.widgets["MISC_JITTER_KEYS"].set(cfg.MISC_JITTER_KEYS)
            self.widgets["BASE_DIR"].set(cfg.BASE_DIR or "")
            self.widgets["INNER_CROP_PX"].set(cfg.INNER_CROP_PX)
            self.widgets["SET_TELEGRAM"].set(cfg.SET_TELEGRAM)
            self.widgets["TELEGRAM_BOT"].set(cfg.TELEGRAM_BOT)
            self.widgets["CHAT_ID"].set(cfg.CHAT_ID)
            self.widgets["SET_USER_ALERT"].set(cfg.SET_USER_ALERT)
            # ── 새 항목들 ──
            self.widgets["DEBUG"].set(cfg.DEBUG)
            self.widgets["MONSTER_BAND_TOP"].set(cfg.MONSTER_BAND_TOP)
            self.widgets["MONSTER_BAND_BOTTOM"].set(cfg.MONSTER_BAND_BOTTOM)
            self.widgets["CHAT_CROP_PX"].set(cfg.CHAT_CROP_PX)
            self.widgets["IMSHOW_SCALE"].set(cfg.IMSHOW_SCALE)
            self.widgets["ATTACK_FOR_SEC"].set(cfg.ATTACK_FOR_SEC)
            messagebox.showinfo("불러오기 완료", str(from_path))
        except Exception as e:
            messagebox.showerror("불러오기 실패", str(e))

    def reset_defaults(self):
        cfg = self.default_cfg
        for key in ("PRESS_INTERVAL_RANGE","X_MOVE_INTERVAL_RANGE","SPECIAL_KEY_GAP",
                    "HIGH_PICK_UP_INTERVAL_RANGE","LOW_PICK_UP_INTERVAL_RANGE"):
            self.widgets[key].set(getattr(cfg, key))
        self.widgets["TARGET_Y"].set(cfg.TARGET_Y)
        self.widgets["PIT_Y"].set(cfg.PIT_Y)  # ← 추가
        self.load_defaults_into_tables()
        # Nudge/Misc
        self.widgets["MIDDLE_X"].set(cfg.MIDDLE_X)
        self.widgets["DEAD_BAND"].set(cfg.DEAD_BAND)
        self.widgets["TIMEOUT_S"].set(cfg.TIMEOUT_S)
        self.widgets["HUNT"].set(cfg.HUNT)
        self.widgets["SKILL_RADIUS"].set(cfg.SKILL_RADIUS)
        self.widgets["MISC_JITTER_PROB"].set(cfg.MISC_JITTER_PROB)
        self.widgets["MISC_JITTER_COOLDOWN"].set(cfg.MISC_JITTER_COOLDOWN)
        self.widgets["MISC_JITTER_KEYS"].set(cfg.MISC_JITTER_KEYS)
        # Files/Telegram
        self.widgets["BASE_DIR"].set(cfg.BASE_DIR or "")
        self.widgets["INNER_CROP_PX"].set(cfg.INNER_CROP_PX)
        self.widgets["SET_TELEGRAM"].set(cfg.SET_TELEGRAM)
        self.widgets["TELEGRAM_BOT"].set(cfg.TELEGRAM_BOT)
        self.widgets["CHAT_ID"].set(cfg.CHAT_ID)
        self.widgets["SET_USER_ALERT"].set(cfg.SET_USER_ALERT)
        # ── 새 항목들 ──
        self.widgets["DEBUG"].set(cfg.DEBUG)
        self.widgets["MONSTER_BAND_TOP"].set(cfg.MONSTER_BAND_TOP)
        self.widgets["MONSTER_BAND_BOTTOM"].set(cfg.MONSTER_BAND_BOTTOM)
        self.widgets["CHAT_CROP_PX"].set(cfg.CHAT_CROP_PX)
        self.widgets["IMSHOW_SCALE"].set(cfg.IMSHOW_SCALE)
        self.widgets["ATTACK_FOR_SEC"].set(cfg.ATTACK_FOR_SEC)
        self.preview_box.delete("1.0","end"); self.preview_box.insert("end","기본값으로 복원했습니다.\n")

    # App 클래스 내부에 추가
    def _start_run(self):
        """
        '시작하기' 눌렀을 때 호출되는 실 실행 함수.
        여기에서 settings.py 불러오거나, collect_config() → 저장 → 별도 모듈 실행 등
        원하는 로직으로 바꿔 쓰세요.
        """
        # 예시) 현재 GUI 값 읽어오기
        try:
            cfg = self.collect_config()
        except Exception as e:
            tk.messagebox.showerror("설정 오류", str(e))
            return

        # TODO: 여기서 cfg를 settings.py에 반영하거나, 바로 main 루틴 호출
        # ex) run_main(cfg)
        tk.messagebox.showinfo("시작", "여기서 실제 동작을 시작하세요!\n(이 메시지는 임시입니다.)")


#def config_setting(default_path: Path | None = None):
#    App(default_path=default_path).mainloop()

if __name__ == "__main__":
    App().mainloop()