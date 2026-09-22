# AI Dev Principles Skill

> 能力内化，知识外置；AI 增强，人在环中。
>
> 可以把执行外包给 AI，但不要把思考外包给 AI。

面向 AI 时代开发者的一套协作契约。它要求 AI 提供知识、示例、骨架、反例和验证建议，同时把业务理解、方案设计、关键判断、复杂实现与最终责任留给开发者本人。

## 核心理念

- **知识开卷**：API、框架配置、库用法、SQL、命令、文档和 Demo 可以随时查询或直接使用。
- **思考闭卷**：问题分析、业务拆解、方案设计、关键判断、复杂逻辑和结果验证必须由人掌握。
- **AI 给骨架，人完成实现**：默认先对齐业务，再提供知识与伪代码骨架，不直接生成整个功能。
- **复制不是问题，不理解才是问题**：已经理解的样板代码可以直接复用；没有理解的代码不能进入项目。
- **训练追求能力，生产追求效率**：学习时主动降低 AI 代劳程度，生产时充分利用 AI 提效，但保留判断权。
- **控制审核带宽**：AI 输出必须保持在人可以真正读完、审完和验证的范围内。

## 适用场景

当用户进行以下任务时，本 skill 会约束 AI 的协作方式：

- 编写、修改、重构或调试代码
- 设计方案、技术选型或评估 trade-off
- 解释代码、框架或底层原理
- Review AI 生成的代码或方案
- 讨论人与 AI 的开发分工
- 明确要求“按我的开发原则来”

## 默认协作流程

### 1. 业务对齐

先确认以下内容，未对齐前不输出实现代码：

- 业务目的
- 正常流程
- 业务规则与状态约束
- 输入与输出
- 异常、并发、超时、重复请求等边界条件

### 2. 知识供给

AI 提供本次任务所需的知识，包括：

- 涉及的 API、库或框架模块
- 调用方式、参数和返回值
- 最小 Demo 与推荐写法
- 常见陷阱、版本差异和性能问题
- 可继续查证的官方文档或源码入口

### 3. 伪代码骨架

将业务语言转换为程序逻辑骨架，并标注：

- `[复杂]`：需要人研究并实现的逻辑
- `[风险]`：容易出现 Bug、并发或边界问题的位置
- `[决策]`：存在多个方案，需要人做 trade-off 的位置
- `[可复制]`：理解后可直接复用的标准调用

AI 给出骨架后应停下来，等待用户检查、修改并确认，不能自动展开成完整实现。

### 4. 实现与验证

用户确认骨架后，再进入实现：

- 简单、已理解的样板代码可以直接复制和调整。
- 并发、状态、异常、算法、核心业务逻辑等复杂部分由用户完成。
- AI 提供参考、Review、Debug 协助和风险清单。
- 每个小块都要给出测试方法、验证步骤和排查入口。

## 输出预算

| 代码规模 | 处理方式 |
| --- | --- |
| ≤ 50 行 | 可以直接交付 |
| 51–150 行 | 声明需要逐行阅读，并给出阅读顺序 |
| 151–300 行 | 必须先拆分，一次只交付一块 |
| > 300 行 | 不直接交付，改为任务拆解清单和第一块实现 |

这里的行数只是审核带宽的参考，不代表代码质量。即使代码少于 50 行，只要用户无法解释，也必须先补齐理解。

## 学习模式与生产模式

| 维度 | 学习模式 | 生产模式 |
| --- | --- | --- |
| 目标 | 让能力进入大脑 | 效率、质量和交付结果 |
| AI 的产出 | 提示、引导、反例、检查项 | Demo、实现、工具和现成方案 |
| 是否给完整答案 | 默认不给 | 可以给 |
| 谁做关键判断 | 人 | 人 |
| 谁负责验证 | 人 | 人 |
| 速度要求 | 允许慢 | 优先快 |

模式不明确时，AI 应先区分：这次是在培养能力，还是在使用能力。

## 常用方式

安装或加载 skill 后，可以直接使用以下表达：

```text
按我的开发原则来，先别写代码。先帮我确认业务目的、流程、规则、输入输出和边界。
```

```text
这次是学习模式。先不要给完整答案，让我先说思路，你再检查漏洞和边界。
```

```text
这次是生产模式。请直接给 API 用法和实现骨架，但方案判断和核心逻辑由我决定。
```

```text
先给我框架和 API 知识：怎么调用、参数、返回值、推荐写法、Demo 和常见坑。
```

```text
先给伪代码骨架，标出 [复杂] [风险] [决策] [可复制]，不要直接展开实现。
```

```text
Review 这段代码，重点检查业务理解、设计取舍、边界风险、验证方式和认知所有权。
```

完整提示词可参考 [`assets/prompt-cards.md`](assets/prompt-cards.md)。

