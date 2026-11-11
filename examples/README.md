# 可复现的合成投稿示例

本例仅测试软件，不对应真实期刊政策，也不含真实论文或作者资料。需要 Python 3.10+、lxml 和 python-docx；PDF 自动筛查另需 pdfplumber。

从仓库根目录运行，输出目录必须尚不存在：

```bash
python examples/synthetic_submission.py /tmp/submission-demo
```

生成 source.docx、formatted.docx、规则/计划/格式契约、修改日志、完整性结果和 `检查报告.md`。包含可编辑表格、OMML 公式、合成引用字段和页眉。引用字段用于检查字节保留，不代表真实 Zotero 库或插件刷新兼容。

示例字体默认 Times New Roman，可加 `--font-family "其他实际目标字体"`；这是测试参数，不是通用期刊默认值。字体属性检查通过不等于本机已安装该字体。

预期：格式契约与纯格式完整性检查通过；最终状态 **incomplete**，因为没有核验真实期刊、实际渲染或逐页复核，也没有准备真实投稿包。示例进程返回 0 表示该预期成立，其内部 readiness 命令返回 3。

如需继续验证版面，先用可用的 Word/LibreOffice/宿主工具实际转换最终 DOCX，再运行：

```bash
python skills/journal-submission-prep/scripts/submission.py layout /tmp/submission-demo/render/formatted.pdf --font-family "Times New Roman" --out /tmp/submission-demo/layout-check.json
```

开发目录布局中的路径是 `journal-submission-prep/scripts/submission.py`。转换路径按实际环境填写；PDF 生成后仍须逐页看图。按技能目录的 `references/readiness.md` 更新 delivery-review 及其证据，再使用新的报告文件名运行 readiness。

## 运行全部测试

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

测试和本例放在 skill 目录之外，选择性安装 skill 时不需要下载其输出或私人材料。CI 执行相同测试，真实渲染与 Word/Zotero/EndNote 插件兼容性仍需相应环境验证。
