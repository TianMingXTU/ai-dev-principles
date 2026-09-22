#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mode_router.py -- 判定「学习模式」还是「生产模式」，并输出 AI 侧协作参数。

用法:
    python mode_router.py "帮我实现一个 JWT 登录接口"
    python mode_router.py --text "再给我讲讲这里为什么要用锁" --json
    python mode_router.py --list-signals
    python mode_router.py              # 无参数时从 stdin 读取一行

纯标准库实现。不联网、不写文件、不修改任何东西。
"""

from __future__ import annotations

import argparse
import json
import sys

# ---------------------------------------------------------------------------
# 信号词表：从《我的开发原则》中「学习追求能力 / 生产追求效率」提炼
# ---------------------------------------------------------------------------

LEARNING_SIGNALS = {
    "学习": 3, "练习": 3, "训练": 3, "搞懂": 3, "弄懂": 3, "弄明白": 3,
    "刷题": 3, "面试": 3, "八股": 3, "教我": 3, "不看答案": 3,
    "打基础": 3, "从零": 2, "手写": 2, "重写一遍": 2, "原理": 2,
    "为什么": 2, "怎么实现的": 2, "底层": 2, "讲解": 2, "教程": 2,
    "入门": 2, "自己写": 2, "复习": 2, "笔记": 1, "推导": 2,
    "自己实现": 2, "自己 debug": 3, "debug 一下": 1,
}

PRODUCTION_SIGNALS = {
    "上线": 3, "交付": 3, "提测": 3, "发版": 3, "线上": 3,
    "deadline": 3, "紧急": 3, "赶紧": 3, "尽快": 3, "加班": 2,
    "修 bug": 3, "修bug": 3, "修复": 2, "今天要": 3, "明天要": 3,
    "这周要": 3, "排期": 2, "发布": 2, "生产环境": 3, "项目里": 2,
    "业务要": 2, "需求要": 2, "效率": 2, "重构": 1, "帮我改": 2,
    "帮我写": 1, "先跑起来": 2, "能跑就行": 2,
}

# ---------------------------------------------------------------------------
# 两种模式的协作参数
# ---------------------------------------------------------------------------

LEARNING_PROFILE = {
    "mode": "学习模式",
    "goal": "让能力进入大脑（训练追求能力）",
    "give": [
        "提示与引导方向，不给完整答案",
        "检查清单：让用户自查是否遗漏",
        "反例与常见错误，让用户自己对比",
        "官方文档 / 源码入口",
    ],
    "withhold": [
        "完整的可运行实现",
        "直接的最终答案",
        "替用户完成的推导过程",
    ],
    "allow_slow": "允许。慢是成本的一部分，不是浪费。",
    "opening": "这次按学习模式来：我先不给答案。你先说说你会怎么分析和设计，我再帮你找漏洞和边界。",
    "closing": "在写下第一行代码前，先回答：你的方案是什么？你为什么排除其他方案？边界在哪？",
}

PRODUCTION_PROFILE = {
    "mode": "生产模式",
    "goal": "效率、质量、结果（生产追求效率）",
    "give": [
        "可直接使用的最小实现 / Demo",
        "框架与 API 的完整用法：参数、返回值、推荐写法、易踩的坑",
        "工具链建议、测试与验证方案",
        "样板代码、重复劳动的自动化",
    ],
    "withhold": [
        "替用户做的方案设计与关键判断",
        "对复杂逻辑 / 并发 / 状态 / 算法的最终定论",
        "对结果的验证结论",
    ],
    "allow_slow": "不允许。慢在这里是浪费。",
    "opening": "这次按生产模式来：我直接给你 API 用法和可用的实现骨架，但业务判断和核心实现你自己拿。",
    "closing": "交付前确认：这段代码的业务前提对不对？出错你从哪查？你打算怎么验证？",
}

MIXED_PROFILE = {
    "mode": "混合（需分阶段）",
    "goal": "同一任务里既有学习诉求又有交付压力，必须分阶段处理",
    "give": [
        "先把任务切成「要交付的部分」和「要学明白的部分」",
        "交付部分：充分开卷，给实现与工具",
        "学习部分：闭卷训练，只给提示与检查项",
    ],
    "withhold": [
        "不要把学习部分也顺手写完，否则等于放弃了训练目标",
    ],
    "allow_slow": "分段决定：交付段求快，学习段允许慢。",
    "opening": "这个任务里我听到了两种诉求。我们分开：哪部分是今天必须交付的？哪部分是你想借此学明白的？",
    "closing": "确认清单：交付部分验证过了吗？学习部分你能独立复现吗？",
}

BUDGET = [
    (50, "可直接交付", "整段给，无需声明"),
    (150, "需要显式审核", "交付前声明「这段需要你逐行看」，并给出阅读顺序"),
    (300, "高成本，建议拆分", "先拆分，一次只给一块"),
    (10 ** 9, "超出审核带宽，必须拆分", "不交付；改为输出任务拆解清单 + 第一块实现"),
]


def score(text: str):
    hits_learn, hits_prod = [], []
    learn = prod = 0
    low = text.lower()
    for word, weight in LEARNING_SIGNALS.items():
        if word.lower() in low:
            hits_learn.append("%s(+%d)" % (word, weight))
            learn += weight
    for word, weight in PRODUCTION_SIGNALS.items():
        if word.lower() in low:
            hits_prod.append("%s(+%d)" % (word, weight))
            prod += weight
    return learn, prod, hits_learn, hits_prod


def decide(learn: int, prod: int):
    if learn == 0 and prod == 0:
        return MIXED_PROFILE, "无信号", 0.0
    total = learn + prod
    if learn >= prod * 1.5:
        return LEARNING_PROFILE, "学习模式", round(learn / float(total), 2)
    if prod >= learn * 1.5:
        return PRODUCTION_PROFILE, "生产模式", round(prod / float(total), 2)
    return MIXED_PROFILE, "混合", 0.5


def budget_for(lines: int) -> str:
    for limit, label, action in BUDGET:
        if lines <= limit:
            return "%d 行 -> %s：%s" % (lines, label, action)
    return ""


def render(text: str, profile: dict, label: str, confidence: float,
           learn: int, prod: int, hits_learn, hits_prod) -> str:
    out = []
    out.append("=" * 64)
    out.append("任务描述：%s" % (text.strip() or "(空)"))
    out.append("判定结果：%s   (置信度 %.2f)" % (label, confidence))
    out.append("信号得分：学习 %d / 生产 %d" % (learn, prod))
    if hits_learn:
        out.append("  学习信号：%s" % ", ".join(hits_learn))
    if hits_prod:
        out.append("  生产信号：%s" % ", ".join(hits_prod))
    out.append("-" * 64)
    out.append("目标：%s" % profile["goal"])
    out.append("")
    out.append("AI 应该给：")
    for item in profile["give"]:
        out.append("  + %s" % item)
    out.append("AI 不应该给：")
    for item in profile["withhold"]:
        out.append("  - %s" % item)
    out.append("允许慢吗：%s" % profile["allow_slow"])
    out.append("")
    out.append("建议开场：%s" % profile["opening"])
    out.append("建议收尾：%s" % profile["closing"])
    out.append("")
    out.append("输出预算（按代码行数）：")
    for limit, lbl, action in BUDGET:
        cap = "∞" if limit > 10 ** 8 else str(limit)
        out.append("  <= %-5s %s -- %s" % (cap, lbl, action))
    out.append("")
    out.append("下一步：确认业务目的 / 流程 / 规则 / 输入输出 / 边界，再进入技术方案。")
    out.append("=" * 64)
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="判定学习/生产模式，输出 AI 协作参数与输出预算")
    parser.add_argument("text", nargs="*", help="任务描述")
    parser.add_argument("--text", dest="text_opt", default=None, help="任务描述（显式）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--budget-lines", type=int, default=None,
                        help="只查询指定行数对应的输出预算")
    parser.add_argument("--list-signals", action="store_true", help="打印信号词表")
    args = parser.parse_args(argv)

    if args.list_signals:
        print("学习信号：%s" % ", ".join(sorted(LEARNING_SIGNALS)))
        print("生产信号：%s" % ", ".join(sorted(PRODUCTION_SIGNALS)))
        return 0

    if args.budget_lines is not None:
        print(budget_for(args.budget_lines))
        return 0

    text = args.text_opt if args.text_opt is not None else " ".join(args.text)
    if not text and not sys.stdin.isatty():
        text = sys.stdin.readline()
    if not text:
        parser.print_help()
        return 1

    learn, prod, hits_learn, hits_prod = score(text)
    profile, label, confidence = decide(learn, prod)

    if args.json:
        payload = {
            "text": text.strip(),
            "mode": label,
            "confidence": confidence,
            "score": {"learning": learn, "production": prod},
            "hits": {"learning": hits_learn, "production": hits_prod},
            "profile": profile,
            "budget": [{"limit": l, "label": lb, "action": a}
                       for l, lb, a in BUDGET],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(text, profile, label, confidence,
                     learn, prod, hits_learn, hits_prod))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