## 安装

本目录本身就是一个完整 skill。将目录复制到 Kilo 的用户 skill 目录：

```text
~/.agents/skills/ai-dev-principles/
```

Windows PowerShell 示例：

```powershell
New-Item -ItemType Directory `
  -Path (Join-Path $HOME ".agents\skills") `
  -Force | Out-Null

Copy-Item -LiteralPath ".\ai-dev-principles" `
  -Destination (Join-Path $HOME ".agents\skills") `
  -Recurse -Force
```

安装后重新启动或刷新 Kilo，使新 skill 被加载。

## 辅助脚本

两个脚本都只使用 Python 标准库，不需要安装第三方依赖。

### 判断学习模式或生产模式

```powershell
python .\scripts\mode_router.py --text "这次我想搞懂 JWT 登录的原理"
```

输出 JSON：

```powershell
python .\scripts\mode_router.py --text "这个 Bug 很急，今天要修复" --json
```

查询输出预算：

```powershell
python .\scripts\mode_router.py --budget-lines 120
```

查看判定信号：

```powershell
python .\scripts\mode_router.py --list-signals
```

`mode_router.py` 使用关键词启发式判定，结果适合作为协作起点，不应替代人的最终判断。

### 检查认知所有权与审核带宽

检查文件或目录：

```powershell
python .\scripts\ownership_check.py .\src
```

指定单块代码行数和扩展名：

```powershell
python .\scripts\ownership_check.py .\src --budget 50 --ext .py,.ts
```

检查 Diff：

```powershell
python .\scripts\ownership_check.py --diff .\change.patch
```

输出 JSON：

```powershell
python .\scripts\ownership_check.py .\src --json
```

脚本会统计代码规模、识别较长函数并提示部分代码异味，但无法判断人是否真正理解代码。报告末尾的自检问题仍需要由人认真回答。

## 交付前自检

每次交付前至少确认：

- 我能说明需求解决的业务问题和不做它的后果。
- 我理解正常流程、业务规则和关键边界。
- 我知道为什么选择当前方案，以及至少一个未采用方案的原因。
- 我逐行看过代码，理解每处 API 调用的目的和参数。
- `[复杂]` 部分由我实现，或经过我研究后接受。
- 我知道如何测试、验证和排查问题。
- 单次代码量处于我的审核带宽内。
- 我能向别人解释这段代码，并愿意对结果负责。

完整清单见 [`assets/review-checklist.md`](assets/review-checklist.md)。

## 项目级复用

可以将 [`assets/agent-rules-snippet.md`](assets/agent-rules-snippet.md) 中的规则粘贴到项目的 `AGENTS.md`、`.cursorrules`、`CLAUDE.md` 或其他 AI 规则文件中，使项目内的 AI 协作遵循同一套契约。

## 目录结构

```text
ai-dev-principles/
├── SKILL.md
├── README.md
├── assets/
│   ├── agent-rules-snippet.md
│   ├── prompt-cards.md
│   └── review-checklist.md
├── references/
│   ├── anti-patterns.md
│   ├── boundary-table.md
│   ├── collaboration-protocol.md
│   └── principles-full.md
└── scripts/
    ├── mode_router.py
    └── ownership_check.py
```

## 文件说明

- [`SKILL.md`](SKILL.md)：skill 的机器可识别入口和核心执行约束。
- [`references/principles-full.md`](references/principles-full.md)：原则原文，是最高优先级依据；与其他文件冲突时以此为准。
- [`references/collaboration-protocol.md`](references/collaboration-protocol.md)：四步协作协议的细粒度规程和话术。
- [`references/boundary-table.md`](references/boundary-table.md)：AI 与人的能力边界，以及学习/生产模式差异。
- [`references/anti-patterns.md`](references/anti-patterns.md)：认知依赖反模式和纠偏方式。
- [`assets/prompt-cards.md`](assets/prompt-cards.md)：可直接复制的提示词卡片。
- [`assets/review-checklist.md`](assets/review-checklist.md)：交付前认知所有权自检清单。
- [`assets/agent-rules-snippet.md`](assets/agent-rules-snippet.md)：可粘贴到项目规则文件中的精简契约。
- [`scripts/mode_router.py`](scripts/mode_router.py)：学习/生产模式与输出预算辅助判定脚本。
- [`scripts/ownership_check.py`](scripts/ownership_check.py)：代码规模、审核带宽与代码异味辅助检查脚本。

## 最终目标

本 skill 不追求“完全不使用 AI”，也不接受“离开 AI 就无法判断”。

它追求的是：

> 没有 AI 时，知道问题应该如何分析；使用 AI 时，能够更快获得知识、完成执行，同时保持独立判断、持续成长和最终责任。
