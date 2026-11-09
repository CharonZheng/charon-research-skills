---
name: journal-submission-prep
description: Prepare existing research manuscripts for a named journal by finding current official requirements, adapting Word formatting, and assembling submission materials with evidence-backed checks. Use for initial submissions, reformatting for another journal, or editorial technical-check corrections including 投稿格式、转投、技术退修 and 投稿材料准备. Does not choose a journal or write research from scratch.
metadata:
  version: "0.2.1"
---

# 期刊投稿格式与材料准备

用户给出期刊名字即可开始检索；给出稿件后继续审计、修改和交付。默认中文沟通，保留稿件语言。搜索关键词只含期刊与政策，不包含未公开标题、作者、稿件 ID 或私人投稿链接。

开始实际处理前检查本次需要的文件访问、官网检索、Python 3.10+/lxml 和文档渲染能力；仅检索期刊要求时不因缺少 Word 工具而停止，使用 PDF 自动筛查时再检查 pdfplumber。优先使用当前环境已有工具，必要缺项集中说明其影响；技能安装成功不代表这些工具已具备。规则、事实和格式计划由 agent 建立，不要求用户手写 JSON。安装目录可能不同于源码仓库，辅助文件和命令始终以当前 SKILL.md 所在目录定位。

## 识别任务

- **首次投稿**：查目标刊及文章类型的首次投稿要求，确认是否允许 free-format。
- **转投**：比较新刊要求，检查旧刊名、旧 Cover letter、匿名信息、声明及附件残留。
- **技术退修**：将本轮邮件逐条建立任务，默认只改相关范围；版本与回复文件见 [材料准备](references/materials.md)。

文章类型和阶段能从材料明确判断时直接继续；无法判断且影响要求时提问，同时进行独立的文件清点。没有稿件时先交付要求表，明确稿件检查尚未执行。

## 1. 自行查找当前官方要求

按 [要求检索与冲突](references/requirements.md) 搜索期刊全名和 author guidelines，核对出版社、ISSN/期刊身份，打开官方作者指南、文章类型、相关声明/图像政策及必要模板。聚合站只用于发现链接。

每次实际处理都打开官网核验；旧 profile 只用于加速发现和比较。记录 URL、查看日期、相关文本证据、适用阶段及位置。网站阻止访问时尝试同刊其他官方入口、官方 PDF；仍不可得则索取指南文件，未核实项列为待确认。

在输出目录写 `requirements.json`，按 [规则与命令](references/tooling.md) 组织。官网没有规定的格式不升级为强制规则。历史邮件只在本稿本轮适用；冲突明确标记，不凭文件中先后顺序覆盖。

## 2. 审计稿件和附件

清点指定文件，记录哈希，在独立输出目录操作。以下脚本路径相对于本 skill 目录，执行时替换成实际绝对路径。需要 Python 3.10+ 和 lxml；优先使用环境自带/捆绑运行时，缺依赖先报告，不静默安装。

```bash
python scripts/submission.py audit INPUT.docx --out OUTPUT/audit.json
python scripts/submission.py check INPUT.docx --profile OUTPUT/requirements.json --out OUTPUT/check-before.json
```

审计给出段落索引、文本、样式/标题线索、字段、公式、图像及修订。标题、题注、数字引文结果是线索；方括号数字可能是统计值，需要复核。遇到未接受修订或无法识别的结构，不能将检查描述为完整。

按任务选读 [历史退修案例](references/editorial-cases.md)，检查主文、表格/图注、补充 PDF 与附件，关注图表合计上限、漏引、声明位置、版权和系统信息。历史阈值不作为默认 profile。

先读取本稿已有事实记录、全部指定材料和当前会话的作者答复，按 [事实与提问](references/facts.md) 合并为本稿本地 `manuscript-facts.json`。已确认且无新矛盾的事实复用；不跨稿复用伦理、资助、数据权限等声明。必要问题集中一次询问，附建议措辞，继续完成不依赖答复的工作；相同待答问题不重复发送。作者说“无需伦理”只确认该原话，不据此编造委员会豁免、编号或理由。

数字文献审计明确记录参考文献区间，在后续表格/图注前结束，不能把表格行首数值当参考文献。公式编号和图表首次引用顺序仍是候选线索，需核对遗漏、重复、正文与附件的编号映射。

## 3. 根据依据修改副本

先列出文件和具体修改。已授权的格式调整直接执行；伦理、同意、经费、冲突、贡献、版权缺少事实时询问，不自动填“无”“不适用”或签名。

机械格式操作建立 `format-plan.json`，引用已解决、适用、有证据的 rule ID：

```bash
python scripts/submission.py format INPUT.docx --profile OUTPUT/requirements.json --plan OUTPUT/format-plan.json --out OUTPUT/manuscript.docx --log OUTPUT/format-log.json --dry-run
python scripts/submission.py format INPUT.docx --profile OUTPUT/requirements.json --plan OUTPUT/format-plan.json --out OUTPUT/manuscript.docx --log OUTPUT/format-log.json
python scripts/submission.py verify INPUT.docx OUTPUT/manuscript.docx --out OUTPUT/integrity.json
```

