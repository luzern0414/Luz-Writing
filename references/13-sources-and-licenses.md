# 13 · 来源与许可

## 合并来源

本 skill 的核心科技资讯与营销流程来自用户提供的 `D:\Codes\Writing\copywriting`。原有平台、文风、找料、交付规则经过重排和补强，原文相关资产被保留为模板、示例和打包脚本。

2026-10-26 完成了公开 Agent Skill 搜索与下载。初选 17 个仓库，下载全部 `SKILL.md`、README 与许可证，发现 300 余份技能文件；逐份筛选后精读 28 份与写作直接相关的规则。下列来源用于“方法对照与规则融合”，没有把上游整包直接安装：

| 来源 | 版本 | 许可快照 | 吸收的规则 |
| --- | --- | --- | --- |
| https://github.com/blader/humanizer | 8c307f3 | MIT | AI 模式分类、弱证据与误报边界、声音保留 |
| https://github.com/conorbronsdon/avoid-ai-writing | 209815c | MIT | 保声改写、事实保护、检测器限制 |
| https://github.com/MrGeDiao/shuorenhua | e33d5eb | MIT | 最小编辑、命题保真、审稿范围 |
| https://github.com/coreyhaines31/marketingskills | e85f3cb | MIT | 写作诊断、三道门槛、内容策略、营销编辑 |
| https://github.com/jamditis/claude-skills-journalism | f0fea78 | 顶层许可在稀疏快照中未确认 | SIFT、事实核查、编辑工作流；仅重述通用方法并署名 |
| https://github.com/tizzy916/humanities-writing-companion | e097ff6 | CC BY-NC 4.0 | 四层批评、来源状态、作者控制；使用时保留非商业限制 |
| https://github.com/jzOcb/writing-style-skill | d94826e | 快照未见许可证 | 风格维度与样本学习的高层思路；未复制原文 |
| https://github.com/haowjy/creative-writing-skills | a7b0ac1 | Apache-2.0 | 读者回报、视角边界、场景与省略 |
| https://github.com/zenstory-ai/oh-story-claudecode | c3fbbbe | MIT | 长短篇流程、故事层去 AI、连续性审查 |
| https://github.com/Master-cai/Research-Paper-Writing-Skills | 77e7c2c | MIT | 反向提纲、claim-evidence、评审者视角 |
| https://github.com/zLanqing/codex-claude-academic-skills | 7ed6377 | MIT | 中文科研写作、术语与证据边界 |
| https://github.com/qiyuxi24/writing-essay-skills | 3566ae9 | MIT | 观点文、科普、故事真实性与隐私边界 |
| https://github.com/vstorm-co/content-skills | 5138a11 | MIT | 内容审计、渠道复用与品牌一致性 |
| https://github.com/forjd/better-writing | 8e45d0b | MIT | 轻编辑原则、语境优先、声音测量 |
| https://github.com/coleschaffer/copywritingskills-rmbc | 8327d49 | MIT | Research/Mechanism/Brief/Copy 战略顺序与具体性 |
| https://github.com/realrossmanngroup/no_ai_slop_writing_rules | 35e32ae | 快照未见许可证 | 用可核事实替换强度词的高层原则；未复制原文 |
| https://github.com/anthropics/skills | dbd4588 | 随技能提供许可证；总仓库快照未见统一顶层许可 | 渐进披露、协作写作、读者测试、技能结构 |

## 2026-10-26 第二轮：去 AI 味与输出纪律

第二轮定向检索了英文 humanizer / anti-slop / unslop / deslop 类技能和中文去 AI 味、降 AI 率、说人话类技能，并参考维基百科 *Signs of AI writing* 页面（2026-10-26 访问）。blader/humanizer 与 MrGeDiao/shuorenhua 提交号未变。吸收内容落在 `15-deliver-only-what-was-asked.md` 与 `17-ai-pattern-catalog.md`，全部为独立重述，没有复制完整文本、词表文件、脚本或素材。上游给出的频率统计和模型对比未经本包复核，只作为经验阈值。

