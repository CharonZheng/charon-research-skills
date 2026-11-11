# journal-submission-prep

期刊投稿格式与材料准备：查要求、改格式、整理材料并核验结果。
Journal submission preparation: verify requirements, adapt formatting, and assemble materials.

[中文](#中文) · [English](#english) · [技能集合 / Skill collection](https://github.com/CharonZheng/charon-research-skills)

## 中文

### 安装

在需要使用技能的项目目录中运行以下命令，按提示选择你的 agent。需要 Node.js 22.20+；`DO_NOT_TRACK=1` 关闭安装工具的遥测。命令示例适用于 macOS/Linux 终端。

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills --skill journal-submission-prep
```

默认安装到当前项目。安装工具及选项见 [skills CLI](https://github.com/vercel-labs/skills#readme)。

**不使用命令行**：选择 **Code → Download ZIP**，解压，将 `skills/journal-submission-prep` 整个文件夹提供给 agent，让它读取其中的 `SKILL.md`。此方式无需 Node.js。

### 适用场景

当前版本：v0.3.0。用于首次投稿、改投其他期刊和编辑部格式退修。agent 执行入口为 [SKILL.md](SKILL.md)。

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

v0.3 新增可直接运行的环境自检，以及绑定稿件和证据哈希的统一交付报告。六类检查缺项、待确认或未检查时，状态保持 incomplete。官网解释、材料与视觉检查仍需 agent 实际执行；ready 不保证期刊接收。

```bash
python scripts/doctor.py --mode docx
```

以上命令从本技能目录运行，`python` 替换为实际可用的解释器；doctor 在缺少 DOCX 依赖时也能输出诊断。高级命令与退出码见 [环境与交付状态](references/readiness.md)。普通使用者只需向 agent 描述任务，无需填写 JSON。

### 使用条件与边界

agent 需要本地文件、官网检索及文档渲染/查看能力。辅助脚本需要 Python 3.10+ 和 `lxml`，PDF 自动筛查另需 `pdfplumber`。首次使用可让 agent 检查现有环境并集中说明缺项；安装技能不等于安装了上述工具。伦理、资助等作者事实缺失时仍需确认；不会自动提交期刊系统。

本技能目录仅分发使用所需文件。[公开仓库](https://github.com/CharonZheng/charon-research-skills) 的 `examples/` 和 `tests/` 独立于安装目录。原创代码使用 [MIT](LICENSE)，保留 [第三方许可](THIRD_PARTY_LICENSES.txt)，复用范围见 [来源说明](references/upstream.md)。

## English

### Install

Run this from your research project and follow the prompts to choose your agent. Requires Node.js 22.20+; `DO_NOT_TRACK=1` disables installer telemetry. This command uses macOS/Linux shell syntax.

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills --skill journal-submission-prep
```

Installation is project-local by default. See [skills CLI](https://github.com/vercel-labs/skills#readme) for installer options.

**Without the command line**: select **Code → Download ZIP**, extract it, and give the complete `skills/journal-submission-prep` folder to your agent. Ask it to read `SKILL.md`. This method does not require Node.js.

### Use cases

Current version: v0.3.0. For initial submissions, journal transfers, and editorial technical revisions. The agent entry point is [SKILL.md](SKILL.md).

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

v0.3 adds offline environment diagnostics and a unified delivery report bound to manuscript and evidence hashes. Missing or unresolved checks remain incomplete. Official-source interpretation, materials review, and page inspection still require real agent/reviewer work; ready does not guarantee journal acceptance. See [diagnostics and delivery status](references/readiness.md). Users do not need to prepare JSON themselves.

### Requirements and limits

The agent needs local file access, official-source research, and document rendering/viewing tools. Helpers require Python 3.10+ and `lxml`; automated PDF checks also need `pdfplumber`. Ask the agent to check the environment and identify missing tools. Installing the skill does not install these dependencies. Missing author facts, including ethics or funding declarations, still require confirmation. The skill does not submit to journal systems. Supporting skill documentation is primarily in Chinese.

This skill directory contains runtime files only. Public synthetic examples and tests are kept separately in the repository. Original code is [MIT-licensed](LICENSE). The [third-party license](THIRD_PARTY_LICENSES.txt) is retained; see [attribution](references/upstream.md).
