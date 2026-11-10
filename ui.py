# ui.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import re
import os
import sys
import queue
import datetime
from settings import load_config, save_config, get_active_profile
from settings_dialog import SettingsDialog
import pyttsx3

from services import (
    translate_text, init_word_doc, check_word_exists,
    save_to_word, delete_from_word, get_count,
    export_favorites, default_export_filename,
)
from history import get_history, get_history_result
from dialogs import HistoryExportDialog  # <-- 导入解耦后的弹窗


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


REVIEW_THRESHOLD = 3
RECENT_MAX = 20


class DictionaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小星英汉词典")
        self.root.geometry("1100x600")
        self.topmost_flag = False
        try:
            icon_path = resource_path("dictionary.ico")
            self.root.iconbitmap(icon_path)
        except Exception:
            pass
        self.current_query = ""
        self.current_result = ""
        self.recent_queries = []

        # 记录本次软件启动时间
        self.start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        init_word_doc()
        self._build_ui()
        self.tts_queue = queue.Queue()
        threading.Thread(target=self._tts_worker, daemon=True).start()
        self.root.after(500, self._check_first_run)
    def _build_ui(self):
        # ========== 顶部状态栏 ==========
        top_pin_bar = ttk.Frame(self.root, height=32)
        top_pin_bar.pack(fill=tk.X, pady=(2, 0))

        self.star_btn = tk.Button(
            top_pin_bar, text="☆", font=("Arial", 12), fg="gray",
            relief="flat", bg=self.root.cget("bg"), cursor="hand2",
            command=self._on_star_click, padx=5, pady=0
        )
        self.star_btn.pack(side=tk.LEFT, padx=(15, 5))
        self.model_switch_var = tk.StringVar()
        self.model_switch_combo = ttk.Combobox(
            top_pin_bar, textvariable=self.model_switch_var,
            state="readonly", width=15, font=("Microsoft YaHei", 9)
        )
        self.model_switch_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.model_switch_combo.bind("<<ComboboxSelected>>", self._on_model_switch)

        # 2. 设置按钮
        self.settings_btn = tk.Button(
            top_pin_bar, text="⚙️ 设置", font=("Microsoft YaHei", 9),
            relief="flat", bg=self.root.cget("bg"), cursor="hand2",
            command=self._open_settings, padx=5, pady=0
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(0, 5))
        # 导出收藏 / 导出历史（紧跟星标）
        self.btn_export_fav = tk.Button(
            top_pin_bar, text="📤 导出收藏", font=("Microsoft YaHei", 9),
            relief="flat", bg=self.root.cget("bg"), cursor="hand2",
            command=self._on_export_favorites, padx=4, pady=0
        )
        self.btn_export_fav.pack(side=tk.LEFT, padx=(2, 2))

        self.btn_export_hist = tk.Button(
            top_pin_bar, text="📤 导出历史", font=("Microsoft YaHei", 9),
            relief="flat", bg=self.root.cget("bg"), cursor="hand2",
            command=self._on_export_history, padx=4, pady=0
        )
        self.btn_export_hist.pack(side=tk.LEFT, padx=(2, 2))

        self.pin_btn = tk.Button(
            top_pin_bar, text="📍", font=("Segoe UI Symbol", 11),
            relief="flat", bg=self.root.cget("bg"), cursor="hand2",
            command=self._toggle_topmost, pady=0
        )
        self.pin_btn.pack(side=tk.RIGHT, padx=(0, 12), pady=0)

        # ========== 主内容区 ==========
        self.main_frame = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # 左侧
        self.left_frame = ttk.LabelFrame(self.paned, text="原文输入（回车查询，Shift+Enter换行）")

        self.recent_bar = ttk.Frame(self.left_frame)
        self.recent_bar.pack(fill=tk.X, padx=15, pady=(6, 0))
        ttk.Label(self.recent_bar, text="最近查询：", foreground="#5e5c64").pack(side=tk.LEFT)
        self.recent_combo = ttk.Combobox(self.recent_bar, state="readonly", width=28)
        self.recent_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.recent_combo.bind("<<ComboboxSelected>>", self._on_recent_selected)

        self.input_box = scrolledtext.ScrolledText(
            self.left_frame, font=("Microsoft YaHei", 11), undo=True,
            width=1, height=1, wrap=tk.WORD
        )
        self.input_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        self.input_box.bind("<Return>", self._on_enter)

        # 右侧
        self.right_frame = ttk.LabelFrame(self.paned, text="查询 / 翻译结果")

        self.audio_bar = ttk.Frame(self.right_frame)
        self.btn_uk = ttk.Button(self.audio_bar, text="🔊 英音", width=8,
                                 command=lambda: self._speak(self.current_query, "en-uk"))
        self.btn_uk.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_us = ttk.Button(self.audio_bar, text="🔊 美音", width=8,
                                 command=lambda: self._speak(self.current_query, "en-us"))
        self.btn_us.pack(side=tk.LEFT, padx=(0, 5))

        self.output_box = scrolledtext.ScrolledText(
            self.right_frame, font=("Microsoft YaHei", 11),
            width=1, height=1, wrap=tk.WORD
        )
        self.output_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        self.output_box.config(state="disabled")

        self.paned.add(self.left_frame, weight=30)
        self.paned.add(self.right_frame, weight=70)

        # 底部状态栏
        self.btn_frame = ttk.Frame(self.root, padding=8)
        self.btn_frame.pack(fill=tk.X, padx=10)
        self.status_label = ttk.Label(self.btn_frame, text="就绪 (按回车键查询)", foreground="#888888")
        self.status_label.pack(side=tk.LEFT, padx=10)

    # -------- 最近查询历史（内存） --------
    def _add_recent(self, text: str):
        key = text.strip()
        if not key:
            return
        key_lower = key.lower()
        self.recent_queries = [x for x in self.recent_queries if x.lower() != key_lower]
        self.recent_queries.insert(0, key)
        if len(self.recent_queries) > RECENT_MAX:
            self.recent_queries = self.recent_queries[:RECENT_MAX]
        self._refresh_recent_combo()

    def _refresh_recent_combo(self):
        if not self.recent_queries:
            self.recent_combo["values"] = []
            self.recent_combo.set("")
            return
        self.recent_combo["values"] = self.recent_queries
        cur = self.input_box.get("1.0", tk.END).strip()
        if cur and cur in self.recent_queries:
            self.recent_combo.set(cur)
        elif not self.recent_combo.get():
            self.recent_combo.set(self.recent_queries[0])

    def _on_recent_selected(self, event=None):
        text = self.recent_combo.get().strip()
        if not text:
            return
        self.input_box.delete("1.0", tk.END)
        self.input_box.insert(tk.END, text)

        # 从历史读结果，不重查
        item = get_history_result(text)
        if item and item.get("result"):
            self.current_query = text
            self.current_result = item["result"]
            self._update_star_icon(text)
            count = item.get("count_at_query", 0)
            self._display_result(text, item["result"],
                                 item.get("source", "历史记录"), count)
        else:
            self._on_translate()

    def _check_first_run(self):
        cfg = load_config()
        if not cfg.get("profiles"):
            self._open_settings()
        else:
            self._refresh_model_switch()

    def _refresh_model_switch(self):
        """刷新下拉框列表，并选中当前激活的项"""
        cfg = load_config()
        profiles = list(cfg.get("profiles", {}).keys())
        self.model_switch_combo["values"] = profiles

        active = cfg.get("active_profile")
        if active and active in profiles:
            self.model_switch_var.set(active)
        elif profiles:
            # 如果没有激活项，默认选第一个
            self.model_switch_var.set(profiles[0])
            cfg["active_profile"] = profiles[0]
            save_config(cfg)

    def _on_model_switch(self, event=None):
        """用户在下拉框切换模型"""
        selected = self.model_switch_var.get()
        if not selected:
            return
        cfg = load_config()
        cfg["active_profile"] = selected
        save_config(cfg)
        self.status_label.config(text=f"已切换当前接口：{selected}")

    def _open_settings(self):
        """打开设置，关闭后刷新下拉框"""
        dialog = SettingsDialog(self.root, on_saved=self._refresh_model_switch)
        self.root.wait_for_window(dialog) if hasattr(self.root, 'wait_for_window') else self.root.wait_window(dialog)
    # -------- TTS --------
    @staticmethod
    def _pick_voice(engine, accent_type):
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return None

        want_gb = (accent_type == "en-uk")
        want_us = (accent_type == "en-us")

        GB_KEYS = ("hazel", "george", "susan", "en-gb", "en_gb", "uk", "british")
        US_KEYS = ("zira", "david", "mark", "aria", "guy", "en-us", "en_us", "us", "american")

        def score(voice):
            name = (getattr(voice, "name", "") or "").lower()
            vid = (getattr(voice, "id", "") or "").lower()
            text = name + " " + vid
            s = 0
            if want_gb and ("en-gb" in text or "en_gb" in text):
                s += 10
            if want_us and ("en-us" in text or "en_us" in text):
                s += 10
            if want_gb:
                s += sum(1 for k in GB_KEYS if k in text)
            if want_us:
                s += sum(1 for k in US_KEYS if k in text)
            if "english" not in text and "en-" not in text and "en_" not in text:
                s -= 5
            return s

        best, best_score = None, -10 ** 9
        for v in voices:
            sc = score(v)
            if sc > best_score:
                best, best_score = v, sc

        if best is None or best_score <= 0:
            return None
        return getattr(best, "id", None)

    def _tts_worker(self):
        while True:
            text, accent_type = self.tts_queue.get()
            if text is None:
                break
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                voice_id = self._pick_voice(engine, accent_type)
                if voice_id:
                    engine.setProperty('voice', voice_id)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                del engine
            except Exception as e:
                print(f"发音失败: {e}")
            finally:
                self.tts_queue.task_done()

    def _speak(self, text, accent_type):
        if not text:
            return
        self.tts_queue.put((text, accent_type))

    # -------- 置顶 --------
    def _toggle_topmost(self):
        self.topmost_flag = not self.topmost_flag
        self.root.attributes("-topmost", self.topmost_flag)
        if self.topmost_flag:
            self.pin_btn.config(text="📌")
            self.status_label.config(text="已开启窗口置顶")
        else:
            self.pin_btn.config(text="📍")
            self.status_label.config(text="已关闭窗口置顶")

    # -------- 星标 --------
    def _update_star_icon(self, query_text):
        if check_word_exists(query_text):
            self.star_btn.config(text="★", fg="#FFD700")
        else:
            self.star_btn.config(text="☆", fg="gray")

    def _on_star_click(self):
        if not self.current_query or not self.current_result:
            messagebox.showinfo("提示", "没有可保存的内容，请先查询。")
            return

        if check_word_exists(self.current_query):
            success, msg = delete_from_word(self.current_query)
            if success:
                self._update_star_icon(self.current_query)
                self.status_label.config(text="已取消保存，记录已删除")
            else:
                messagebox.showinfo("提示", msg)
        else:
            success, msg = save_to_word(self.current_query, self.current_result)
            if success:
                self._update_star_icon(self.current_query)
                self.status_label.config(text="已保存到 Dictionary_Records.docx")
            else:
                messagebox.showinfo("提示", msg)

    # -------- 导出收藏 --------
    def _on_export_favorites(self):
        default_name = default_export_filename("收藏记录")
        path = filedialog.asksaveasfilename(
            title="导出收藏记录",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word 文档", "*.docx")]
        )
        if not path:
            return
        success, msg = export_favorites(path)
        if success:
            self.status_label.config(text=msg)
        else:
            messagebox.showinfo("导出收藏", msg)

    # -------- 导出历史 --------
    def _on_export_history(self):
        records = get_history()
        if not records:
            messagebox.showinfo("导出历史", "暂无历史记录。")
            return
        # 将启动时间作为参数传入弹窗
        HistoryExportDialog(
            self.root, records,
            start_time=self.start_time,
            on_export_done=self._on_history_exported
        )

    def _on_history_exported(self, msg: str):
        self.status_label.config(text=msg)

    # -------- 输入/查询 --------
    def _on_enter(self, event):
        if event.state & 0x0001:
            return
        self._on_translate()
        return "break"

    def _on_translate(self):
        src_text = self.input_box.get("1.0", tk.END).strip()
        if not src_text:
            messagebox.showwarning("提示", "请输入要查询/翻译的内容！")
            return

        if self.input_box.cget("state") == "disabled":
            return
        self.input_box.config(state="disabled")

        self.current_query = src_text
        self._update_star_icon(src_text)
        self._add_recent(src_text)
        self.audio_bar.pack_forget()

        self.output_box.config(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, "正在查询...")
        self.output_box.config(state="disabled")
        self.status_label.config(text="正在查询...")

        t = threading.Thread(target=self._translate_thread, args=(src_text,), daemon=True)
        t.start()

    def _translate_thread(self, src_text):
        try:
            final_result, source_tag = translate_text(src_text)
        except Exception as e:
            final_result = f"发生内部错误：\n{str(e)}"
            source_tag = "程序异常"

        self.current_result = final_result
        try:
            count = get_count(src_text)
        except Exception:
            count = 0

        self.root.after(0, lambda: self._display_result(src_text, final_result, source_tag, count))

    def _display_result(self, src_text: str, final_result: str, source_tag: str, count: int):
        """统一的结果渲染（查询与历史回看共用）"""
        self.input_box.config(state="normal")
        self.output_box.config(state="normal")
        self.output_box.delete("1.0", tk.END)

        if count >= REVIEW_THRESHOLD:
            header_lines = [f"【查询次数】：{count} 次"]
            is_fav = check_word_exists(src_text)
            if is_fav:
                header_lines.append(
                    f"【掌握度提示】：该内容已查询 {count} 次，已收藏，请重点复习！"
                )
            else:
                header_lines.append(
                    f"【掌握度提示】：该内容已查询 {count} 次，说明尚未掌握，建议点击左上角 ☆ 收藏起来重点复习！"
                )
            header_lines.append("")
            self.output_box.insert(tk.END, "\n".join(header_lines) + "\n")

        self.output_box.insert(tk.END, final_result)
        self._apply_formatting_tags()
        self.output_box.config(state="disabled")

        if count >= REVIEW_THRESHOLD:
            self.status_label.config(
                text=f"查询来源: {source_tag} ｜ 该内容累计查询 {count} 次"
            )
        else:
            self.status_label.config(text=f"查询来源: {source_tag}")

        if "【英音音标】" in final_result or "【美音音标】" in final_result:
            self.audio_bar.pack(fill=tk.X, padx=15, pady=(5, 0), before=self.output_box)
        else:
            self.audio_bar.pack_forget()

    def _apply_formatting_tags(self):
        content = self.output_box.get("1.0", tk.END)
        self.output_box.tag_config("bold_blue", foreground="#1a5fb4", font=("Microsoft YaHei", 11, "bold"))
        self.output_box.tag_config("bold_gray", foreground="#5e5c64", font=("Microsoft YaHei", 11, "bold"))
        for match in re.finditer(r'【[^】]+】', content):
            self.output_box.tag_add("bold_blue", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")
        for match in re.finditer(r'\[[^\]]+\]', content):
            self.output_box.tag_add("bold_gray", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")