脚本支持 [命令说明](references/tooling.md) 和 [基础格式质量门槛](references/formatting.md) 中的格式；默认拒绝表格内段落，只有逐段明确 `allow_table:true` 才可调整。支持现有正文、页眉页脚、脚注尾注文字部件；不改引文域或公式内容、不重建表格、不自动重写 styles.xml。拒绝已有输出及源文件覆盖。

**基础格式必须建立可核验目标，不能凭“看起来一致”完成。** 修改前由 agent 为标题、各级标题、正文、图注、表格、参考文献及页眉脚注等实际存在的角色建立格式表，写明字体（含中西文槽）、字号、倍数或固定行距、段前后间隔、标题级别；需要时加对齐、缩进、粗斜体和分页。每项区分官方要求、作者选择、保留原稿、编辑排版选择，禁止统一套用示例的 Times New Roman/12 pt/双倍行距。

每个交付 DOCX 建立 `format-contract.json`，覆盖所有含文本段落或逐项记录有理由的例外。每组必须有五类基础指标；不得从修改后的实际值直接反推目标以制造通过。格式日志保存修改前、计划修改后和保存后回读结果。样式继承、主题字体、局部覆盖、自动段距、网格或条件表格样式无法可靠确定时，结果保持未检查/待确认，继续处理或明确指出，不能判 pass。

章节移动、摘要重组、标题缩写、图表迁移、匿名化、引文换样式及材料生成，由 agent 使用可用 DOCX/PDF 工具定向修改，遵循 [编辑与验证](references/editing.md)。保留关系文件、嵌入对象、交叉引用与插件字段。复杂 DOCX 默认不经 Markdown 往返。不能将脚本不支持的操作假报完成，也不能仅交审计报告就结束已授权修改。

## 4. 组装投稿包并验证

按 [材料与一致性](references/materials.md) 准备实际需要的文件；各文件的标题、作者顺序、单位和声明从同一份确认事实生成。没有系统快照则系统实填为“未检查”。不自动登录、上传或提交期刊系统。

修改后重跑检查。`verify` 严格比较非格式内容和包成员，仅适合格式修改；有意改文、重排或匿名化会产生差异，需要记录具体授权与前后映射，另外核验，不能忽略失败。

最终 DOCX/PDF 需渲染并逐页检查，尤其标题分页、表格、公式、图注、字体和修订可见性。有 documents/pdf 技能时使用其捆绑渲染流程。缺渲染工具时明确视觉验证未完成。结构检查不能替代视觉验证。

```bash
python scripts/submission.py format-audit OUTPUT/manuscript.docx --contract OUTPUT/format-contract.json --out OUTPUT/format-check.json
python scripts/submission.py layout OUTPUT/render/manuscript.pdf --font-family "ACTUAL REQUIRED FONT" --out OUTPUT/layout-check.json
```

字体写入成功不证明渲染机有该字体。核查 PDF 实际字体和替代情况，指定字体缺失时不得悄悄改用另一字体并称通过。PDF 自动筛查仅提示越界、空白页及字体等候选问题；仍须逐页打开图像，特别复核公式裁切、文字重叠和表格分页。任一必需基础格式 fail、未覆盖段落、未解决基础格式问题或未完成渲染，都不得交付为“格式验证完成”；可明确交付待完善副本及问题清单。

对照同一份事实表核查正文、Cover letter、补充材料的标题、作者、资助、伦理和数据代码声明，记录冲突及处理依据。复用旧要求时，另用 `compare-profiles` 保存新旧规则及来源快照差异；每次仍须重新查看官网。

仅将交付文件放入单独 staging 目录，登记清单：

```bash
python scripts/submission.py manifest OUTPUT/staging --out OUTPUT/package-manifest.json
```

此命令只记录现有文件与哈希，不判断材料是否齐全或生成附件。私人事实笔记、旧稿、临时渲染文件不要混入投稿包。

交付实际文件、逐项检查表、修改记录及待补事实。结果分为 pass、fail、needs_confirmation、not_applicable、not_checked；不以总分宣称“可投稿”。

用户首先看到修改稿和本次实际需要的投稿材料链接，以及简短的修改与待办说明。提供可直接阅读的 `检查报告.md`，写清已改内容、检查结果和未解决问题；存在必要缺项时再单列待确认清单，不生成空白占位材料。详细 JSON、格式契约和机器日志放在检查记录目录，用户无需阅读它们才能理解结果。核心格式、渲染字体和视觉验证的结论分别列出。

## 复用来源

官方核验流程改编自 MIT 许可的 K-Dense venue-templates，见 [上游来源](references/upstream.md)。配套代码为本项目实现，不含许可不明项目代码。不内置声称现行有效的期刊数值大全。
