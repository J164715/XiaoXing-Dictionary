# settings_dialog.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from settings import load_config, save_config, PROVIDERS


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.title("配置管理 - 小星英汉词典")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 【新增】：强制计算居中位置，防止跑到副屏或离得太远
        self.update_idletasks()  # 先让 Tkinter 计算窗口的实际宽高
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        my_w = self.winfo_width()
        my_h = self.winfo_height()

        # 计算居中坐标
        x = parent_x + (parent_w - my_w) // 2
        y = parent_y + (parent_h - my_h) // 2

        # 应用坐标
        self.geometry(f"+{x}+{y}")

        self.on_saved = on_saved
        self.config_data = load_config()
        self._build_ui()
        self._refresh_profiles_list()

    def _build_ui(self):
        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="管理您的 AI 接口配置", font=("Microsoft YaHei", 12, "bold")).pack(pady=(0, 10))

        # 选择要编辑的配置
        row0 = ttk.Frame(main)
        row0.pack(fill=tk.X, pady=5)
        ttk.Label(row0, text="编辑已有配置：", width=12).pack(side=tk.LEFT)
        self.edit_profile_var = tk.StringVar()
        self.edit_profile_combo = ttk.Combobox(row0, textvariable=self.edit_profile_var, state="readonly")
        self.edit_profile_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.edit_profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        # 新建按钮
        ttk.Button(row0, text="新建", width=6, command=self._new_profile).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=10)

        # 配置名称
        row1 = ttk.Frame(main)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="配置别名：", width=12).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row1)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 服务商预设
        row2 = ttk.Frame(main)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="选择服务商：", width=12).pack(side=tk.LEFT)
        self.provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(row2, textvariable=self.provider_var, values=list(PROVIDERS.keys()),
                                           state="readonly")
        self.provider_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # API Key
        row3 = ttk.Frame(main)
        row3.pack(fill=tk.X, pady=5)
        ttk.Label(row3, text="API Key：", width=12).pack(side=tk.LEFT)
        self.key_entry = ttk.Entry(row3, show="*")
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 模型名称
        row4 = ttk.Frame(main)
        row4.pack(fill=tk.X, pady=5)
        ttk.Label(row4, text="模型名称：", width=12).pack(side=tk.LEFT)
        self.model_entry = ttk.Entry(row4)
        self.model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 接口地址
        row5 = ttk.Frame(main)
        row5.pack(fill=tk.X, pady=5)
        ttk.Label(row5, text="接口地址：", width=12).pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(row5)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 底部按钮
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(bottom, text="删除此配置", command=self._delete_profile).pack(side=tk.LEFT)
        ttk.Button(bottom, text="保存此配置", command=self._save_profile).pack(side=tk.RIGHT)

    def _refresh_profiles_list(self):
        profiles = list(self.config_data.get("profiles", {}).keys())
        self.edit_profile_combo["values"] = profiles
        if profiles:
            self.edit_profile_combo.current(0)
            self._on_profile_selected()
        else:
            self._new_profile()

    def _on_profile_selected(self, event=None):
        name = self.edit_profile_var.get()
        if not name: return
        p = self.config_data["profiles"].get(name, {})

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)

        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, p.get("api_key", ""))

        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, p.get("model", ""))

        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, p.get("url", ""))

        # 尝试匹配服务商
        for provider, info in PROVIDERS.items():
            if info["url"] == p.get("url"):
                self.provider_var.set(provider)
                break
        else:
            self.provider_var.set("自定义")

    def _new_profile(self):
        self.edit_profile_var.set("")
        self.edit_profile_combo.set("")
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, "新配置")
        self.provider_var.set("DeepSeek")
        self._on_provider_change()
        self.key_entry.delete(0, tk.END)

    def _on_provider_change(self, event=None):
        provider = self.provider_var.get()
        info = PROVIDERS.get(provider, {})
        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, info.get("default_model", ""))
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, info.get("url", ""))

    def _save_profile(self):
        name = self.name_entry.get().strip()
        key = self.key_entry.get().strip()
        model = self.model_entry.get().strip()
        url = self.url_entry.get().strip()

        if not name or not key or not model or not url:
            messagebox.showwarning("提示", "所有字段均不能为空！", parent=self)
            return

        # 检查重命名冲突
        old_name = self.edit_profile_var.get()
        if old_name and old_name != name and name in self.config_data["profiles"]:
            messagebox.showwarning("提示", "该配置名称已存在，请换一个！", parent=self)
            return

        # 如果改名了，删掉旧的
        if old_name and old_name != name:
            del self.config_data["profiles"][old_name]
            if self.config_data.get("active_profile") == old_name:
                self.config_data["active_profile"] = name

        self.config_data["profiles"][name] = {
            "api_key": key,
            "model": model,
            "url": url
        }

        # 如果是第一个配置，自动设为激活
        if not self.config_data.get("active_profile"):
            self.config_data["active_profile"] = name

        save_config(self.config_data)
        messagebox.showinfo("成功", "配置已保存！", parent=self)

        self.edit_profile_var.set(name)
        self._refresh_profiles_list()
        if self.on_saved:
            self.on_saved()

    def _delete_profile(self):
        name = self.edit_profile_var.get()
        if not name:
            return
        if messagebox.askyesno("确认", f"确定要删除配置「{name}」吗？", parent=self):
            if name in self.config_data["profiles"]:
                del self.config_data["profiles"][name]

            if self.config_data.get("active_profile") == name:
                self.config_data["active_profile"] = ""

            save_config(self.config_data)
            self._new_profile()
            self._refresh_profiles_list()
            if self.on_saved:
                self.on_saved()