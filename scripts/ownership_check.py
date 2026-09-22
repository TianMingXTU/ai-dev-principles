#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ownership_check.py -- 对代码变更做「认知所有权 / 审核带宽」自检。

核心命题：复制不是问题，不理解才是问题。
真正的瓶颈不是 AI 的代码生成能力，而是人的审核带宽。

用法:
    python ownership_check.py <文件或目录>
    python ownership_check.py <目录> --json
    python ownership_check.py --diff patch.diff
    python ownership_check.py <目录> --ext .py,.ts --budget 50

纯标准库实现。只读文件，不写文件、不修改任何东西。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

BUDGET_TIERS = [
    (50, "舒适区", "可以直接理解整段。"),
    (150, "需要显式审核", "交付前必须声明「这段要逐行看」，并给出阅读顺序。"),
    (300, "高成本", "审核成本明显上升，建议拆成多块分别验证。"),
    (10 ** 9, "超出审核带宽", "不要一次性接受，必须拆分；否则等于没有 review。"),
]

CODE_EXTS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".java", ".kt", ".kts", ".go", ".rs", ".c", ".h", ".cc", ".cpp",
    ".hpp", ".cs", ".rb", ".php", ".swift", ".m", ".mm", ".scala",
    ".sh", ".bash", ".zsh", ".ps1", ".sql", ".vue", ".svelte",
}

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "dist", "build", "out",
    "target", "__pycache__", ".venv", "venv", "env", ".idea", ".vscode",
    "vendor", "coverage", ".next", ".nuxt", "site-packages",
}

# 函数 / 类 / 块 的起点（启发式，覆盖主流语言）
BLOCK_START = re.compile(
    r"^(\s*)"
    r"(?:@\w+(?:\([^)]*\))?\s*)?"                              # 装饰器/注解
    r"(?:export\s+|default\s+|public\s+|private\s+|protected\s+|"
    r"static\s+|async\s+|final\s+|abstract\s+|virtual\s+|override\s+|"
    r"inline\s+|suspend\s+|open\s+|sealed\s+|partial\s+)*"
    r"(?:def|function|func|fn|class|interface|enum|struct|impl|trait|"
    r"module|namespace)\s+([A-Za-z_$][\w$]*)"
)

