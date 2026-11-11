# 交付状态与证据

v0.3 将六类结果汇总为 ready / incomplete / blocked。命令只聚合证据，不替代官网检索、事实判断、渲染或逐页查看。每份交付 DOCX 分别运行；投稿包其余文件在 materials 复核中列出并核对。

## 环境自检

```bash
python scripts/doctor.py --mode docx
python scripts/submission.py doctor --mode render --font-family "Times New Roman" --out environment.json
```

doctor 入口只需要标准库，可在 Python 3.9 或缺少 lxml 时报告问题。requirements 模式不要求 DOCX 环境；docx 要求 Python 3.10+/lxml；pdf 另检查 pdfplumber；render 再探测 soffice/libreoffice、pdftoppm 和 Fontconfig。`--font-family` 可重复，示例字体不是期刊默认值。

ready 只代表所选模式的探测通过。软件路径存在不等于能转换，字体匹配不等于 PDF 字体正确。没有 CLI 时宿主可能另有 Word/文档渲染工具，agent 必须另行验证，不自动安装。

## delivery-review.json

下列是结构示例，SHA-256 均须由实际文件计算；由 agent 建立，用户不需要填写。证据路径相对于本 JSON 所在目录，也接受绝对路径。每个文件变更后应重新检查，再更新记录，不能只刷新哈希来沿用旧结论。

```json
{
  "schema_version": 1,
  "manuscript_sha256": "actual-final-docx-sha256",
  "checks": {
    "integrity": {"path": "integrity.json", "sha256": "actual-report-sha256"},
    "formatting": {"path": "format-check.json", "sha256": "actual-report-sha256"},
    "policy": {"status": "not_checked", "note": "查当前官网及适用规则后记录"},
    "visual": {"status": "not_checked", "note": "渲染并逐页查看后记录"},
    "materials": {"status": "not_checked", "note": "核对需要的材料与声明后记录"}
  }
}
```

缺失的 rendered_fonts 自动显示未检查，其余必需类别也不能靠省略来通过。

### 机器报告

- integrity 引用 `verify` 输出，核对 `after_sha256` 为最终 DOCX；passed=false 阻断。
- formatting 引用 `format-audit` 输出，核对 `input_sha256` 为最终 DOCX；属性确实不符则阻断，只有未知属性或覆盖缺项则保持 incomplete。有 exemptions 时，必须实际复核并在引用对象补 `"exemptions_reviewed": true`，说明留在复核记录中；例外不能掩盖实际失败。
- rendered_fonts 引用 `layout` CLI 输出，核对 `input_sha256` 为当前 PDF，必须指定过期望字体。任何候选问题保持待确认，不以 automated_triage_clear 的单独值掩盖 findings。
- 旧版 layout 报告没有文件哈希或期望字体列表，须重新运行，不手工补上假装已检查。

先实际转换 DOCX，再登记 PDF 来源：

```json
{
  "rendered_pdf": {
    "path": "render/manuscript.pdf",
    "sha256": "actual-pdf-sha256",
    "source_sha256": "actual-final-docx-sha256",
    "renderer": "实际工具名称、版本和本次转换记录位置"
  }
}
```

此对象加入顶层；checks 增加 `"rendered_fonts": {"path":"layout-check.json", "sha256":"actual-report-sha256"}`。来源关联由执行者如实记录；汇总脚本不能独立证明 PDF 是由这个 DOCX 转换而来。

### 人工/agent 复核记录

policy / visual / materials 支持 pass、fail、needs_confirmation、not_checked。materials 确实不适用时可用 not_applicable，其余五类不能取消。pass 与 not_applicable 都需要非空 note、reviewer、checked_on（ISO 日期）和 evidence（至少一个实际文件引用及哈希）。

policy 的证据应包括本轮要求表及必要来源快照，说明文章类型、阶段、冲突处理和仍适用的要求；materials 的证据应列出本次实际需要的文件、哈希及跨文件核对结果。只有已检查项才能在复核记录写通过；不能用一个空白清单当证据。

视觉复核需逐页打开图像；完成后才记录，例如两页 PDF：

```json
{
  "status": "pass",
  "reviewer": "实际复核者或执行 agent 标识",
  "checked_on": "2026-11-11",
  "note": "逐页核对标题分页、表格、公式、题注及字形；本次发现的问题已修正并重新渲染。",
  "reviewed_pages": [1, 2],
  "evidence": [
    {"page": 1, "path": "render/page-1.png", "sha256": "actual-image-sha256"},
    {"page": 2, "path": "render/page-2.png", "sha256": "actual-image-sha256"}
  ]
}
```

必须与绑定的 PDF 页数逐页对应，不得漏页或重复。汇总命令验证记录和文件没有变化，不会自行看图，也不会识别不真实的复核陈述。

### 授权内容编辑的完整性复核

章节重排、匿名化等会使严格 `verify` 失败；不能删改机器失败记录来冒充纯格式通过。integrity 改用 `method: authorized_edit_review`，按人工记录填写 status/note/reviewer/checked_on/evidence，并额外提供：

- `source_docx`：原稿文件引用（path/sha256）。
- `authorized_changes`：非空字符串列表，逐项指向已授权改动的范围、前后映射和依据。
- evidence 指向实际差异与复核记录，覆盖未授权内容、数字、公式、引用和对象的保留情况。

此方式是明确披露的人工复核，不会自动证明内容正确；汇总输出保留该 method。不要为了绕过真实损坏而使用。

## 命令与退出码

```bash
python scripts/submission.py readiness manuscript.docx --review delivery-review.json --out delivery-status.json --report 检查报告.md
```

0=ready；1=blocked（存在 fail）；2=输入无效、稿件哈希不匹配或输出已存在；3=incomplete（缺项、待确认、未检查或证据变化）。报告拒绝覆盖，重跑使用新文件名或新目录。

`check` 从 v0.3 起也在强制规则未检查/待确认时返回 3，新增 required_checks_status。原先依赖其“无 fail 就返回 0”的调用需要更新。`format`、`verify`、`format-audit`、`layout` 的独立结果仍不能替代最终交付汇总。
