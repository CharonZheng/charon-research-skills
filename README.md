# charon-research-skills

将科研实践中可复用的方法与工具整理为 AI agent skills，持续积累、独立使用。
A growing collection of reusable AI agent skills for research workflows.

[中文](#中文) · [English](#english)

## 中文

### 关于这个仓库

这里收集面向实际科研任务的技能。每个技能独立维护自己的用途、操作流程和必要工具，按需要安装和使用。当前可用技能见下表，后续新增技能也会统一收录于此。

### 技能目录

| 技能 | 用途 | 使用说明 |
|---|---|---|
| journal-submission-prep | 期刊投稿准备、改投及格式退修 | [查看说明](skills/journal-submission-prep/README.md) |

点击对应技能的使用说明，可查看适用场景、调用示例、依赖和交付内容。

### 安装技能

在需要使用技能的项目目录中运行，然后按提示选择技能和 agent：

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills
```

此安装方式需要 Node.js 22.20+，默认安装到当前项目。示例使用 macOS/Linux 终端语法，并关闭安装工具遥测。更多选项见 [skills CLI](https://github.com/vercel-labs/skills#readme)。

也可以选择 **Code → Download ZIP**，解压后，将 `skills/` 下所需技能的整个文件夹提供给 agent，让它读取该文件夹中的 `SKILL.md`。ZIP 下载方式无需 Node.js。

安装技能后，按该技能的使用说明提出任务。各技能的运行依赖由 agent 检查；安装技能本身不等于安装了所有外部工具。

### 目录组织

每个技能位于 `skills/<skill-name>/`：

- `README.md`：给使用者看的说明。
- `SKILL.md`：给 agent 读取的执行入口。
- 其他必要脚本、参考资料与第三方许可随技能保存，按需使用。

技能目录只包含使用所需内容；`tests/`、`examples/` 和 CI 在仓库中独立保存，便于公开复现。选择性安装单个 skill 时无需这些开发文件。私人研究材料不进入仓库。

原创代码使用 [MIT 许可](LICENSE)。各技能的复用来源与第三方许可见其目录。验证方法见 [测试与合成示例](examples/README.md)。

## English

### About this collection

This repository collects skills for practical research tasks. Each skill maintains its own scope, workflow, and required tools, and can be installed independently. Available skills are listed below; future additions will use the same catalog.

### Skill catalog

| Skill | Purpose | User guide |
|---|---|---|
| journal-submission-prep | Journal submissions, transfers, and formatting revisions | [Read the guide](skills/journal-submission-prep/README.md) |

Each guide describes the skill's use cases, example requests, dependencies, and outputs.

### Install skills

Run this from your project directory, then follow the prompts to choose skills and your agent:

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills
```

Requires Node.js 22.20+ and installs to the current project by default. The example uses macOS/Linux shell syntax and disables installer telemetry. See [skills CLI](https://github.com/vercel-labs/skills#readme) for additional options.

Alternatively, choose **Code → Download ZIP**, extract it, and give the complete folder of your chosen skill under `skills/` to your agent. Ask it to read that folder's `SKILL.md`. The ZIP method does not require Node.js.

After installation, follow the selected skill's guide to describe your task. The agent checks runtime requirements; installing a skill does not install every external tool it may need.

### Repository layout

Each skill lives in `skills/<skill-name>/`:

- `README.md`: instructions for users.
- `SKILL.md`: the execution entry point for agents.
- Required scripts, references, and third-party licenses are kept with the skill and used as needed.

Skill directories contain runtime files only. Public `tests/`, `examples/`, and CI are kept separately for reproducibility and are not required for selective skill installation. Private research materials are excluded.

Original code is [MIT-licensed](LICENSE); attribution and third-party licenses remain in each skill directory. See [tests and synthetic examples](examples/README.md).
