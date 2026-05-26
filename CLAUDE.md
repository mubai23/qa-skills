# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

`qa-skills` 是一个 Claude Code 插件，为 QA 测试工程师提供 5 个全流程 Skill，通过插件市场分发。安装后以 `/qa-skills:skill-name` 形式调用。

## 目录结构

```
./
├── .claude-plugin/
│   ├── plugin.json          # 插件元数据
│   └── marketplace.json     # 市场注册（GitHub 仓库指针）
├── skills/
│   ├── prd-analysis/        # 需求分析 → BR 编号清单
│   ├── case-design/         # 用例设计 → 关联 BR 编号
│   ├── case-review/         # 用例评审 → 以 BR 清单评审覆盖
│   ├── api-test/            # 接口测试（独立体系）
│   └── bug-report/          # 缺陷报告（独立使用）
├── README.md                # 用户安装与使用说明
└── CLAUDE.md                # 本项目 AI 协作指南
```

每个 Skill 目录内：`SKILL.md`（必需，核心指令文件）+ `examples/`（必需，至少一个参考范例）+ 可选的 `references/`（按需加载的标准文档）、`scripts/`（Python 辅助脚本，仅用户明确要求时运行）。

## Skill 架构模式

### SKILL.md 结构

所有 SKILL.md 遵循统一的五段式结构：

1. **YAML frontmatter** — `name` + `description`。`description` 是触发匹配的关键：决定了用户说什么话时会自动触发该 Skill，必须覆盖各种口语化表述
2. **角色定义 + 核心原则** — 声明"不要探索代码库"（基于文档设计用例，看代码反而会被有 bug 的实现误导）
3. **输入处理** — 先判断输入类型是否适配本 Skill，不适配的引导到正确的 Skill（如 case-design 遇接口文档 → 引导到 api-test）
4. **核心逻辑** — 分析方法、测试维度、输出模板（固定 Markdown 表格格式，确保不同对话输出一致）
5. **质量自检 + 完成提示** — checkbox 格式自检清单 + 引导下一步 Skill 的提示语

### 跨 Skill 核心约束

- **不探索代码库**：所有 Skill 基于文档/描述工作，不搜索项目文件、不查看数据库、不读代码。这是刻意设计——测试用例应验证"需求期望的行为"，而非"代码实际的行为"，对着有 bug 的实现写用例会导致漏测
- **优先级约定**：P0 = 阻断/核心主流程（case-design 要求 ≤20%）/ P1 = 重要分支 / P2 = 边缘场景 / P3 = 极端/探索性
- **可执行原则**：所有测试数据、建议、步骤必须是具体值/动作，不接受描述性文字（如"有效的手机号" → 必须写 "13812345678"）

### Skill 协作关系（BR 追溯链）

```
prd-analysis  ──→  case-design  ──→  case-review
（输出 BR-xxx）    （备注关联 BR）   （以 BR 清单做精确覆盖对比）
```

- `case-review` 无 BR 清单时启用"降级模式"（经验检查清单），不拒绝评审
- `case-design` 不处理接口用例，遇接口文档须引导用户使用 `api-test`

### Skill 互斥边界

| 输入类型 | 应触发 Skill | 不应触发 |
|---------|-------------|---------|
| PRD/用户故事/需求描述 | prd-analysis | — |
| 需求分析结果/BR 清单/功能描述 | case-design | api-test |
| 接口文档/Swagger/curl | api-test | case-design |
| 已有用例集 | case-review | — |
| 缺陷现象/报错日志 | bug-report | — |

## 修改 Skill 后的验证

修改 SKILL.md 或示例文件后，无需发布即可本地验证：

1. 重启 Claude Code 或 `/reload-plugins` 使修改生效
2. 用示例中的触发语句测试 Skill 是否正确触发
3. 检查输出格式是否与 examples/ 中的范例一致
4. 确认 Skill 间的互斥引导是否正确（如对 case-design 输入接口文档，应引导到 api-test）

验证通过后提交到 GitHub 仓库 `mubai23/qa-skills`，用户端执行 `/plugin marketplace update qa-skills` → `/plugin update qa-skills@qa-skills` → `/reload-plugins` 获取更新。

## references/ 按需加载约定

references/ 中的标准文档不应默认全部加载，只在 Skill 正文中按匹配条件加载：

| 文件 | 所属 Skill | 加载条件 |
|------|-----------|---------|
| `functional-testcases-standard.md` | case-design | 用户说"功能测试"或输入为业务需求 |
| `performance-testcases-standard.md` | case-design | 用户说"性能测试"或文档含 QPS/RT/并发 |
| `automation-testcases-standard.md` | case-design | 用户说"自动化候选" |
| `api-testcases-standard.md` | api-test | 接口测试场景 |

> `api-testcases-standard.md` 不在 case-design 中使用，这是刻意区分——功能用例和接口用例是两个独立体系。

## scripts/ 使用约定

- `case-design/scripts/export_to_excel.py` — 将 Markdown 用例表导出为 Excel（自动选列最多的表，P0-P3 优先级着色）
- `api-test/scripts/export_postman.py` — 将 Markdown 接口用例导出为 Postman Collection v2.1 JSON（自动识别维度作为 Folder、curl 示例作为 Request）

两个脚本的用法均为 `python <script> <markdown_file> [output_dir]`。仅在用户明确要求导出时运行，不主动提议或自动执行。
