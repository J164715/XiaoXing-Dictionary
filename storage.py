# storage.py
# -*- coding: utf-8 -*-
import os
import re
import unicodedata
from docx import Document

WORD_FILE = "Dictionary_Records.docx"

# 匹配 "原文：xxx" / "原文:xxx"，容忍全半角冒号、首尾空白
_ORIGINAL_PATTERN = re.compile(r"^\s*原文\s*[：:]\s*(.+?)\s*$")


def _normalize(s: str) -> str:
    """
    统一规范化，用于比较：
    - NFKC：全角字母/数字/标点 → 半角（Ａｐｐｌｅ → Apple）
    - 去掉不换行空格 \u00A0、零宽字符 \u200B
    - strip + lower
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00A0", " ").replace("\u200B", "")
    return s.strip().lower()


def init_storage():
    """
    确保 Word 文件存在并带有标题。
    若文件存在但损坏（无法打开），备份为 .bak 后重建。
    """
    if os.path.exists(WORD_FILE):
        try:
            Document(WORD_FILE)  # 能打开即认为正常
            return
        except Exception as e:
            print(f"检测到 Word 文件损坏，将备份并重建: {e}")
            try:
                bak = WORD_FILE + ".bak"
                if os.path.exists(bak):
                    import time
                    bak = f"{WORD_FILE}.{int(time.time())}.bak"
                os.replace(WORD_FILE, bak)
                print(f"原文件已备份为: {bak}")
            except Exception as be:
                print(f"备份损坏文件失败: {be}")
    try:
        doc = Document()
        doc.add_heading('英语词典查询记录', 0)
        doc.save(WORD_FILE)
    except Exception as e:
        print(f"创建 Word 文件失败: {e}")


def check_exists(query_text: str) -> bool:
    """
    检查该词是否已经保存在 Word 中。
    提取每段的"原文：xxx"值，规范化后比较。
    """
    if not query_text or not os.path.exists(WORD_FILE):
        return False

    target = _normalize(query_text)
    if not target:
        return False

    try:
        doc = Document(WORD_FILE)
    except Exception as e:
        print(f"读取 Word 失败（无法判断是否已存在）: {e}")
        return False

    for para in doc.paragraphs:
        text = para.text
        if not text:
            continue
        m = _ORIGINAL_PATTERN.match(text)
        if not m:
            continue
        if _normalize(m.group(1)) == target:
            return True
    return False


def save_record(query_text: str, result_text: str) -> tuple[bool, str]:
    """
    直接追加保存到 Word。结果文本按行拆分为多个段落，确保真正换行。
    """
    if not query_text or not result_text:
        return False, "没有可保存的内容。"

    if check_exists(query_text):
        return False, "该内容已经保存在文档中了！"

    if not os.path.exists(WORD_FILE):
        init_storage()

    try:
        doc = Document(WORD_FILE)
    except Exception as e:
        print(f"打开 Word 失败，尝试重建: {e}")
        init_storage()
        try:
            doc = Document(WORD_FILE)
        except Exception as e2:
            return False, f"无法打开 Word 文档：{e2}"

    try:
        doc.add_paragraph(f"原文：{query_text}")

        # 结果按行分段，确保 Word 内真正换行
        doc.add_paragraph("结果：")
        for line in result_text.split("\n"):
            doc.add_paragraph(line)

        doc.add_paragraph("-" * 40)
        doc.save(WORD_FILE)
        return True, "成功保存到 Dictionary_Records.docx"
    except Exception as e:
        return False, f"无法写入 Word 文档：{str(e)}"


def delete_record(query_text: str) -> tuple[bool, str]:
    """
    从 Word 中删除指定词的整条记录。
    删除范围：从"原文：xxx"段落到其后第一个分隔线（40 个 '-'）为止（含）。
    若无分隔线（异常结构），只删"原文"及紧随的结果段落。
    """
    if not query_text or not os.path.exists(WORD_FILE):
        return False, "没有可删除的记录。"

    target = _normalize(query_text)
    if not target:
        return False, "没有可删除的记录。"

    try:
        doc = Document(WORD_FILE)
    except Exception as e:
        return False, f"无法打开 Word 文档：{e}"

    # 1) 定位目标"原文："段落
    target_idx = None
    for i, para in enumerate(doc.paragraphs):
        m = _ORIGINAL_PATTERN.match(para.text or "")
        if m and _normalize(m.group(1)) == target:
            target_idx = i
            break

    if target_idx is None:
        return False, "文档中未找到该记录。"

    # 2) 向后扫描到分隔线；若没找到，退化为"删到下一个原文前"
    end_idx = target_idx
    found_sep = False
    for j in range(target_idx + 1, len(doc.paragraphs)):
        text = (doc.paragraphs[j].text or "").strip()
        end_idx = j
        if text and set(text) == {"-"}:   # 40 个 '-' 的分隔线
            found_sep = True
            break
        # 若遇到下一个"原文："，说明上一条没有分隔线，停在它前面
        if _ORIGINAL_PATTERN.match(text):
            end_idx = j - 1
            break

    if not found_sep and end_idx == len(doc.paragraphs) - 1:
        # 扫到末尾仍无分隔线，end_idx 已是最后一段
        pass

    if end_idx < target_idx:
        end_idx = target_idx

    # 3) 删除区间 [target_idx, end_idx]
    try:
        for p in doc.paragraphs[target_idx:end_idx + 1]:
            p._element.getparent().remove(p._element)
        doc.save(WORD_FILE)
        return True, "已取消保存，记录已从文档删除"
    except Exception as e:
        return False, f"删除失败：{e}"