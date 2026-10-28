Required Notice: Copyright 2026 luzern0414 (https://github.com/luzern0414/Luz-Writing)

# Luz Writing · 来源与许可说明

本说明补充 `references/13-sources-and-licenses.md`，记录合并来源、公开调研的使用边界和再分发前需要核对的材料。这里不替任何上游项目授予其许可证之外的权限。

## 原始 Luz 材料

本 Skill 的科技资讯与营销流程由用户提供的 `D:\Codes\Writing\copywriting` 合并而来。原先保留的 HTML 模板、正文示例与文章构建脚本属于 Luz 项目资产；公开再分发这些资产前，应由项目所有者确认其来源和授权条件。

## 公开写作 Skill 的融合方式

2026-10-26，调研检索了 Agent/Claude/Codex 写作技能，初选并下载 17 个代表性仓库，扫描 300 余份 `SKILL.md`，精读其中 28 份与写作直接相关的规则。最终包只保留对通用写作流程有用的独立重述，没有安装上游仓库，也没有复制完整 Skill、代码或素材。

同日第二轮检索英文 humanizer / anti-slop 与中文去 AI 味类技能，新增约 50 个候选仓库，精读其中 34 个并列入来源表；规则只做独立重述，落在 `references/15-deliver-only-what-was-asked.md` 与 `references/17-ai-pattern-catalog.md`。其中 ilien-dev/quiron（AGPL-3.0）、badmuriss/unslop（CC BY-SA 4.0）、swaylq/humanize-chinese（非标准非商业条款）、fy-agent/humanize-chinese-writing（自定义版权）以及未见许可证的仓库，只用于阅读和重述通用方法，没有复制文本或代码。

来源、固定提交号和规则映射见：

- `references/13-sources-and-licenses.md`

## 本机视觉工具

写作 Skill 可选择调用两个本机工作区：

- `D:\Codes\Imagegen`：图片生成与参考图编辑。
- `D:\Codes\Luz-Design`：海报、视觉系统、页面设计与排版验收。

这两个目录没有被复制进本 Skill，也不在本说明中重新授权。它们继续受各自仓库的许可证、服务条款和素材权利约束。本 Skill 只保存调用方法、输入约束和回退规则，不包含 Imagegen 密钥。调用方不得读取、打印或复制 `Imagegen\docs\apikey.txt`。

## 许可分层

- **MIT / Apache-2.0 来源**：用于阅读、比较和融合通用写作方法。若未来直接复制其代码、模板或大段文字，必须随附对应许可证要求的版权与许可声明。
- **CC BY-NC 4.0 来源（tizzy916/humanities-writing-companion）**：只提供人文学术批评方法的高层参考；任何受该来源保护内容的商业使用都受非商业条件限制。
- **许可未在调研快照中确认的来源（jzOcb/writing-style-skill、realrossmanngroup/no_ai_slop_writing_rules，以及 jamditis/claude-skills-journalism 的统一顶层许可）**：只用于阅读和独立重述通用方法，未复制完整文本、脚本或素材。公开再分发或商业使用前应回到对应仓库重新核对许可。
- **anthropics/skills**：仓库内不同 Skill 可能各自附有许可文件；本包未直接复制其技能正文或脚本。
- 三个未确认许可的项目和 CC BY-NC 项目若未来被直接引用或复制，应重新审查来源、适用许可证和署名方式。

## 事实与效果边界

上游项目对写作质量、检测器表现、行业框架或平台规则的陈述属于经验性材料。本 Skill 将它们作为编辑启发，不把它们当作已验证的普遍事实。事实核验、署名和引用要求由实际写作任务中的证据与发表渠道决定。

## 免责声明

本说明记录合并与调研时的许可快照，不构成法律意见。正式商业发行、修改许可证或重新打包第三方资产前，应核对各来源的最新许可证文本。
