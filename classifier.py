# classifier.py
# -*- coding: utf-8 -*-
import re
import json
import os

import jieba

try:
    from lemminflect import getAllLemmas
except ImportError:
    getAllLemmas = None


DICTIONARY_FILE = "dictionary.json"

# C3：单字虚词，单字输入时直接否决；出现在词首尾时倾向判为句子片段
FUNCTION_CHARS = set("的了着过吗呢吧啊呀哦嗯嘛哈呗啦哇")

# C4：jieba 会切成 1 个词、但语义上是短语的黑名单
PHRASE_BLACKLIST = {
    "没关系", "不得了", "差不多", "不得已", "不好意思",
    "没什么", "不客气", "对不起", "为什么", "怎么办",
    "没问题", "不要紧", "不敢当", "不怎么样",
}


def is_chinese_word(text: str) -> bool:
    """
    判断是否为可走"模板B（中文单独词语）"的短词汇。

    返回 False 的情况：
      - 非纯汉字
      - 单字虚词（的、了、吗…）
      - 命中短语黑名单（没关系、不得了…）
      - 首/尾为虚词的句子片段（吃饭了、你好吗…）
      - ≤3 字但 jieba 切成多词（句子片段）
      - 4 字（成语走模板D，专有名词走模板C，都不该走模板B）
      - ≥5 字但 jieba 切成多词
    """
    text = text.strip()
    if not re.fullmatch(r"[\u4e00-\u9fa5]+", text):
        return False

    # C3：单字只保留实词，排除纯虚词
    if len(text) == 1:
        return text not in FUNCTION_CHARS

    # C4：短语黑名单直接否决
    if text in PHRASE_BLACKLIST:
        return False

    # 首/尾为虚词，基本是句子片段（吃饭了、你好吗）
    # 只查首尾，避免误伤"目的""的确"这类中间含虚词的真词
    if text[0] in FUNCTION_CHARS or text[-1] in FUNCTION_CHARS:
        return False

    words = list(jieba.cut(text))
    n_words = len(words)

    # C1：≤3 字，jieba 切成 1 个词才算词
    if len(text) <= 3:
        return n_words == 1

    # C2：4 字一律 False
    # 成语→模板D，专有名词/普通长词→模板C，均不走模板B
    if len(text) == 4:
        return False

    # ≥5 字：只有 jieba 切成 1 个词才算真长词（社会主义、奥林匹克…）
    return n_words == 1


def get_lemma_hints(text: str) -> str:
    """获取本地词形库参考提示（C5 修复：验证返回结构）"""
    if not re.fullmatch(r"[A-Za-z]+", text) or not getAllLemmas:
        return ""
    try:
        lemmas_dict = getAllLemmas(text)

        # C5：返回值必须是 dict
        if not isinstance(lemmas_dict, dict):
            return ""

        all_lemmas = []
        for upos, lemmas in lemmas_dict.items():
            # value 是字符串时整体加入，避免 extend 拆成单字符
            if isinstance(lemmas, str):
                all_lemmas.append(lemmas)
            # value 是可迭代对象（tuple/list/set 等）时展开
            elif hasattr(lemmas, "__iter__"):
                all_lemmas.extend(lemmas)
            # 其他类型（None/int 等）跳过，不污染结果

        all_lemmas = sorted(set(all_lemmas))  # 顺序稳定，提示可复现

        if all_lemmas:
            return (f"【本地词形库参考】：系统检测到该词的词形变体或原形可能包含："
                    f"{', '.join(all_lemmas)}。请在生成模板A时，优先参考这些词族，不要遗漏。\n")
    except Exception as e:
        print(f"本地词形库查询异常: {e}")
    return ""


def get_local_phrases(word: str) -> list:
    """
    从本地 dictionary.json 中检索固定搭配（C6 修复）。
    三级匹配，消除原版"死分支 + 小写化抢占"的冲突：
      1) 原始大小写精确命中（最高优先级）
      2) 小写命中（忽略大小写）
      3) 遍历兜底（兼容 key 大小写不统一，如 APPLE / Apple）
    """
    if not os.path.exists(DICTIONARY_FILE):
        return []
    try:
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print("dictionary.json 根节点不是对象，忽略")
            return []

        target = word.strip().lower()

        # 1) 原始大小写精确命中
        if word.strip() in data:
            return data[word.strip()]

        # 2) 小写命中（忽略大小写）
        if target in data:
            return data[target]

        # 3) 遍历兜底
        for k, v in data.items():
            if isinstance(k, str) and k.strip().lower() == target:
                return v
    except Exception as e:
        print(f"读取本地词典失败: {e}")
    return []