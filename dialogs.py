# dialogs.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import unicodedata

from services import default_export_filename
from history import export_history

# 圆点字符（如果 ui.py 其他地方也用了，可以把它移到 config.py）
DOT_ON = "⬤"
DOT_OFF = "◯"


class HistoryExportDialog(tk.Toplevel):
    """历史记录多选导出窗口：圆点选择、全选/全不选、搜索+时间过滤。"""

    def __init__(self, parent, records: list, start_time: str, on_export_done=None):
        super().__init__(parent)
        self.title("选择要导出的历史记录")
        self.geometry("680x520")
        self.transient(parent)
        self.grab_set()
        # 【新增】：强制计算居中位置，防止跑到副屏
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        my_w = self.winfo_width()
        my_h = self.winfo_height()

        x = parent_x + (parent_w - my_w) // 2
        y = parent_y + (parent_h - my_h) // 2
        self.geometry(f"+{x}+{y}")

        self.parent = parent
        self.start_time = start_time
        self.parent = parent
        self.start_time = start_time
        self.on_export_done = on_export_done
        self.all_records = records
        self.time_filtered_records = list(records)
        self.filtered_records = list(records)
        self.selected_words = set()

        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Button(top, text="全选", width=6, command=self._select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(top, text="全不选", width=6, command=self._select_none).pack(side=tk.LEFT, padx=(0, 12))

        # 时间筛选
        ttk.Label(top, text="时间：").pack(side=tk.LEFT)
        self.time_var = tk.StringVar(value="全部历史")
        self.time_combo = ttk.Combobox(
            top, textvariable=self.time_var, state="readonly", width=10,
            values=["全部历史", "本次启动", "今天", "最近3天", "最近7天", "最近30天"]
        )
        self.time_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.time_combo.bind("<<ComboboxSelected>>", self._on_time_filter_changed)

        # 关键词搜索
        ttk.Label(top, text="搜索：").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._apply_filters())
        ttk.Entry(top, textvariable=self.search_var, width=14).pack(side=tk.LEFT)

        self.count_label = ttk.Label(top, text="已选 0 / 0 条", foreground="#5e5c64")
        self.count_label.pack(side=tk.RIGHT)

        # 列表
        list_frame = ttk.Frame(self, padding=(8, 0, 8, 0))
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("dot", "word", "ts", "count")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="none")

        self.tree.heading("dot", text="")
        self.tree.heading("word", text="查询内容", anchor="center")
        self.tree.heading("ts", text="查询时间", anchor="center")
        self.tree.heading("count", text="查询次数", anchor="center")

        self.tree.column("dot", width=40, anchor="center")
        self.tree.column("word", width=180, anchor="w")
        self.tree.column("ts", width=160, anchor="center")
        self.tree.column("count", width=80, anchor="center")

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Button-1>", self._on_tree_click)

        # 底部按钮
        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="导出选中", command=self._on_export).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(bottom, text="取消", command=self.destroy).pack(side=tk.RIGHT)

    def _on_time_filter_changed(self, event=None):
        self._apply_filters()

    def _apply_filters(self):
        now = datetime.datetime.now()
        time_mode = self.time_var.get()

        temp_records = []
        for r in self.all_records:
            ts_str = r.get("ts", "")
            if not ts_str:
                continue

            try:
                r_time = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            if time_mode == "本次启动":
                if ts_str >= self.start_time:
                    temp_records.append(r)
            elif time_mode == "今天":
                if r_time.date() == now.date():
                    temp_records.append(r)
            elif time_mode == "最近3天":
                if (now - r_time).days <= 3:
                    temp_records.append(r)
            elif time_mode == "最近7天":
                if (now - r_time).days <= 7:
                    temp_records.append(r)
            elif time_mode == "最近30天":
                if (now - r_time).days <= 30:
                    temp_records.append(r)
            else:  # 全部历史
                temp_records.append(r)

        self.time_filtered_records = temp_records

        # 关键词过滤
        kw = self.search_var.get().strip().lower()
        if not kw:
            self.filtered_records = list(self.time_filtered_records)
        else:
            self.filtered_records = [
                r for r in self.time_filtered_records
                if kw in self._norm(r.get("word", ""))
            ]

        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.filtered_records:
            word = item.get("word", "")
            key = self._norm(word)
            dot = DOT_ON if key in self.selected_words else DOT_OFF
            self.tree.insert(
                "", tk.END,
                values=(dot, word, item.get("ts", ""), item.get("count_at_query", 0))
            )
        self._update_count()

    def _on_tree_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        values = self.tree.item(iid, "values")
        word = values[1]
        key = self._norm(word)

        if key in self.selected_words:
            self.selected_words.discard(key)
            dot = DOT_OFF
        else:
            self.selected_words.add(key)
            dot = DOT_ON

        self.tree.item(iid, values=(dot, word, values[2], values[3]))
        self._update_count()

    @staticmethod
    def _norm(s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("\u00A0", " ").replace("\u200B", "")
        return s.strip().lower()

    def _select_all(self):
        for r in self.filtered_records:
            self.selected_words.add(self._norm(r.get("word", "")))
        self._refresh_tree()

    def _select_none(self):
        self.selected_words.clear()
        self._refresh_tree()

    def _update_count(self):
        total = len(self.all_records)
        selected = len(self.selected_words)
        if len(self.filtered_records) < total:
            self.count_label.config(text=f"已选 {selected} / 共 {total} 条 (当前显示 {len(self.filtered_records)} 条)")
        else:
            self.count_label.config(text=f"已选 {selected} / {total} 条")

    def _on_export(self):
        if not self.selected_words:
            messagebox.showinfo("导出历史", "请至少选择一条记录。", parent=self)
            return

        selected_words = []
        for r in self.all_records:
            if self._norm(r.get("word", "")) in self.selected_words:
                selected_words.append(r.get("word", ""))

        default_name = default_export_filename("查询历史")
        path = filedialog.asksaveasfilename(
            parent=self,
            title="导出查询历史",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word 文档", "*.docx")]
        )
        if not path:
            return

        success, msg = export_history(selected_words, path)
        if success:
            if self.on_export_done:
                self.on_export_done(msg)
            self.destroy()
        else:
            messagebox.showinfo("导出历史", msg, parent=self)