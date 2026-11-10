# history.py
# -*- coding: utf-8 -*-
"""
查询历史（四六级背单词场景）。
- 持久化到 query_history.json
- 按词去重：同词只保留最新一条，移到最前
- 每条记录含：词、结果、来源、时间、查询次数快照
- 支持导出选中词为 Word
"""
import json
import os
import threading
import unicodedata
from datetime import datetime

HISTORY_FILE = "query_history.json"
MAX_HISTORY = 500   # 最多保留 500 条，超出淘汰最旧

_lock = threading.Lock()


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00A0", " ").replace("\u200B", "")
    return s.strip().lower()


def _load() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"读取历史失败: {e}")
        return []


def _save(data: list):
    try:
        tmp = HISTORY_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, HISTORY_FILE)
    except Exception as e:
        print(f"写入历史失败: {e}")


def add_history(word: str, result: str, source: str, count_at_query: int = 0):
    """追加一条历史（按词去重：同词只保留最新一条，移到最前）"""
    key = word.strip()
    if not key:
        return
    key_lower = _normalize(key)
    with _lock:
        data = _load()
        data = [x for x in data if _normalize(x.get("word", "")) != key_lower]
        data.insert(0, {
            "word": key,
            "result": result,
            "source": source,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "count_at_query": int(count_at_query),
        })
        if len(data) > MAX_HISTORY:
            data = data[:MAX_HISTORY]
        _save(data)


def get_history() -> list:
    """返回历史列表（最新的在前）"""
    with _lock:
        return _load()


def get_history_result(word: str) -> dict:
    """按词查历史条目（不重查 API）"""
    key_lower = _normalize(word)
    for item in _load():
        if _normalize(item.get("word", "")) == key_lower:
            return item
    return {}


def export_history(selected_words: list, export_path: str) -> tuple[bool, str]:
    """
    把选中的词导出为 Word。
    selected_words 可以是原始词列表；按规范化后匹配历史条目。
    """
    try:
        from docx import Document
    except ImportError:
        return False, "缺少 python-docx，无法导出 Word。"

    data = _load()
    index = {_normalize(x.get("word", "")): x for x in data}

    items = []
    for w in selected_words:
        item = index.get(_normalize(w))
        if item:
            items.append(item)

    if not items:
        return False, "选中的记录在历史中不存在。"

    try:
        doc = Document()
        doc.add_heading('查询历史导出', 0)
        doc.add_paragraph(f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"共 {len(items)} 条")
        doc.add_paragraph("")

        for item in items:
            doc.add_paragraph(f"原文：{item.get('word', '')}")
            doc.add_paragraph(f"查询时间：{item.get('ts', '')}")
            doc.add_paragraph(f"累计查询次数：{item.get('count_at_query', 0)}")
            doc.add_paragraph("结果：")
            for line in str(item.get("result", "")).split("\n"):
                doc.add_paragraph(line)
            doc.add_paragraph("-" * 40)

        doc.save(export_path)
        return True, f"已导出 {len(items)} 条到 {export_path}"
    except Exception as e:
        return False, f"导出失败：{e}"