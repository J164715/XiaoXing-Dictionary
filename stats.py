# stats.py
# -*- coding: utf-8 -*-
"""
查询次数统计（四六级背单词场景）。
- 跨会话持久化到 query_stats.json
- 只存 {规范化词: 次数}，不存查询内容/结果
- 原子写入，防文件损坏
"""
import json
import os
import threading
import unicodedata

STATS_FILE = "query_stats.json"
_lock = threading.Lock()


def _normalize(s: str) -> str:
    """与 storage._normalize 一致，保证"同一词"的判定跨模块统一"""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00A0", " ").replace("\u200B", "")
    return s.strip().lower()


def _load() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"读取统计文件失败: {e}")
        return {}


def _save(data: dict):
    try:
        tmp = STATS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATS_FILE)   # 原子写
    except Exception as e:
        print(f"写入统计文件失败: {e}")


def record_query(text: str) -> int:
    """记录一次查询，返回该词累计次数"""
    key = _normalize(text)
    if not key:
        return 0
    with _lock:
        data = _load()
        data[key] = int(data.get(key, 0)) + 1
        _save(data)
        return data[key]


def get_query_count(text: str) -> int:
    """读取该词累计查询次数（不 +1）"""
    key = _normalize(text)
    if not key:
        return 0
    with _lock:
        data = _load()
        return int(data.get(key, 0))


def clear_stats():
    """清空所有统计（可选的维护入口）"""
    with _lock:
        _save({})