ARROW_BLOCK = re.compile(
    r"^(\s*)(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
    r"\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)

COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", "<!--", '"""', "'''", "%")

SMELLS = {
    "空 except / catch（吞掉异常）": re.compile(
        r"except\s*:\s*(?:\n|$)|except\s+Exception\s*:\s*pass|catch\s*\([^)]*\)\s*\{\s*\}"),
    "裸 TODO / FIXME": re.compile(r"(?:TODO|FIXME|XXX|HACK)\b", re.IGNORECASE),
    "硬编码疑似密钥": re.compile(
        r"(?i)(?:password|passwd|secret|token|api[_-]?key|access[_-]?key)"
        r"\s*[:=]\s*[\"'][^\"']{6,}[\"']"),
    "魔法数字（>=4 位数值字面量）": re.compile(r"(?<![\w.])\d{4,}(?![\w.])"),
    "被注释掉的代码块": re.compile(r"^\s*(?:#|//)\s*(?:if|for|while|return|def|function)\b",
                                   re.MULTILINE),
}


def is_code_file(path: str, exts) -> bool:
    return os.path.splitext(path)[1].lower() in exts


def iter_files(target: str, exts):
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in sorted(files):
            full = os.path.join(root, name)
            if is_code_file(full, exts):
                yield full


def read_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError as exc:
        print("! 无法读取 %s: %s" % (path, exc), file=sys.stderr)
        return []


def shorten(path: str, width: int) -> str:
    """过长路径保留尾部语义，前缀加省略号，避免被误读成另一个路径。"""
    return path if len(path) <= width else "…" + path[-(width - 1):]


def block_length(lines, start_idx: int, start_indent: int) -> int:
    """启发式估算块长度：缩进回到同级、且花括号已闭合时结束。"""
    depth = 0
    for j in range(start_idx, len(lines)):
        line = lines[j]
        if j > start_idx:
            stripped = line.strip()
            if stripped and depth <= 0:
                indent = len(line) - len(line.lstrip())
                if indent <= start_indent:
                    return j - start_idx
        depth += line.count("{") + line.count("(") - line.count("}") - line.count(")")
        if depth < 0:
            depth = 0
    return len(lines) - start_idx


def analyze(path: str, rel: str):
    lines = read_lines(path)
    if not lines:
        return None

    total = len(lines)
    blank = 0
    comment = 0
    code = 0
    in_block_comment = False

    for raw in lines:
        s = raw.strip()
        if not s:
            blank += 1
            continue
        if in_block_comment:
            comment += 1
            if "*/" in s or '"""' in s or "'''" in s:
                in_block_comment = False
            continue
        if s.startswith(("/*", '"""', "'''")):
            comment += 1
            if not (s.endswith(("*/", '"""', "'''")) and len(s) > 4):
                in_block_comment = True
            continue
        if s.startswith(COMMENT_PREFIXES):
            comment += 1
            continue
        code += 1

    blocks = []
    for idx, raw in enumerate(lines):
        m = BLOCK_START.match(raw) or ARROW_BLOCK.match(raw)
        if m:
            name = m.group(2)
            indent = len(m.group(1).replace("\t", "    "))
            blocks.append((name, idx + 1, block_length(lines, idx, indent)))

    smells = {}
    joined = "\n".join(lines)
    for label, pattern in SMELLS.items():
        found = pattern.findall(joined)
        if found:
            smells[label] = len(found)

    return {
        "path": rel,
        "total": total,
        "code": code,
        "comment": comment,
        "blank": blank,
        "blocks": blocks,
        "longest": max((b[2] for b in blocks), default=0),
        "longest_name": max(blocks, key=lambda b: b[2])[0] if blocks else "-",
        "smells": smells,
    }


def tier_for(code_lines: int):
    for limit, label, action in BUDGET_TIERS:
        if code_lines <= limit:
            return label, action
    return BUDGET_TIERS[-1][1], BUDGET_TIERS[-1][2]


SELF_CHECK = [
    "为什么这样设计？有没有更简单的方案？",
    "这段代码解决了什么业务问题？",
    "这里为什么调用这个 API？参数为什么这么传？",
    "还有没有其他方案？为什么没选它们？",
    "有什么风险？边界条件有哪些？",
    "出现问题应该从哪里开始查？",
    "我是怎么验证它的？我能向别人解释它吗？",
    "我愿不愿意对它的最终结果负责？",
]


def report(results, budget: int, show_self_check: bool) -> str:
    out = []
    out.append("=" * 66)
    out.append("认知所有权 / 审核带宽自检")
    out.append("=" * 66)

    total_code = sum(r["code"] for r in results)
    out.append("文件数：%d    代码行数合计：%d" % (len(results), total_code))
    out.append("")

    worst = sorted(results, key=lambda r: r["code"], reverse=True)[:8]
    out.append("按代码行数排序（前 8）：")
    for r in worst:
        label, _ = tier_for(r["code"])
        out.append("  %-46s %5d 行  [%s]" % (shorten(r["path"], 46), r["code"], label))
    out.append("")

    label, action = tier_for(total_code)
    out.append("-" * 66)
    out.append("整体判定：%s" % label)
    out.append("建议动作：%s" % action)
    if total_code > budget:
        chunks = (total_code + budget - 1) // budget
        out.append("按每块 %d 行计算，至少需要拆成 %d 块，逐块理解、逐块验证。"
                   % (budget, chunks))
    out.append("")

    long_blocks = [r for r in results if r["longest"] > budget]
    if long_blocks:
        out.append("单个函数/方法超出单块预算（这些是最容易「看不懂就放过去」的地方）：")
        for r in sorted(long_blocks, key=lambda x: x["longest"], reverse=True)[:8]:
            out.append("  %s :: %s  (%d 行)" % (r["path"], r["longest_name"], r["longest"]))
        out.append("")

    smell_rows = [(r["path"], k, v) for r in results for k, v in r["smells"].items()]
    if smell_rows:
        out.append("需要人工确认的信号（脚本只做提示，不代表一定是问题）：")
        for path, k, v in smell_rows[:12]:
            out.append("  [%s x%d] %s" % (k, v, path))
        out.append("")

    out.append("-" * 66)
    out.append("审核前请能回答以下问题（答不上来就先别提交）：")
    items = SELF_CHECK if show_self_check else SELF_CHECK[:4]
    for i, q in enumerate(items, 1):
        out.append("  %2d. %s" % (i, q))
    out.append("")
    out.append("提醒：复制不是问题，不理解才是问题。")
    out.append("=" * 66)
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="对代码做认知所有权与审核带宽自检")
    parser.add_argument("path", nargs="?", help="目标文件或目录")
    parser.add_argument("--diff", default=None, help="分析 diff 文件（按新增行统计）")
    parser.add_argument("--ext", default=None, help="逗号分隔的扩展名白名单，如 .py,.ts")
    parser.add_argument("--budget", type=int, default=50, help="单块行数预算，默认 50")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument("--quiet", action="store_true", help="只输出判定结论")
    args = parser.parse_args(argv)

    exts = CODE_EXTS
    if args.ext:
        exts = {e.strip() if e.strip().startswith(".") else "." + e.strip()
                for e in args.ext.split(",") if e.strip()}

    results = []

    if args.diff:
        lines = read_lines(args.diff)
        added = [l for l in lines if l.startswith("+") and not l.startswith("+++")]
        removed = [l for l in lines if l.startswith("-") and not l.startswith("---")]
        if not added and not removed:
            print("! %s 里没有找到 diff 行（以 + / - 开头）。" % args.diff,
                  file=sys.stderr)
            print("  如果这是普通源码文件，请改用位置参数："
                  "ownership_check.py <路径>", file=sys.stderr)
            return 2
        code_added = sum(1 for l in added if l[1:].strip()
                         and not l[1:].strip().startswith(COMMENT_PREFIXES))
        results.append({
            "path": args.diff,
            "total": len(added) + len(removed),
            "code": code_added,
            "comment": 0,
            "blank": 0,
            "blocks": [],
            "longest": 0,
            "longest_name": "-",
            "smells": {},
        })
    else:
        if not args.path:
            parser.print_help()
            return 1
        if not os.path.exists(args.path):
            print("路径不存在：%s" % args.path, file=sys.stderr)
            return 2
        for full in iter_files(args.path, exts):
            rel = os.path.relpath(full, args.path) if os.path.isdir(args.path) else full
            info = analyze(full, rel)
            if info and info["code"] > 0:
                results.append(info)

    if not results:
        print("没有找到可分析的代码文件。")
        return 0

    total_code = sum(r["code"] for r in results)
    label, action = tier_for(total_code)

    if args.json:
        print(json.dumps({
            "files": len(results),
            "code_lines": total_code,
            "verdict": label,
            "action": action,
            "budget_per_chunk": args.budget,
            "detailed": results,
            "self_check": SELF_CHECK,
        }, ensure_ascii=False, indent=2))
    elif args.quiet:
        print("%d 个文件 / %d 行 -> %s：%s" % (len(results), total_code, label, action))
    else:
        print(report(results, args.budget, True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
