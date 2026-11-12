# 规则结构与命令

脚本离线运行，无网络请求。需要 Python 3.10+、lxml。`python` 应替换为当前环境可用的满足版本要求的解释器。`audit/check` 只读输入，`format` 创建新副本，已有输出拒绝覆盖。`--dry-run` 验证完整计划并打印，不写文件。JSON 为 UTF-8。

## requirements.json

以下是合成示例，不是任何真实期刊政策。使用时替换为本次实际核验的来源、日期和规则。

```json
{
  "journal": "Synthetic Journal for Testing",
  "article_type": "Research Article",
  "stage": "initial",
  "checked_on": "2026-11-09",
  "sources": [{
    "id": "S1", "kind": "user",
    "locator": "Synthetic fixture specification",
    "checked_on": "2026-11-09",
    "evidence": "For this test only, use double spacing and a 200-word abstract."
  }],
  "rules": [{
    "id": "R1", "description": "Test abstract word limit",
    "mandatory": true, "applicability": "applicable", "source_ids": ["S1"],
    "check": {"type": "word_limit", "section": "Abstract", "max": 200}
  }, {
    "id": "R2", "description": "Test double spacing",
    "mandatory": true, "applicability": "applicable", "source_ids": ["S1"],
    "check": {"type": "manual", "instruction": "Verify double spacing in applicable paragraphs"}
  }]
}
```

stage=initial/revision/accepted。source kind=official/editor_current/historical/user；locator 为官网 URL 或可定位本地文件/邮件；evidence 写足以支持该规则的文本或准确摘要。source.checked_on 是实际查看日期，source_date 可为 null。

applicability=applicable/not_applicable/unknown，后两者需要 applicability_reason。冲突可增加 conflict_group、resolution=unresolved/resolved、resolution_note。同一冲突组有未解决规则时，所有组内规则都保持待确认；脚本会拒绝用它们自动改格式。只有历史来源的规则也保持待确认。

支持的 check：

| type | 字段 | 自动检查范围 |
|---|---|---|
| required_section / forbidden_section | section | 检查非表格样式标题；无样式独立段落与名称一致时待确认，忽略大小写、数字序号和末尾冒号；正文句中提及不视为标题 |
| section_order | sections 字符串列表 | 每个指定标题仅出现一次时核对顺序 |
| max_heading_level | max 整数 | 识别标题的层级上限 |
| max_heading_characters | max；可选 within_section | 含空格及编号；within_section 只计其子标题 |
| word_limit | section、max；可选 count_mode=whitespace | 从指定标题至下一个同级/更高标题；含范围内表格/子节；不支持中文汉字计数 |
| display_limit | max | 唯一主图/表题注候选合计，始终待确认；不把多面板或补充文件当成已验证 |
| manual | 可选 instruction | 事实、版面、文件、引用插件、版权等，结果为未检查 |

审计的 numeric_reference_candidates 是方括号数字引用与编号参考文献的线索，可能漏掉上标、作者年份、图注/补充材料，也可能把统计值当引文。不能直接自动补引、删文献或声称文献核查完成。

## format-plan.json

```json
{
  "input_sha256": "replace-with-actual-audit-sha256",
  "operations": [{
    "kind": "paragraph_format", "rule_id": "R2",
    "paragraph": 3, "expected_text": "Exact paragraph text from audit",
    "format": {"font_name": "Times New Roman", "font_size_pt": 12,
               "line_spacing": 2, "space_before_pt": 0, "space_after_pt": 0,
               "first_line_indent_mm": 0, "alignment": "both",
               "page_break_before": false}
  }]
}
```

仅写需要修改的属性，别把示例当默认期刊样式。paragraph 是 audit 的零起始索引（包含表格段落），expected_text 必须精确相同；表格段落默认拒绝，逐段明确 allow_table=true 才允许。rule_id 需要适用、有证据且无冲突，agent 还须核对该规则确实支持相应操作，脚本不理解证据语义。part 省略为 word/document.xml；指定其他现有正文故事部件时使用该部件独立索引。

另一操作：`{"kind":"page_margins","rule_id":"R3","section":0,"margins_mm":{"top":25.4,"bottom":25.4,"left":25.4,"right":25.4}}`。需先有对应 R3，section 零起始，省略的边不改。

允许字号 1–200 pt（半点步长）、行距 0.5–5 倍或 1–200 pt、段前后 0–200 pt、首行缩进 0–100 mm 或 0–20 字符、页边距 1–100 mm；alignment=left/center/right/both。均只是输入合理性限制，不是期刊建议。更多字体槽、标题级别、现有样式及局部例外见 [基础格式](formatting.md)。负悬挂、匿名化、结构重排需 agent 定向处理。

字体操作改含 w:t 的文本 run，不动 OMML。只调整直接格式，不更新 styles.xml；存在修订的稿件需要先明确希望保留的视图。

## CLI 与退出码

```bash
python scripts/doctor.py --mode docx
python scripts/submission.py doctor --mode render --font-family "Arial" --out environment.json
python scripts/submission.py audit INPUT.docx --out audit.json
python scripts/submission.py check INPUT.docx --profile requirements.json --out check.json
python scripts/submission.py format INPUT.docx --profile requirements.json --plan format-plan.json --out manuscript.docx --log format-log.json --dry-run
python scripts/submission.py format INPUT.docx --profile requirements.json --plan format-plan.json --out manuscript.docx --log format-log.json
python scripts/submission.py verify INPUT.docx manuscript.docx --out integrity.json
python scripts/submission.py manifest STAGING_DIRECTORY --out package-manifest.json
python scripts/submission.py format-audit INPUT.docx --contract format-contract.json --out format-check.json
python scripts/submission.py layout INPUT.pdf --font-family "Arial" --out layout-check.json
python scripts/submission.py facts --observations observations.json --out manuscript-facts.json --questions questions.json
python scripts/submission.py compare-profiles requirements-old.json requirements-new.json --out requirements-diff.json
python scripts/submission.py readiness INPUT.docx --review delivery-review.json --out delivery-status.json --report 检查报告.md
```

0=该命令范围内完成；1=check 的强制 fail、verify 失败、format-audit 未全通过或 layout 有候选问题；2=无效输入/拒绝操作；3=check 的强制规则仍待确认/未检查、doctor 能力未确认或 readiness 未完成。check 新增 required_checks_status=pass/fail/incomplete；非强制问题仍须看逐项结果。facts 的 0 只表示队列生成成功，不代表声明已确认。错误摘要写 stderr。manifest 输出须在 staging 之外，拒绝链接；它不生成压缩包、检查隐私或材料齐全性。报告也拒绝覆盖：重跑请用新目录或新的报告名。

doctor 不依赖 lxml 即可诊断当前解释器。readiness 的六类状态、证据结构与自动/人工边界见 [交付状态](readiness.md)。layout CLI 输出包含 PDF input_sha256 和 expected_font_families，用于绑定本次结果；仍不证明所有字形或视觉合格。

`format-log` 记录输入哈希、操作、source IDs、before/predicted_after、保存后 readback 和结构比较结果。回读不通过拒绝发布，但只证明计划中的属性，不代表全稿已覆盖。视觉状态始终 not_checked，agent 渲染后另在最终报告登记结果，不能让脚本冒称已看页面。事实复用和问题队列详见 [事实记录](facts.md)；基础格式完整覆盖详见 [格式契约](formatting.md)。
