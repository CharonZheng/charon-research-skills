# charon-research

面向实际科研工作的 AI agent skills。让重复工作更省力，让修改过程可核查。

Practical AI agent skills for research workflows, with changes you can review and verify.

[中文](#中文) · [English](#english)

## 中文

### 关于这个仓库

`charon-research` 收集和维护可复用的科研技能。每个技能围绕具体任务组织操作说明、辅助脚本和参考资料，由具备相应工具能力的 AI agent 执行。

目前从论文投稿准备开始，后续将逐步扩展其他科研工作场景。尚未实现的技能不会列为已有功能。

### 现有技能

| 技能 | 版本 | 用途 |
|---|---|---|
| [journal-submission-prep](skills/journal-submission-prep/SKILL.md) | 0.2 | 检索目标期刊当前官方要求，调整已有稿件格式，准备投稿材料并核验结果 |

### journal-submission-prep 能做什么

- **核验要求**：根据期刊名称、文章类型和投稿阶段查找官方指南，记录来源和查看日期，区分现行规则与历史个案。
- **调整格式**：支持首次投稿、改投和编辑部技术退修；检查旧期刊名称、旧投稿信及其他格式残留。
- **检查基础排版**：核对字体、字号、行距、段前后间隔和标题等级，按正文、标题、图注、表格和参考文献等角色设置目标。
- **保存后回读**：检查实际生效的 Word 属性，报告漏检段落；结合字体核查和逐页渲染检查版面。
- **准备材料**：按要求整理投稿信、补充材料和声明，对照本稿事实记录检查文件间的一致性。
- **减少重复提问**：复用本稿已有且无矛盾的作者确认，集中询问必要缺项；不跨稿复用伦理、资助等声明。
- **保留原件**：在独立目录输出修改副本、修改记录和检查报告。

### 如何使用

将整个技能目录提供给支持读取本地技能的 agent，保留其中的 `SKILL.md`、`scripts/` 和 `references/`。在当前源码目录中，可以直接要求 agent 读取入口文件：

```text
请读取 skills/journal-submission-prep/SKILL.md 并使用这个技能。
目标期刊为【期刊全名】，这是【首次投稿／转投／技术退修】。
原稿和已有材料位于【本地路径】。

请查询当前官方要求，调整稿件和必要投稿材料，检查旧期刊名称及旧格式残留。
逐项核对字体、字号、行距、段前后间隔和标题等级，保存后回读并渲染逐页检查。
复用本稿已确认事实，保留原件，另建目录交付修改稿、材料和检查报告。
```

只提供期刊名称时，可以先检索要求；执行稿件修改还需要原稿和相应材料。规则表、事实记录和格式计划由 agent 建立，不要求用户手动填写 JSON。

### 环境与辅助命令

| 部分 | 所需环境 |
|---|---|
| 官方要求检索 | agent 可用的联网检索与网页读取工具 |
| 核心 DOCX 辅助脚本及行为测试 | Python 3.10+、`lxml` |
| PDF 自动筛查 | 另需 `pdfplumber` |
| 真实 Word 合成测试文件生成 | 另需 `python-docx` |
| 版面验证 | 可用的 DOCX 转 PDF／页面图像工具，以及查看全部页面的能力 |

辅助脚本离线运行；联网检索、语义修改和视觉复核由 agent 配合相应工具完成。仓库不捆绑渲染器，也不静默安装依赖。

从仓库根目录运行只读审计或查看命令：

```bash
python3 skills/journal-submission-prep/scripts/submission.py --help
python3 skills/journal-submission-prep/scripts/submission.py audit INPUT.docx --out audit.json
```

输出文件必须尚不存在。`audit` 不会自动完成格式修改；更多命令及输入结构见 [命令说明](skills/journal-submission-prep/references/tooling.md)、[基础格式核验](skills/journal-submission-prep/references/formatting.md) 和 [事实复用](skills/journal-submission-prep/references/facts.md)。

### 验证与能力边界

v0.2 开发验证记录包括 70 项合成行为测试，以及真实合成 DOCX 的修改、回读和渲染检查。字体替代测试确认：Word 中写入字体名称，并不等于渲染时使用了该字体。上述结果不代表所有稿件或所有平台均已验证。

从仓库根目录运行行为测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

格式属性、结构完整性、渲染字体和逐页视觉检查分别记录。无法可靠检查的项目保留为待确认或未检查，不能用结构检查替代版面检查。伦理、知情同意、作者贡献和版权等事实需要可靠材料或作者确认，不自动编造；技能不自动登录或提交期刊系统，也不保证期刊接收。

### 源码组织与发布范围

每个技能独立存放于 `skills/` 下，测试位于 `tests/`。后续新增技能沿用这一组织方式。

```text
charon-research/
├── README.md
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── skills/
│   └── journal-submission-prep/
│       ├── SKILL.md
│       ├── agents/
│       ├── scripts/
│       ├── references/
│       └── THIRD_PARTY_LICENSES.txt
└── tests/
```

私人论文、原始投稿邮件、作者事实记录、真实投稿输出和缓存不属于公开源码。扩展技能时优先提供独立入口、明确依赖和适用范围，以及可公开复现的合成测试。

### 来源与许可

官方来源核验流程改编自 MIT 许可的 K-Dense `venue-templates`。详见 [来源说明](skills/journal-submission-prep/references/upstream.md) 和 [第三方许可](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt)。本项目原创代码的仓库级许可尚未指定，公开发布时应补充；第三方许可不自动覆盖全部原创代码。

## English

### About

`charon-research` collects reusable skills for research work. Each skill combines task instructions, helper scripts, and references for an AI agent with the necessary tools.

The collection currently starts with manuscript submission preparation. Additional research workflows will be added over time; planned skills are not presented as existing capabilities.

### Available skills

| Skill | Version | Purpose |
|---|---|---|
| [journal-submission-prep](skills/journal-submission-prep/SKILL.md) | 0.2 | Find current official journal requirements, adapt existing manuscripts, prepare submission materials, and verify the results |

### What journal-submission-prep does

- **Verifies requirements** using official sources for the journal, article type, and submission stage, with source locations and access dates.
- **Adapts manuscripts** for initial submissions, transfers, and editorial technical corrections, including checks for previous journal names and outdated submission materials.
- **Checks basic formatting** such as fonts, font sizes, line spacing, paragraph spacing, and heading levels, with separate targets for body text, headings, captions, tables, and references.
- **Reads saved formatting back** to check effective Word properties and uncovered paragraphs, alongside font checks and page-by-page rendering review.
- **Prepares materials** such as cover letters, supplementary files, and declarations, checking consistency against the manuscript's fact record.
- **Reduces repeated questions** by reusing consistent author confirmations for the same manuscript and batching necessary questions. Ethics and funding declarations are not reused across manuscripts.
- **Preserves originals** and places revised copies, change logs, and check reports in a separate output directory.

### Usage

Provide the complete skill directory to an agent that can read local skills. Keep `SKILL.md`, `scripts/`, and `references/` together. From the current source directory, ask the agent to read the entry point:

```text
Read skills/journal-submission-prep/SKILL.md and use this skill.
The target journal is [full journal name]. This is an [initial submission / transfer / technical revision].
The manuscript and existing materials are located at [local path].

Find the current official requirements, adapt the manuscript and required submission materials,
and check for previous journal names and outdated formatting.
Verify fonts, font sizes, line spacing, paragraph spacing, and heading levels.
Read formatting back after saving, render the documents, and inspect every page.
Reuse confirmed facts for this manuscript, preserve the originals, and deliver revised files,
submission materials, and check reports in a new directory.
```

A journal name is enough to start requirements research. Manuscript editing also requires the source files and relevant materials. The agent prepares rule profiles, fact records, and formatting plans; users do not need to write JSON manually.

### Requirements and helper commands

| Component | Requirements |
|---|---|
| Official requirements research | Web search and page-reading tools available to the agent |
| Core DOCX helpers and behavioral tests | Python 3.10+ and `lxml` |
| Automated PDF triage | Additionally, `pdfplumber` |
| Synthetic Word document generation | Additionally, `python-docx` |
| Layout validation | DOCX-to-PDF/page-image tools and the ability to inspect every page |

Helper scripts run offline. The agent uses appropriate tools for web research, semantic editing, and visual review. The repository does not bundle a renderer or silently install dependencies.

Run a read-only audit or view available commands from the repository root:

```bash
python3 skills/journal-submission-prep/scripts/submission.py --help
python3 skills/journal-submission-prep/scripts/submission.py audit INPUT.docx --out audit.json
```

Output files must not already exist. `audit` does not perform manuscript reformatting. See [commands and schemas](skills/journal-submission-prep/references/tooling.md), [format verification](skills/journal-submission-prep/references/formatting.md), and [fact reuse](skills/journal-submission-prep/references/facts.md) for details. Supporting skill documentation is currently primarily in Chinese.

### Validation and limits

The v0.2 development record includes 70 synthetic behavioral tests and editing, readback, and rendering checks on a real synthetic DOCX. A font-substitution test confirmed that a font name stored in Word does not establish which font the renderer uses. These results do not establish compatibility with every manuscript or platform.

Run behavioral tests from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Formatting properties, structural integrity, rendered fonts, and visual review are reported separately. Unresolved checks remain pending or unchecked; structural checks do not replace page inspection. Ethics, consent, authorship, and copyright facts require reliable evidence or author confirmation and are never fabricated. The skill does not automatically log in to or submit through journal systems, and it does not guarantee acceptance.

### Source layout and publication scope

Each skill lives in its own directory under `skills/`, with tests in `tests/`. Additional skills will follow the same layout.

```text
charon-research/
├── README.md
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── skills/
│   └── journal-submission-prep/
│       ├── SKILL.md
│       ├── agents/
│       ├── scripts/
│       ├── references/
│       └── THIRD_PARTY_LICENSES.txt
└── tests/
```

Private manuscripts, original submission emails, author fact records, actual submission outputs, and caches are outside the public source scope. New skills should have an independent entry point, explicit requirements and scope, and reproducible tests using publishable synthetic data.

### Attribution and licensing

The official-source verification workflow is adapted from K-Dense's MIT-licensed `venue-templates`. See [attribution](skills/journal-submission-prep/references/upstream.md) and [third-party license](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt). A repository-level license for the original code has not yet been selected and should be added for public release; the third-party license does not automatically license all original code.
