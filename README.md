# charon-research-skills

面向实际科研任务的 AI agent skills。当前提供 **journal-submission-prep v0.3.2**，用于期刊投稿、转投和编辑部格式退修。

## 技能用途

给出目标期刊和已有 Word 稿件，让 agent 查要求、修改副本、整理材料，并逐项记录核验结果。

- 查找当前官方要求，区分文章类型和投稿阶段。
- 调整字体、字号、行距、段落间隔和标题等级，保存后回读核对。
- 检查旧期刊名称、旧投稿信和声明残留，整理本次需要的投稿材料。
- 结合文档渲染和逐页查看，交付修改稿、检查报告与待确认事项。

## 目录结构

```text
charon-research-skills/
├── README.md
├── LICENSE
└── skills/
    └── journal-submission-prep/
        ├── SKILL.md                  # agent 执行入口
        ├── scripts/                  # DOCX 修改、格式检查和环境自检
        ├── references/               # 要求检索、材料、事实与核验说明
        ├── LICENSE
        └── THIRD_PARTY_LICENSES.txt
```

安装只需完整的 `journal-submission-prep/` 文件夹。脚本和参考资料随技能一起使用，请保持目录结构。

## 安装教程

### 下载使用

1. 打开 [最新版本](https://github.com/CharonZheng/charon-research-skills/releases/latest)，下载附件中的独立 skill ZIP。
2. 解压，将整个 `journal-submission-prep` 文件夹放入所用 agent 的技能目录，按该工具的方式加载。
3. 在会话中输入“请使用 journal-submission-prep”，并提供期刊名称和稿件位置。

也可以选择仓库的 **Code → Download ZIP**，解压后取出 `skills/journal-submission-prep/`。有本地文件工具的 agent 可直接读取其中的 `SKILL.md`。

### 命令行安装

macOS/Linux 用户可在项目目录运行，随后选择对应 agent：

```bash
DO_NOT_TRACK=1 npx skills add CharonZheng/charon-research-skills --skill journal-submission-prep
```

此方式需要 Node.js 22.20+，并关闭安装工具遥测；下载 ZIP 无需 Node.js。

## 使用说明

**首次投稿**

```text
请使用 journal-submission-prep，将【稿件目录】中的论文准备投稿至【期刊全名】。
查询当前官方要求，调整正文和必要材料，保留原件，核验后另建目录交付。
```

**转投**

```text
请使用 journal-submission-prep，将【稿件目录】中的论文从【旧期刊】改投【新期刊】。
按新要求修改，检查旧刊残留，复用本稿已确认事实，保留原件。
```

**技术退修**

```text
请使用 journal-submission-prep，依据【编辑部邮件】修改【稿件目录】中的投稿材料。
逐条处理本轮意见，交付修改稿、修改说明和仍需确认的事项。
```

用户提供期刊、稿件和相关材料即可；规则、格式计划与详细检查记录由 agent 建立。

## 运行条件

- agent 具备本地文件、官网检索及文档渲染/查看能力。
- DOCX 辅助脚本：Python 3.10+、`lxml`。
- PDF 自动筛查：另需 `pdfplumber`。

从技能目录运行环境自检，`python` 替换为实际解释器：

```bash
python scripts/doctor.py --mode docx
```

安装技能与运行环境分别检查。伦理、资助等作者事实缺失时需确认；未完成的检查会明确列出。详细命令见 [命令说明](skills/journal-submission-prep/references/tooling.md)，交付状态见 [核验说明](skills/journal-submission-prep/references/readiness.md)。

## 来源与许可

原创代码采用 [MIT](LICENSE)。官方要求核验流程改编自 K-Dense 的 venue-templates，其他参考来源和贡献范围见 [来源说明](skills/journal-submission-prep/references/upstream.md)，保留 [第三方许可](skills/journal-submission-prep/THIRD_PARTY_LICENSES.txt)。

本仓库分发使用所需文件。合成测试与示例保留在 [v0.3.0 验证版本](https://github.com/CharonZheng/charon-research-skills/tree/journal-submission-prep-v0.3.0)；该版本的 101 项测试已在 Linux/Windows 六组 CI 中通过，见 [运行记录](https://github.com/CharonZheng/charon-research-skills/actions/runs/43045873033)。

## 致谢

感谢 K-Dense 的 [venue-templates](https://github.com/K-Dense-AI/scientific-agent-skills/tree/a25cf9ec00e2745d03f8704acf6f6919694ccd9a/skills/venue-templates)、[my-submission-formatting-agent](https://github.com/maxwell2732/my-submission-formatting-agent) 和 [manuscript-docx-cleaner](https://github.com/SEUWanglibo/manuscript-docx-cleaner) 为本项目提供的流程与设计参考，具体借鉴范围见[来源说明](skills/journal-submission-prep/references/upstream.md)，相关版权与许可声明已保留。同时，感谢玻尔科学空间对本项目的支持，欢迎科研用户共同参与试用、反馈与完善。
