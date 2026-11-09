# charon-research-skills

面向实际科研工作的 AI agent skills。 / Practical AI agent skills for research workflows.

[中文](#中文) · [English](#english)

## 中文

### 可用技能

**[journal-submission-prep · v0.2](skills/journal-submission-prep/SKILL.md)**：检索目标期刊当前官方要求，调整已有论文格式，准备投稿材料。保留原件，核对字体、字号、行距、段距及标题等级，并复用本稿已确认事实。

### 下载与使用

1. 在仓库页面选择 **Code → Download ZIP**，解压。
2. 将 `skills/journal-submission-prep` 整个文件夹放入支持本地技能的 agent 环境，保留全部内容。
3. 在解压目录中向 agent 提出任务，例如：

```text
请读取 skills/journal-submission-prep/SKILL.md 并使用这个技能。
将【稿件路径】中的论文转投【期刊全名】，查询当前官方要求，
调整正文及必要投稿材料，核对基础格式并渲染逐页检查。
保留原件，另建目录交付。
```

agent 需要能读取和修改本地文件、访问期刊官网，并渲染和查看文档。辅助脚本需要 Python 3.10+ 和 `lxml`；PDF 自动筛查另需 `pdfplumber`。可直接让 agent 检查环境并说明缺项，无需手动填写规则或 JSON。

仓库仅包含使用所需的技能文件与本说明；测试及开发资料不随下载包提供。无法可靠核验的格式保持待确认，伦理等作者事实不能编造；技能不自动提交期刊系统，也不保证接收。

### 来源与许可

保留了 [第三方许可](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt)，复用范围见 [来源说明](skills/journal-submission-prep/references/upstream.md)。原创代码尚未指定仓库级开源许可。

## English

### Available skill

**[journal-submission-prep · v0.2](skills/journal-submission-prep/SKILL.md)** finds current official journal requirements, adapts existing manuscripts, and prepares submission materials. It preserves originals, checks fonts, sizes, line and paragraph spacing, and heading levels, and reuses confirmed facts for the same manuscript.

### Download and use

1. Select **Code → Download ZIP** on the repository page and extract it.
2. Place the complete `skills/journal-submission-prep` folder in an agent environment that supports local skills. Keep all its contents together.
3. From the extracted directory, ask the agent:

```text
Read skills/journal-submission-prep/SKILL.md and use this skill.
Prepare the manuscript at [path] for transfer to [full journal name].
Find the current official requirements, adapt the manuscript and required materials,
verify basic formatting, render the documents, and inspect every page.
Preserve the originals and deliver revised files in a separate directory.
```

The agent needs local file access, journal website access, and document rendering and viewing tools. Helper scripts require Python 3.10+ and `lxml`; automated PDF checks additionally require `pdfplumber`. Ask the agent to check the environment and identify missing tools. You do not need to write rules or JSON manually. Supporting skill documentation is primarily in Chinese.

This repository contains only the skill files and this guide. Tests and development materials are excluded from the download. Unresolved formatting checks remain pending; author facts such as ethics declarations are never fabricated. The skill does not submit to journal systems or guarantee acceptance.

### Attribution and licensing

The [third-party license](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt) is retained; see [attribution](skills/journal-submission-prep/references/upstream.md) for its scope. A repository-level open-source license for the original code has not yet been selected.
