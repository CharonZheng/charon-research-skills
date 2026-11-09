# 本稿事实复用与集中提问

事实记录仅在用户本稿工作目录保存，不放入投稿包、可分发 skill 或全局记忆。由 agent 阅读所有指定材料和当前作者答复后生成 observations；脚本负责确定性合并，不声称自动理解所有伦理或法律事实。新稿件分配新的稳定 manuscript_id；同稿转投沿用该 ID，文件哈希另记，不能把哈希当跨版本身份。

```json
{
  "manuscript_id": "synthetic-study-001",
  "sources": [{"id":"U1", "kind":"author_confirmation",
    "locator":"Current author reply 1", "evidence":"The sponsor had no involvement."}],
  "facts": [{"key":"funding_role", "value":"No sponsor involvement",
    "status":"confirmed", "source_ids":["U1"], "required":true},
    {"key":"ethics_basis", "status":"missing", "required":true, "blocking":true,
     "question":"Please provide the factual basis for ethics not being required.",
     "proposed_text":"Draft wording will be prepared once the basis is established."}]
}
```

```bash
python scripts/submission.py facts --observations observations.json --out manuscript-facts.json --questions questions.json
python scripts/submission.py facts --observations observations-next.json --existing manuscript-facts.json --out manuscript-facts-next.json --questions questions-next.json
python scripts/submission.py compare-profiles requirements-old.json requirements-new.json --out requirements-diff.json
```

source kind 为 document、author_confirmation、system_snapshot，需 locator 和 evidence；来源 ID 不可改变含义。事实 status 为 observed、confirmed、missing、conflicting、not_applicable。confirmed/not_applicable 必须引用作者确认来源；不能将文中出现的声明升级为作者已经确认。required 是本次必须确认的事实，不是所有字段统一设 true；blocking 只阻塞依赖该事实的最终声明，不阻止其他格式工作。

相同确认值复用，普通缺失观察不抹去已有确认；矛盾值保留 alternatives，未解决时不能选其中一项。作者明确更正后用新的确认来源和 `supersedes:true` 更新，保留旧值历史。required 的 observed/missing/conflicting 进入提问队列；可选缺项留在报告，不打断用户。new_questions 集中展示一次，pending_questions 仍保持未答；相同问题不重复发出不等于已获答复。脚本生成队列时记录已安排询问的指纹，agent 应在同一轮实际展示新问题。

尽量问“以下两句是否准确”而非让用户从头写英文；但不能以默认选项或沉默代替事实。对含糊答复精确限定确认范围，例如“确认”不能自动解释为同时确认问题中互不相关的所有条件，“无需伦理”不等于“伦理委员会正式豁免”。同一组问题收齐后直接继续，不对已经明确答复的资助方角色反复追问。

compare-profiles 按 rule ID 比较增删改，同时报告来源快照变化。改投后 ID 发生变化时需 agent 做语义对照；脚本不自动证明两个措辞等价，也不把旧要求当作现行政策。