| 来源 | 版本 | 许可快照 | 吸收的规则 |
| --- | --- | --- | --- |
| https://github.com/hardikpandya/stop-slop | 8da1f03 | MIT | 英文填充短语与结构模式 |
| https://github.com/Nanako0129/sepia | fb06be7 | MIT | 改后不变长、编辑比例、审稿只报不改 |
| https://github.com/theclaymethod/unslop | 17ed39c | 仅 SKILL.md 头部声明 MIT，无 LICENSE 文件 | 无问题原样返回、未命中句逐字保留 |
| https://github.com/mshumer/unslop | edcb623 | MIT | 博客模板结构 |
| https://github.com/stephenturner/skill-deslop | a906154 | MIT | 去除模板化写法 |
| https://github.com/Aboudjem/humanizer-skill | a58df06 | MIT | 预设反驳、问句小标题、推理与引用标记泄漏 |
| https://github.com/ninehills/skills | f3e82a7 | 快照未见许可证 | 只输出改写文本，不附改动清单 |
| https://github.com/adnanakil/nobuzz | a6bfbb1 | MIT | 无前言无评论的输出、流行空话 |
| https://github.com/eric-tramel/slop-guard | 7ef2113 | MIT | 段落等长与短语复用 |
| https://github.com/MohamedAbdallah-14/unslop | 3ea65db | MIT | 不补新事实、文风不改立场 |
| https://github.com/asavvin-pixel/unslop | 5e6bac5 | MIT | 首句连读测试、空泛两端、夸大来源、半分力句子 |
| https://github.com/ilien-dev/quiron | d807289 | AGPL-3.0 | 更新的英文高频词、担保真诚副词、矫枉过正与一轮清理；仅高层重述 |
| https://github.com/gabelul/slopbuster | 8215cbf | MIT | 聊天收尾套话 |
| https://github.com/woerndl/unsloppify | 0970a26 | MIT | 规则优先级、过程残留、工程俚语 |
| https://github.com/badmuriss/unslop | a3f5666 | CC BY-SA 4.0 | 叙事层痕迹；仅高层重述 |
| https://github.com/adewale/anti-slop-writing | 00b0809 | MIT | 对比句三分类、对冲式对称、压平测试 |
| https://github.com/cursor/plugins | 99b609a | 快照未见许可证 | 抽象隐喻名词、删破折号只用句号逗号 |
| https://github.com/immeasurablematt/a16z-anti-slop | f3caa78 | MIT | 不为展示工作量而改 |
| https://github.com/MariusAure/anti-slop-writing | df7168c | MIT | 用户要求时才解释改动 |
| https://github.com/op7418/Humanizer-zh | f4518a8 | MIT | 中文模式分类、不默认附命中清单与自评 |
| https://github.com/larashero3-dotcom/lieflat-less-ai-tone | 27d2923 | MIT | 翻案腔变体、翻译腔实测范围、不作为改写理由的写法 |
| https://github.com/KKKKhazix/human-writing | 4fda173 | MIT | 中文黑话与抒情词、只交作品不交过程 |
| https://github.com/devswha/patina | 9ad44bc | MIT | 带阈值的中文词汇与句式 |
| https://github.com/OUBIGFA/De-AI-Prompt-Enhancer-Writer-Booster-SKILL | 59eafed | 快照未见许可证 | 首句连读、机器序列、人类区间校准 |
| https://github.com/jiji262/humanizer-chinese | 1d6c08e | MIT | 立场真空、均质书面腔、引号强调 |
| https://github.com/Raymondhou0917/speak-human-tw | 6e56a12 | MIT | 聊天残留、破折号密度、工具残留 |
| https://github.com/swaylq/humanize-chinese | 6510ca7 | 非标准“MIT（Non-Commercial）” | 只输出改写正文、不带腔原样返回；仅高层重述 |
| https://github.com/garden-cosmos/natural-chinese-protocol | a6d4819 | MIT | 反电报体的矫枉过正 |
| https://github.com/leter/zh-tech-writing | ffda935 | MIT | 递进句拆分、宣传形容词 |
| https://github.com/liuliu-66-create/ll-humanizer-zh | f62891a | MIT | 替读者说话、老师式自问自答 |
| https://github.com/meikis/remove-ai-flavor-writing-skill | 5edd9fa | MIT | 阶段壳、易答框、小说动作套话 |
| https://github.com/fy-agent/humanize-chinese-writing | e284777 | 自定义版权，非开源许可 | 不自发补免责声明与提示；仅高层重述 |
| https://github.com/laoguo2025/huoren-write | 1825439 | 快照未见许可证 | 安抚客服腔；仅高层重述 |
| https://github.com/Hyacehila/humanizer-zh-next | 0c3ee9c | MIT | 内部自检不展示、无问题保持原样 |

AGPL-3.0、CC BY-SA 4.0、非商业或自定义版权、以及未见许可证的来源，只用于阅读和独立重述通用方法，未复制任何文本或代码；公开再分发前按 NOTICE.md 重新核对。

## 使用边界

- 本文件只说明规则来源，不替上游项目授权超过其许可证允许的使用。
- 未确认许可证的来源只用于阅读和独立重述通用方法；没有搬入其完整文本、脚本或素材。
- CC BY-NC 4.0 来源的人文学术分析思路在非商业使用范围内署名；商业使用前需要重新核对许可。
- 上游对行业成果、框架效果或平台规则的陈述没有被当作已验证事实。
- 模板和打包脚本来自用户原有 Luz 项目；保留时需要由项目所有者确认再分发条件。
- 原始下载快照是开发证据，不进入最终可安装包，避免无关代码、体积和许可混杂。需要复现时可使用表中仓库和提交号。

## 研究覆盖

本次定向搜索覆盖：

- 中文去 AI 味与自然表达。
- 保声改写与事实保真。
- 科技新闻、事实核查与来源验证。
- 营销文案、直接响应与内容策略。
- 观点文、科普和真实故事。
- 长篇与短篇叙事、连续性、审稿。
- 学术论文、人文学科、结构化文档。
- 风格样本学习与多渠道适配。

选择标准是规则是否能跨项目执行、是否保护事实、是否适合渐进加载。关键词热度、仓库星数和单一成功案例没有被当作质量证明。
