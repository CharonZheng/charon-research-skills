# 基础格式质量门槛

目标是有依据的设置、保存后独立回读、全稿覆盖和逐页渲染共同验证。不能承诺任何 Word/操作系统都绝对零差异；未知属性、缺字体、异常版面必须显式暴露。

## 格式契约

先根据官方要求及原稿识别角色，定目标后再修改。每个交付 DOCX 的最终哈希写入契约；不是复制回读结果当目标。下面仅为合成测试，不是默认期刊要求。

```json
{
  "input_sha256":"actual-final-docx-sha256",
  "groups":[{
    "id":"body", "role":"body",
    "basis":{"kind":"user", "source":"Synthetic test instructions"},
    "expected":{"font_name":"Arial", "font_size_pt":12,
      "line_spacing":2, "space_before_pt":0, "space_after_pt":6,
      "heading_level":0},
    "targets":[{"part":"word/document.xml", "paragraph":3,
      "expected_text":"Exact text from audit",
      "run_exemptions":[{"run":2,"properties":["font_size_pt"],
        "reason":"Preserve a verified superscript reference size; visually checked separately"}]}]
  }],
  "exemptions":[]
}
```

basis.kind 为 official/user/preserved/editorial_choice，source 写本轮可定位依据。每组必须含字体、字号、行距、段前后和标题等级。paragraph 索引包含表格段落，各 XML part 分别从 0 计数；expected_text 精确匹配，哈希/文字变化则重新建立映射。

所有含文本的正文、页眉页脚、脚注尾注都需被组覆盖。确需例外的段落在 exemptions 中逐项指定 part、paragraph、expected_text 和 reason，并在最终报告列出另外核验方式；禁止整章“复杂所以跳过”。空段落、纯 OMML 公式、图形内文字、编号标记不在文字 run 覆盖保证内，必须视觉/对象检查；不能把契约 passed 等同于全部版面通过。

## 支持的格式与单位

| 属性 | 含义与限制 |
|---|---|
| font_name | 设置四个文字字体槽；混合文字优先明确各槽 |
| font_ascii / font_hansi / font_east_asia / font_cs | 英文 ASCII、其他拉丁、东亚、复杂文字字体槽；检查需覆盖实际用到的槽 |
| font_size_pt / font_size_cs_pt | pt；设置前者同时设 sz/szCs，后者可单独覆盖复杂文字；只支持 0.5 pt 步长 |
| line_spacing | 倍数，2 表示双倍；不是 24 pt；自动关闭该段网格吸附，除非明确指定 |
| line_spacing_pt + line_rule | pt，必须同时指定 exact 或 atLeast；不能与倍数混用 |
| space_before_pt / space_after_pt | pt；显式关闭自动段距、同样式段距抑制；继承的行数段距不能可靠覆盖时拒绝通过 |
| heading_level | 0 正文，1–9 大纲级别；只加粗放大不算标题层级 |
| style_id | 只能选现有段落样式，不自动新建；标题应同时映射正确样式和大纲级别 |
| first_line_indent_mm / first_line_indent_chars | 毫米或字符二选一；不含负悬挂缩进 |
| alignment | left / center / right / both |
| bold / italic | 显式布尔；默认不改，保护统计符号与学名等局部斜体 |
| page_break_before / contextual_spacing / snap_to_grid | 显式布尔；涉及实际分页仍需渲染 |

格式计划使用上述属性。表格必须逐段明确 `allow_table:true`，part 可为已有 word/document.xml、headerN.xml、footerN.xml、footnotes.xml、endnotes.xml。只改变段落和文字属性；不改变表格网格、行高、单元格、图片、字段、公式和 styles.xml。公式字体保持 OMML，不能全局改成普通文字字体。

上标/下标、符号、局部字号例外通过 run_exemptions 指定，并在契约沿用。run 为该段 `.//w:r` 的原始索引（含字段 run），审计报告中每个可见 run 有 index，不能猜。例外只豁免列出的属性，不豁免文字完整性。

## 三道验证

1. `format --dry-run`：按原文/哈希定位，展示 before/predicted_after 与来源。实际写入时再次回读，目标属性非 pass 就拒绝发布该副本。它只证明计划中的操作成功，不能替代全稿契约。
2. `format-audit`：解析文档默认、样式继承、字符样式、直接覆盖、可解析主题字体和文字字体槽；核对契约及漏检段落。条件表格样式、修订、缺失样式、文本框、编号标记等保守保持待确认。未解析行数段距/主题字体不得判通过。
3. 渲染并逐页打开 PNG，检查标题级别/分页、字形、公式、表格、题注和空白。`layout` 需要 pdfplumber，报告字体、文本越界/替换字符/空白页候选。指定字体缺失时保持待确认，不自动将替代字体视为合格。自动筛查无异常依然不证明每页无重叠或裁切。

缺少所需字体时使用可用的合规渲染环境；未经作者允许不修改字体目标。保留来源哈希；不通过复制替代字体到名称栏来消除报警。最终报告分开列：规则适用性、结构完整性、基础格式契约、渲染字体与逐页视觉检查。

## OOXML 依据

实现与边界参考 Microsoft 官方文档：[字体槽](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.runfonts?view=openxml-3.0.1)、[字体与主题覆盖规则](https://learn.microsoft.com/mt-mt/openspecs/office_standards/ms-oi29500/aef3c9a6-5d6c-434b-90b7-85e761fd8e62)、[同样式段距](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.contextualspacing?view=openxml-3.0.1)、[网格吸附](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.snaptogrid?view=openxml-3.0.1)、[自动段前距](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.spacingbetweenlines.beforeautospacing?view=openxml-3.0.1)。这些解释文件结构，不代表任何期刊的格式政策。
