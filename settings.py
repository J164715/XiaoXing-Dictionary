# settings.py
import json
import os
import sys
import win32com.client

CONFIG_FILE = "config.json"
DATA_DIR = "小星词典数据"

PROVIDERS = {
    "DeepSeek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "default_model": "deepseek-chat"
    },
    "Kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "default_model": "moonshot-v1-8k"
    },
    "豆包 (火山引擎)": {
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "default_model": "您的接入点ID (ep-xxxxxx)" 
    },
    "阿里通义千问": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "default_model": "qwen-turbo"
    },
    "自定义": {
        "url": "",
        "default_model": ""
    }
}

DEFAULT_CONFIG = {
    "active_profile": "",  # 当前使用的配置名称
    "profiles": {}         # 保存的所有配置，格式为 {"配置名称": {api_key: "", model: "", url: ""}}
}

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

def get_data_dir():
    path = os.path.join(get_app_dir(), DATA_DIR)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_config_path():
    return os.path.join(get_data_dir(), CONFIG_FILE)

CONFIG_PATH = get_config_path()

def load_config():
    """加载完整配置文件"""
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 兼容旧版本数据格式
            if "profiles" not in data:
                return DEFAULT_CONFIG.copy()
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(data):
    """保存完整配置文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_active_profile():
    """获取当前选中的配置详情（供 translator.py 调用）"""
    cfg = load_config()
    active_name = cfg.get("active_profile")
    if not active_name or active_name not in cfg["profiles"]:
        return None
    return cfg["profiles"][active_name]