# services.py
# -*- coding: utf-8 -*-
import os
import re
import shutil
from datetime import datetime

from translator import call_deepseek, query_local_fallback
from storage import init_storage, check_exists, save_record, delete_record, WORD_FILE
from stats import record_query, get_query_count
from history import add_history

init_storage()

_REFUSAL_PATTERNS = [
    re.compile(r"^\s*i'?m sorry", re.IGNORECASE),
    re.compile(r"^\s*i am sorry", re.IGNORECASE),
    re.compile(r"^\s*i cannot help", re.IGNORECASE),
    re.compile(r"^\s*i can'?t help", re.IGNORECASE),
    re.compile(r"^\s*无法协助", re.IGNORECASE),
    re.compile(r"^\s*抱歉", re.IGNORECASE),
]
_REFUSAL_MAX_LEN = 80


def _looks_like_refusal(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) > _REFUSAL_MAX_LEN:
        return False
    return any(p.match(stripped) for p in _REFUSAL_PATTERNS)


def translate_text(src_text: str) -> tuple[str, str]:
    """核心调度：大模型为主，本地兜底。查询前记次数，成功后写历史。"""
    record_query(src_text)   # 次数 +1

    success, final_result = call_deepseek(src_text)

    if success and _looks_like_refusal(final_result) and not _looks_like_refusal(src_text):
        success = False

    if success:
        _record_history_safe(src_text, final_result, "DeepSeek API (主力)")
        return final_result, "DeepSeek API (主力)"

    success, final_result = query_local_fallback(src_text)
    if success:
        _record_history_safe(src_text, final_result, "本地 wd 词库 (API失败保底)")
        return final_result, "本地 wd 词库 (API失败保底)"

    return "查询失败，请稍后重试或检查网络连接。", "查询失败"


def _record_history_safe(word: str, result: str, source: str):
    """写历史失败不影响主流程"""
    try:
        count = get_query_count(word)
        add_history(word, result, source, count)
    except Exception as e:
        print(f"写历史失败: {e}")


def init_word_doc():
    init_storage()


def check_word_exists(query_text: str) -> bool:
    return check_exists(query_text)


def save_to_word(query_text: str, result_text: str) -> tuple[bool, str]:
    return save_record(query_text, result_text)


def delete_from_word(query_text: str) -> tuple[bool, str]:
    return delete_record(query_text)


def get_count(query_text: str) -> int:
    return get_query_count(query_text)


def export_favorites(dest_path: str) -> tuple[bool, str]:
    """
    导出收藏记录：直接复制 Dictionary_Records.docx 到目标位置。
    """
    if not os.path.exists(WORD_FILE):
        return False, "暂无收藏记录。"
    try:
        shutil.copy2(WORD_FILE, dest_path)
        return True, f"已导出收藏到 {dest_path}"
    except Exception as e:
        return False, f"导出收藏失败：{e}"


def default_export_filename(prefix: str) -> str:
    """生成默认导出文件名，如 查询历史_20261109.docx"""
    stamp = datetime.now().strftime("%Y%m%d")
    return f"{prefix}_{stamp}.docx"