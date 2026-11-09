# charon-research-skills

把实际科研工作中的重复流程整理成可复用的 AI agent skills。Reusable AI agent skills for everyday research workflows.

[中文](#中文) · [English](#english)

## 中文

### 安装

在需要使用技能的项目目录中运行以下命令，按提示选择你的 agent。需要 Node.js 22.20+；`DO_NOT_TRACK=1` 关闭安装工具的遥测。命令示例适用于 macOS/Linux 终端。

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills --skill journal-submission-prep
```

默认安装到当前项目。私有仓库需要访问权限及已配置的 Git/GitHub 登录。安装工具及选项见 [skills CLI](https://github.com/vercel-labs/skills#readme)。

**不使用命令行**：选择 **Code → Download ZIP**，解压，将 `skills/journal-submission-prep` 整个文件夹提供给 agent，让它读取其中的 `SKILL.md`。此方式无需 Node.js。

### 技能目录

| 技能 | 适用场景 |
|---|---|
| [journal-submission-prep · v0.2.1](skills/journal-submission-prep/SKILL.md) | 首次投稿、改投其他期刊、编辑部格式退修 |

提供期刊名称和稿件位置即可开始。agent 会查官方要求、检查环境、调整副本并核验结果；规则和 JSON 由 agent 处理。

### 直接这样说

**首次投稿**

```text
请使用 journal-submission-prep，将【稿件目录】中的论文准备投稿至【期刊全名】。
查询当前官方要求，调整正文和必要材料，核验基础格式，保留原件，另建目录交付。
```

**改投期刊**

```text
请使用 journal-submission-prep，将【稿件目录】中的论文从【旧期刊】改投【新期刊】。
按新要求修改，检查旧期刊名称和旧格式残留，复用本稿已确认事实，保留原件。
```

**技术退修**

```text
请使用 journal-submission-prep，依据【编辑部邮件】修改【稿件目录】中的投稿材料。
逐条处理本轮格式意见，核验后交付修改稿、修改说明和仍需确认的事项。
```

### 会得到什么

- 修改后的稿件，以及本次实际需要的投稿信、补充材料或其他附件。
- 可直接阅读的检查报告，说明修改内容、核验结果及待确认事项。
- 独立保存的原件与修改副本；详细日志放在检查记录中，无需用户阅读 JSON。

字体、字号、行距、段前后间隔和标题等级会按目标核对，并在保存后回读；最终文档还须渲染逐页检查。无法可靠核验的项目不会判为通过。

### 使用条件与边界

agent 需要本地文件、官网检索及文档渲染/查看能力。辅助脚本需要 Python 3.10+ 和 `lxml`，PDF 自动筛查另需 `pdfplumber`。首次使用可让 agent 检查现有环境并集中说明缺项；安装技能不等于安装了上述工具。伦理、资助等作者事实缺失时仍需确认；不会自动提交期刊系统。

此仓库仅分发使用所需文件。保留 [第三方许可](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt)，复用范围见 [来源说明](skills/journal-submission-prep/references/upstream.md)；原创代码尚未指定仓库级开源许可。

## English

### Install

Run this from your research project and follow the prompts to choose your agent. Requires Node.js 22.20+; `DO_NOT_TRACK=1` disables installer telemetry. This command uses macOS/Linux shell syntax.

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills --skill journal-submission-prep
```

Installation is project-local by default. Private repositories require access and configured Git/GitHub authentication. See [skills CLI](https://github.com/vercel-labs/skills#readme) for installer options.

**Without the command line**: select **Code → Download ZIP**, extract it, and give the complete `skills/journal-submission-prep` folder to your agent. Ask it to read `SKILL.md`. This method does not require Node.js.

### Skill catalog

| Skill | Use cases |
|---|---|
| [journal-submission-prep · v0.2.1](skills/journal-submission-prep/SKILL.md) | Initial submissions, journal transfers, and editorial technical revisions |

Start with a journal name and manuscript location. The agent checks official requirements and available tools, edits copies, and verifies results. It prepares the rules and JSON for you.

### Example requests

**Initial submission**

```text
Use journal-submission-prep to prepare the paper in [manuscript directory] for [full journal name].
Find current official requirements, adapt the manuscript and required materials, verify basic
formatting, preserve the originals, and deliver revised files in a separate directory.
```

**Journal transfer**

```text
Use journal-submission-prep to transfer the paper in [directory] from [old journal] to [new journal].
Apply the new requirements, check for old journal names and formatting, reuse confirmed facts
for this manuscript, and preserve the originals.
```

**Technical revision**

```text
Use journal-submission-prep to revise the files in [directory] according to [editorial email].
Address each formatting request and deliver verified revised files, a change summary,
and any remaining questions.
```

### What you receive

- A revised manuscript and the cover letter, supplementary files, or other materials actually required.
- A readable check report covering changes, verification results, and unresolved items.
- Preserved originals and separate revised copies. Detailed logs stay in the check records; you do not need to read JSON.

Fonts, sizes, line and paragraph spacing, and heading levels are checked against explicit targets and read back after saving. Final documents also require rendering and page-by-page inspection. Unresolved checks are not marked as passed.

### Requirements and limits

The agent needs local file access, official-source research, and document rendering/viewing tools. Helpers require Python 3.10+ and `lxml`; automated PDF checks also need `pdfplumber`. Ask the agent to check the environment and identify missing tools. Installing the skill does not install these dependencies. Missing author facts, including ethics or funding declarations, still require confirmation. The skill does not submit to journal systems. Supporting skill documentation is primarily in Chinese.

This repository distributes only files needed to use the skill. The [third-party license](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt) is retained; see [attribution](skills/journal-submission-prep/references/upstream.md). A repository-level open-source license for the original code has not yet been selected.
