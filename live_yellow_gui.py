#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk
import cv2, numpy as np
from capture_pw import WindowCapturerPW

# ==== 기본값 ====
DEFAULT_WINDOW_TITLE   = "maple"
DEFAULT_INTERVAL_SEC   = 0.05
DEFAULT_ROI_PCT        = (0.0, 0.0, 1.0, 1.0)     # x1,y1,x2,y2 (0~1)
DEFAULT_ROI_PX         = (1, 1, 1330, 840)        # x,y,w,h
DEFAULT_CHAT_CROP_PX    = "0, 500, 575, 100"   # x,y,w,h (원하면 바꿔도 됨)
DEFAULT_SKILL_RADIUS    = 300              # px
DEFAULT_MONSTER_BAND    = "0.45, 0.73"    # top, bottom (0~1 비율)
DEFAULT_INNER_CROP_PX  = "0,100,200,100"           # x,y,w,h
DEFAULT_OUT_PATH       = "roi.png"                # ROI 저장
DEFAULT_INNER_OUT_PATH = "roi_inner.png"          # INNER 저장

class YellowMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yellow Center Live Monitor")
        self.geometry("1080x740")

        try:
            self.lift(); self.attributes("-topmost", True); self.after(300, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

        self.cap = None
        self.polling = False
        self.out_path = None
        self.inner_out_path = None
        self._imgtk_roi = None
        self._imgtk_inner = None

        # ── 상단 입력 ─────────────────────────────────────────
        top = ttk.Frame(self, padding=10); top.pack(fill="x")

        # Window Title
        lbl_title = ttk.Label(top, text="Window Title:")
        lbl_title.grid(row=0, column=0, sticky="e", padx=(0,8), pady=4)
        self.var_title = tk.StringVar(value=DEFAULT_WINDOW_TITLE)
        ent_title = ttk.Entry(top, textvariable=self.var_title, width=28)
        ent_title.grid(row=0, column=1, sticky="w", pady=4)

        # Interval
        lbl_interval = ttk.Label(top, text="Interval(s):")
        lbl_interval.grid(row=0, column=2, sticky="e", padx=(16,8))
        self.var_interval = tk.StringVar(value=str(DEFAULT_INTERVAL_SEC))
        ent_interval = ttk.Entry(top, textvariable=self.var_interval, width=8, justify="right")
        ent_interval.grid(row=0, column=3, sticky="w")

        # ROI_PCT
        lbl_roi_pct = ttk.Label(top, text="ROI_PCT (x1,y1,x2,y2):")
        lbl_roi_pct.grid(row=1, column=0, sticky="e", padx=(0,8), pady=4)
        self.var_roi_pct = tk.StringVar(value="{}, {}, {}, {}".format(*DEFAULT_ROI_PCT))
        ent_roi_pct = ttk.Entry(top, textvariable=self.var_roi_pct, width=28)
        ent_roi_pct.grid(row=1, column=1, sticky="w", pady=4)

        # ROI_PX
        lbl_roi_px = ttk.Label(top, text="ROI_PX (x,y,w,h|빈칸):")
        lbl_roi_px.grid(row=1, column=2, sticky="e", padx=(16,8), pady=4)
        self.var_roi_px = tk.StringVar(value="{}, {}, {}, {}".format(*DEFAULT_ROI_PX))
        ent_roi_px = ttk.Entry(top, textvariable=self.var_roi_px, width=28)
        ent_roi_px.grid(row=1, column=3, sticky="w", pady=4)

        # out_path
        lbl_out = ttk.Label(top, text="out_path:")
        lbl_out.grid(row=2, column=2, sticky="e", padx=(16,8), pady=4)
        self.var_out = tk.StringVar(value=str(DEFAULT_OUT_PATH))
        ent_out = ttk.Entry(top, textvariable=self.var_out, width=20)
        ent_out.grid(row=2, column=3, sticky="w", pady=4)
        btn_out = ttk.Button(top, text="...", width=3, command=self.choose_out)
        btn_out.grid(row=2, column=4, sticky="w", padx=(6,0))

        # inner_out_path
        lbl_inner_out = ttk.Label(top, text="inner_out_path:")
        lbl_inner_out.grid(row=3, column=2, sticky="e", padx=(16,8), pady=4)
        self.var_inner_out = tk.StringVar(value=str(DEFAULT_INNER_OUT_PATH))
        ent_inner_out = ttk.Entry(top, textvariable=self.var_inner_out, width=20)
        ent_inner_out.grid(row=3, column=3, sticky="w", pady=4)
        btn_inner_out = ttk.Button(top, text="...", width=3, command=self.choose_inner_out)
        btn_inner_out.grid(row=3, column=4, sticky="w", padx=(6,0))
        ttk.Label(top, text="INNER_CROP_PX (x,y,w,h):").grid(row=2, column=0, sticky="e", padx=(0,8), pady=4)
        self.var_inner = tk.StringVar(value=DEFAULT_INNER_CROP_PX)
        ttk.Entry(top, textvariable=self.var_inner, width=28).grid(row=2, column=1, sticky="w", pady=4)

        # SKILL_RADIUS, MONSTER_BAND
        ttk.Label(top, text="SKILL_RADIUS(px):").grid(row=4, column=0, sticky="e", padx=(0,8), pady=4)
        self.var_skill_radius = tk.StringVar(value=str(DEFAULT_SKILL_RADIUS))
        ttk.Entry(top, textvariable=self.var_skill_radius, width=10, justify="right").grid(row=4, column=1, sticky="w", pady=4)

        ttk.Label(top, text="MONSTER_BAND(top,bottom 0~1):").grid(row=4, column=2, sticky="e", padx=(16,8), pady=4)
        self.var_monster_band = tk.StringVar(value=DEFAULT_MONSTER_BAND)
        ttk.Entry(top, textvariable=self.var_monster_band, width=20).grid(row=4, column=3, sticky="w", pady=4)

        # CHAT_CROP_PX
        ttk.Label(top, text="CHAT_CROP_PX (x,y,w,h):").grid(row=5, column=0, sticky="e", padx=(0,8), pady=4)
        self.var_chat_crop = tk.StringVar(value=DEFAULT_CHAT_CROP_PX)
        ttk.Entry(top, textvariable=self.var_chat_crop, width=28).grid(row=5, column=1, sticky="w", pady=4)

        # ── 버튼 ──────────────────────────────────────────────
        btns = ttk.Frame(self, padding=(10,6)); btns.pack(fill="x")
        self.btn_start = ttk.Button(btns, text="시작 (cap.start)", command=self.on_start)
        self.btn_start.pack(side="left")
        #ttk.Button(btns, text="INNER 적용(재설정)", command=self.on_apply_inner).pack(side="left", padx=8)
        self.btn_stop = ttk.Button(btns, text="정지", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=8)

        # ── 상태 ──────────────────────────────────────────────
        status = ttk.LabelFrame(self, text="실시간 상태", padding=10); status.pack(fill="x", padx=10, pady=(6,4))
        self.var_yellow = tk.StringVar(value="(미검출)")
        self.var_roi    = tk.StringVar(value="-")
        self.var_inner_rect = tk.StringVar(value="-")
        ttk.Label(status, text="yellow center(screen):").grid(row=0, column=0, sticky="e", padx=(0,8), pady=2)
        ttk.Label(status, textvariable=self.var_yellow).grid(row=0, column=1, sticky="w")
        ttk.Label(status, text="ROI screen rect:").grid(row=1, column=0, sticky="e", padx=(0,8), pady=2)
        ttk.Label(status, textvariable=self.var_roi).grid(row=1, column=1, sticky="w")
        ttk.Label(status, text="INNER screen rect:").grid(row=2, column=0, sticky="e", padx=(0,8), pady=2)
        ttk.Label(status, textvariable=self.var_inner_rect).grid(row=2, column=1, sticky="w")

        # ── 프리뷰 (ROI / INNER 나란히) ──────────────────────
        previews = ttk.Frame(self, padding=8); previews.pack(fill="both", expand=True, padx=10, pady=8)
        left = ttk.LabelFrame(previews, text="ROI Preview", padding=8); left.pack(side="left", fill="both", expand=True)
        right = ttk.LabelFrame(previews, text="INNER Preview", padding=8); right.pack(side="left", fill="both", expand=True)

        self.lbl_roi = ttk.Label(left); self.lbl_roi.pack()
        self.lbl_inner = ttk.Label(right); self.lbl_inner.pack()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.skill_radius = DEFAULT_SKILL_RADIUS
        self.monster_band_top = 0.40
        self.monster_band_bottom = 0.70
        self.chat_crop_px = None

        for w in [
            lbl_title, ent_title,
            lbl_interval, ent_interval,
            lbl_roi_pct, ent_roi_pct,
            lbl_roi_px, ent_roi_px,
            lbl_out, ent_out, btn_out,
            lbl_inner_out, ent_inner_out, btn_inner_out,
        ]:
            w.grid_remove()
    
    # ── helpers ─────────────────────────────────────────────
    def choose_out(self):
        p = filedialog.asksaveasfilename(
            title="ROI 저장 경로", defaultextension=".png",
            filetypes=[("PNG","*.png"), ("모든 파일","*.*")]
        )
        if p: self.var_out.set(p)

    def choose_inner_out(self):
        p = filedialog.asksaveasfilename(
            title="INNER 저장 경로", defaultextension=".png",
            filetypes=[("PNG","*.png"), ("모든 파일","*.*")]
        )
        if p: self.var_inner_out.set(p)

    def parse_tuple4(self, s):
        parts = [p.strip() for p in s.split(",") if p.strip()!=""]
        if len(parts) != 4: raise ValueError("형식은 x,y,w,h 여야 합니다.")
        return tuple(int(float(v)) for v in parts)

    def parse_tuple4_float(self, s):
        parts = [p.strip() for p in s.split(",") if p.strip()!=""]
        if len(parts) != 4: raise ValueError("형식은 x1,y1,x2,y2 여야 합니다.")
        return tuple(float(v) for v in parts)

    def parse_tuple2_float(self, s):
        parts = [p.strip() for p in s.split(",") if p.strip()!=""]
        if len(parts) != 2:
            raise ValueError("형식은 top,bottom (0~1) 여야 합니다.")
        return tuple(float(v) for v in parts)
    # ── actions ─────────────────────────────────────────────
    def on_start(self):
        if self.cap:
            messagebox.showinfo("알림", "이미 실행 중입니다."); return
        try:
            title_sub = self.var_title.get().strip()
            interval  = float(self.var_interval.get().strip())
            self.out_path = self.var_out.get().strip()
            self.inner_out_path = self.var_inner_out.get().strip()
            self.skill_radius = int(float(self.var_skill_radius.get().strip()))
            band_top, band_bottom = self.parse_tuple2_float(self.var_monster_band.get().strip())
            self.monster_band_top = band_top
            self.monster_band_bottom = band_bottom
            chat_str = self.var_chat_crop.get().strip()
            self.chat_crop_px = self.parse_tuple4(chat_str) if chat_str else None
            roi_px_str = self.var_roi_px.get().strip()
            if roi_px_str:
                roi_px = self.parse_tuple4(roi_px_str)
                roi_pct = (0.0, 0.0, 1.0, 1.0)
            else:
                roi_px = None
                roi_pct = self.parse_tuple4_float(self.var_roi_pct.get().strip())

            inner = self.parse_tuple4(self.var_inner.get().strip())

            self.cap = WindowCapturerPW(
                window_title_substr=title_sub,
                interval=0.0,
                client_only=True,
                region_pct=(0,0,1,1),
                enable_preview=False,
                preview_scale=1.0,
                enable_inner_detect=True,
                inner_crop_px=inner,
                inner_detect_every=1,
                enable_red_detect=True,
                chat_crop_px=self.chat_crop_px,    # ← 여기!
                red_detect_every=3,
                enable_save=False,
                yellow_gui=True
            )
            self.cap.start()
            self.polling = True
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.after(100, self.poll_tick)
        except Exception as e:
            messagebox.showerror("시작 실패", str(e))
            self.cap = None

    def on_apply_inner(self):
        if not self.cap:
            messagebox.showwarning("알림", "캡처가 아직 시작되지 않았습니다."); return
        try:
            inner = self.parse_tuple4(self.var_inner.get().strip())
            self.cap.inner_crop_px = tuple(int(v) for v in inner)  # 실행 중 갱신
            messagebox.showinfo("적용됨", f"INNER_CROP_PX = {self.cap.inner_crop_px}")

            # 🔥 적용 후 즉시 한 번 화면 갱신
            self.poll_tick()
        except Exception as e:
            messagebox.showerror("오류", str(e))


    def on_stop(self):
        self.polling = False
        if self.cap:
            try: self.cap.stop()
            except Exception: pass
            self.cap = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _load_image_safe(self, path):
        if not path or not os.path.exists(path): return None
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img

    def _draw_overlays_on_roi(self, img_roi):
        """ROI 이미지 위에 노란점, INNER, CHAT, 몬스터 띠/스킬 범위를 그린다."""
        try:
            y  = self.cap.get_last_yellow_screen()
            r  = self.cap.get_roi_screen_rect()
            ir = self.cap.get_last_inner_roi_rect()
            h, w = img_roi.shape[:2]

            draw = img_roi.copy()
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1

            # 1) MONSTER BAND (세로 띠)
            if self.monster_band_top is not None and self.monster_band_bottom is not None:
                bt = int(h * self.monster_band_top)
                bb = int(h * self.monster_band_bottom)
                cv2.rectangle(draw, (0, bt), (w-1, bb), (0, 255, 255), 1)
                cv2.putText(
                    draw, "MONSTER BAND",
                    (5, max(15, bt - 5)),
                    font, font_scale, (0, 255, 255), thickness, cv2.LINE_AA
                )

                # 1-1) SKILL RANGE (중앙 스킬 반경)
                if self.skill_radius is not None:
                    cx = w // 2
                    x1s = max(0, cx - self.skill_radius)
                    x2s = min(w-1, cx + self.skill_radius)
                    cv2.rectangle(draw, (x1s, bt), (x2s, bb), (255, 255, 0), 2)
                    cv2.putText(
                        draw, "SKILL",
                        (x1s + 5, bt + 20),
                        font, font_scale, (255, 255, 0), thickness, cv2.LINE_AA
                    )

            # 2) CHAT_CROP_PX 박스
            if self.chat_crop_px:
                cx, cy, cw, ch = self.chat_crop_px
                x1c, y1c = cx, cy
                x2c, y2c = cx + cw, cy + ch
                cv2.rectangle(draw, (x1c, y1c), (x2c, y2c), (0, 0, 255), 2)
                cv2.putText(
                    draw, "CHAT",
                    (x1c + 5, y1c + 20),
                    font, font_scale, (0, 0, 255), thickness, cv2.LINE_AA
                )

            # 3) INNER 사각형 (screen → ROI 변환)
            if r and ir:
                x1 = max(0, min(w-1, ir["left"] - r["left"]))
                y1 = max(0, min(h-1, ir["top"]  - r["top"]))
                x2 = max(0, min(w-1, x1 + ir["width"]))
                y2 = max(0, min(h-1, y1 + ir["height"]))
                cv2.rectangle(draw, (x1, y1), (x2, y2), (255, 0, 255), 2)
                cv2.putText(
                    draw, "INNER",
                    (x1 + 5, y1 + 20),
                    font, font_scale, (255, 0, 255), thickness, cv2.LINE_AA
                )

            # 4) 노란점 십자
            if y and r:
                cx = y[0] - r["left"]
                cy = y[1] - r["top"]
                if 0 <= cx < w and 0 <= cy < h:
                    cv2.line(draw, (cx-8, cy), (cx+8, cy), (0,255,255), 2)
                    cv2.line(draw, (cx, cy-8), (cx, cy+8), (0,255,255), 2)
                    cv2.circle(draw, (cx, cy), 3, (0,255,255), 2)

            return draw
        except Exception:
            return img_roi


    def _show_on_label(self, bgr_img, label_widget, max_w=500, max_h=420, store_attr_name="_imgtk_roi"):
        if bgr_img is None: return
        rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        disp = cv2.resize(rgb, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_NEAREST)
        pil_img = Image.fromarray(disp)
        imgtk = ImageTk.PhotoImage(pil_img)
        setattr(self, store_attr_name, imgtk)  # 참조 유지
        label_widget.config(image=imgtk)
    
    def get_inner_xy(self, last_yellow_point, inner_roi_rect):
        inner_rect_provider = inner_roi_rect
        pos = last_yellow_point

        sx, sy = pos
        cx, cy = sx, sy
        rect = inner_rect_provider

        if rect and isinstance(rect, dict) and 'left' in rect and 'top' in rect:
            cx = sx - int(rect['left'])
            cy = sy - int(rect['top'])
        
        return cx, cy

    def poll_tick(self):
        if not self.polling or not self.cap:
            return
        try:
            # 텍스트 상태
            r = self.cap.get_roi_screen_rect();    self.var_roi.set("-" if not r else f"{r}")
            ir = self.cap.get_last_inner_roi_rect(); self.var_inner_rect.set("-" if not ir else f"{ir}")
            y = self.cap.get_last_yellow_screen(); self.var_yellow.set(self.get_inner_xy(y,ir) if y or ir else "(미검출)")
            # ROI 프리뷰 + 오버레이
            roi = self.cap.get_last_roi_frame()
            if roi is not None:
                roi_drawn = self._draw_overlays_on_roi(roi)
                self._show_on_label(roi_drawn, self.lbl_roi, store_attr_name="_imgtk_roi")

            # INNER 프리뷰 (✅ 파일 읽지 않음)
            inner = self.cap.get_last_inner_frame()
            if inner is not None:
                self._show_on_label(inner, self.lbl_inner, store_attr_name="_imgtk_inner")

        except Exception as e:
            self.var_yellow.set(f"에러: {e}")

        self.after(100, self.poll_tick)

    def on_close(self):
        self.on_stop()
        self.destroy()
#def yellow_monitor():
#    YellowMonitor().mainloop()

if __name__ == "__main__":
    YellowMonitor().mainloop()