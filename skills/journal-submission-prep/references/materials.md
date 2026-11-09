# 投稿材料与一致性

按适用规则准备主稿、title page、匿名稿、单独图片、表格、合并补充 PDF、Cover letter、报告清单、版权凭证及 clean/marked-up。没有要求且未请求时不额外生成 graphical abstract/highlights。

每项记录文件名、用途、系统目标类型、依据及状态。PDF 合并后检查顺序、页码、字体和可读性；不能改后缀冒充转换。图片按最终宽度和原始像素计算有效 DPI；矢量容器可能含位图，改 DPI 标签或插值放大不是质量修复。

报告清单按研究设计和适用版本逐条定位，不为未实施方法填“已完成”。版权按图与元素收集来源、工具、许可和 proof，工具名称不等于出版授权。

## 事实和系统字段

在任务目录维护 manuscript-facts.json（已有 submission-facts.json 先读取并迁移，不丢弃作者确认）：标题、文章类型、摘要、关键词；作者稳定 ID、顺序、姓名、单位、通讯作者；必要 ORCID/联系字段；经费、贡献、冲突、伦理、同意、数据/代码、图像授权。按任务需要收集，不要求机械填满。来源、复用和集中提问见 [事实记录](facts.md)。

每个事实标 confirmed、missing、conflicting，附来源；只有 confirmed 可进入最终事实声明，不能将内部问号或占位符混入最终稿。

生成 portal-fields.md 供复制，核对正文、title page 和 Cover letter。没有实际系统状态时写“准备文本已核对，系统实填未检查”，不能假定上传抽取正确。

## 返修

按本轮要求准备版本与文件类型。marked-up 需有真实可见修改，不以文件名或格式日志冒充；clean 中的修订和批注按要求处理，不默认删除。

Cover letter、Response to reviewers 和 technical-check response 的职责以本轮指令为准。某历史邮件要求编辑回复放 Cover letter、Rebuttal 只放完整审稿意见和审稿回复，且不提交技术检查回复；不是通则。

在线投稿另需用户授权；本 skill 默认本地交付。作者事实、私人链接和原始编辑邮件不进入公开 skill。
