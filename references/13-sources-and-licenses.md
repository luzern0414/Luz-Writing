# 13 · 来源与许可

## 合并来源

本 skill 的核心科技资讯与营销流程来自用户原有的 Luz 资讯与营销写作项目。原有平台、文风、找料、交付规则经过重排和补强，原文相关资产被保留为模板、示例和打包脚本。

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

## 2026-11-02 第三轮：标准、法规与平台规则的官方核对

这一轮只读官方页面和标准原文（个别标准文本是高校或期刊网站托管的副本，状态另在国家标准全文公开系统核对），用来校正中文文字规范、客户文件、协议与政策、营销合规、渠道限制和事实核查的写法。规则落在 `references/18`、`19` 和 02、06、09、10、14 的相应小节；页面内容没有被整段复制。读不到官方原文的项目（小红书、抖音的社区公约全文、字数限制）在对应小节里写明“本次未能核对”。

| 来源 | 给了什么 |
| --- | --- |
| [国家标准全文公开系统：GB/T 7714](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=7714)、[15834](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=15834)、[15835](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=15835)、[9704](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=9704)、[35273](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=35273)、[8567](https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=8567) | 各标准的现行状态和日期：GB/T 7714—2025 于 2025-12-02 发布、2026-07-01 实施，2015 版废止；15834—2011、15835—2011、9704—2012、35273—2020、8567—2006 现行 |
| [GB/T 15834—2011 文本（海南大学托管副本）](https://rdswxb.hainanu.edu.cn/fileRDSWXB/cms/news/info/2026/01/2cf0bffa33554b6eab11970541de10c4/GBT%2015834%E2%80%942011%E6%A0%87%E7%82%B9%E7%AC%A6%E5%8F%B7%E7%94%A8%E6%B3%95.docx) | 标点用法、位置和附录补充规则的条款号与示例（19 › 标点） |
| [GB/T 15835—2011 文本（华东交通大学学报托管副本）](https://journal.ecjtu.edu.cn/uploadfile/hdjtdx/20241115/GBT%2015835%E2%80%942011%20%E5%87%BA%E7%89%88%E7%89%A9%E4%B8%8A%E6%95%B0%E5%AD%97%E7%94%A8%E6%B3%95.pdf) | 数字形式选用、多位数、数值范围、年月日、大写数字（19 › 数字与日期） |
| [GB/T 7714—2025 文本（首都经济贸易大学托管副本）](https://rem.cueb.edu.cn/docs/2026-04/ab13582039564d9090a722f17cfcbf2e.pdf) | 前言列出的与 2015 版的差异、网页著录格式、文献类型与载体标识代码、预印本定义（19 › 参考文献） |
| [党政机关公文处理工作条例（中国政府网）](https://www.gov.cn/zhengce/2013-02/22/content_2640088.htm) | 15 个文种及用途，公文用字用标点按国家标准，请示一文一事，起草要求（19 › 公文） |
| [个人信息保护法（国家税务总局法规库收录）](https://fgk.chinatax.gov.cn/zcfgk/c100009/c5211776/content.html)、[维基文库全文](https://zh.wikisource.org/wiki/%E4%B8%AD%E5%8D%8E%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9B%BD%E4%B8%AA%E4%BA%BA%E4%BF%A1%E6%81%AF%E4%BF%9D%E6%8A%A4%E6%B3%95) | 告知事项、单独同意、敏感个人信息、未成年人、撤回、个人权利、自动化决策推送（09 › 法律与标准依据） |
| [人脸识别技术应用安全管理办法（新华社报道）](https://www.news.cn/politics/20250321/6bb2fe19239449a39d21e75c363a0ce9/c.html) | 2025-06-01 起施行；单独同意、不得作为唯一验证方式、影响评估、监护人同意、保存期限 |
| [小程序用户隐私保护指引内容介绍（微信开放文档）](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/miniprogram-intro.html) | 指引的各部分与填写要求（09 › 协议与政策文本） |
| [格式条款的相关裁判规则（河南法院网）](https://hnylfy.hncourt.gov.cn/public/detail.php?id=3271) | 民法典第四百九十六条原文；第四百九十七条的适用说明 |
| [消费者权益保护法实施条例（新华社报道）](https://www.news.cn/legal/20240321/ee68a5f44b9c43ac8a41eabce31c18fa/c.html) | 自动续费的显著提示要求，2024-07-01 起施行 |
| [明码标价和禁止价格欺诈规定（国务院公报）](https://www.gov.cn/gongbao/content/2022/content_5699926.htm) | 第六、十六、十七、十九、二十条与 2022-07-01 施行日期（06 › 价格说明） |
| [广告绝对化用语执法指南（湖南省政府转载市场监管总局公告）](https://www.hunan.gov.cn/zqt/zcsd/202303/t20230320_29282723.html) | 绝对化用语的范围、不按绝对化用语处理的情形、高风险领域（06 › 合规） |
| [人工智能生成合成内容标识办法（新华社）](https://www.news.cn/politics/20250314/b7a24028f2924b7681e6ed1bfbd8fade/c.html) | 显式与隐式标识、2025-09-01 施行、禁止删改标识（10、14） |
| [微信公众平台运营规则](https://mp.weixin.qq.com/cgi-bin/readtemplate?amp=&amp=&lang=zh_CN&t=business%2Ffaq_operation_tmpl&type=info)、[新增草稿接口](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html) | 诱导分享、诱导关注、误导类内容的条款；标题、作者、摘要、正文长度和封面比例的限制（10 › 平台规则要点） |
| [小红书社区公约 2.0（中国日报报道）](https://cn.chinadaily.com.cn/a/202601/20/WS696eef27a310942cc499bf9f.html)、[“抖音”用户服务协议](https://www.douyin.com/draft/douyin_agreement/douyin_agreement_user.html?type=6) | 虚假人设、AI 辅助标明、虚假营销；夸张标题、来源引用、谣言、AI 内容标识（10 › 平台规则要点） |
| [网安标委标准化工作月报 2026 年 6 月](https://www.tc260.org.cn/tc260/xwdt1/202608/13a4dc58036a4fd083990fd7a9e3714c.shtml) | 《数据安全技术 个人信息安全规范》征求意见稿 2026-06 公开征求意见，期限 60 天 |
| [SIFT：四步法（Mike Caulfield）](https://hapgood.us/2019/06/19/sift-the-four-moves/)、[IFCN 行为准则的五项承诺](https://ifcncodeofprinciples.poynter.org/know-more/the-commitments-of-the-code-of-principles)、[Reuters 记者手册（公开 PDF，较早版本）](https://www.mediareform.org.uk/wp-content/uploads/2015/12/Reuters_Handbook_of_Journalism.pdf) | 追溯原始语境、来源透明与优先一手来源、引语不得改动、匿名来源最弱（02 › 引语与转述） |
| [W3C 中文排版需求（clreq）](https://www.w3.org/TR/clreq/) | 大陆标点以 GB/T 15834 为准，破折号与省略号各占两个字位置，引号次序（19） |
| [微软写作风格指南：十条要点](https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice)、[Google 开发者文档风格指南：要点](https://developers.google.com/style/highlights)与[步骤写法](https://developers.google.com/style/procedures) | 先说重点、简短、读出声、第二人称与主动语态、条件在前、一步一个动作、可选步骤标明（18 › 使用说明） |
| [Kobak 等：用多余词汇发现大模型参与写作（arXiv 2406.07016）](https://arxiv.org/abs/2406.07016)、[维基百科：AI 写作的迹象](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) | 特定风格词在大模型出现后骤增；迹象是描述不是规则，不能单靠它们判断，只修迹象会让检测更难（04、17 的“复查线索”定位） |

没有读到的：国家标准全文公开系统只提供状态列表，未能在线阅读 GB/T 9704 正文，其版式参数引用 Luz-Design 的文件设计规范；AP 新闻价值与原则页拒绝访问；GB/T 35273 修订稿正文未读，只依据网安标委月报确认其已公开征求意见。

## 2026-11-05 第四轮：受众理解与技能架构

本轮为共用材料理解、写作基础和四类场景入口核对官方方法，全部为独立重述。来源阅读与采用范围如下：

| 来源 | 采用位置与范围 |
| --- | --- |
| [Google Technical Writing · Audience](https://developers.google.com/tech-writing/one/audience) | 20、21：区分读者角色、已有知识、知识差距与任务顺序；不把面向技术文档的细节直接套到所有宣传写作 |
| [OpenAI · Build skills](https://learn.chatgpt.com/docs/build-skills) | SKILL.md、cards.json 与评测方法：清楚描述触发任务、按需加载详细规则、优先指令，只为确定行为使用脚本，并验证触发与实际输出 |

第二个来源从技能文档入口重定向至上述页面，读到最佳实践部分，未读页面尾部；本轮没有验证平台实时传播机制、转化收益或各渠道全部运营规则。渠道规则继续使用 10 已注明来源与范围的资料，发布时再核对当前规则。来源快照与检索结论留在本次开发会话的过程目录，不作为安装包依赖。

## 使用边界

- 本文件只说明规则来源，不替上游项目授权超过其许可证允许的使用。
- CC BY-NC 4.0 来源的人文学术分析思路在非商业使用范围内署名；商业使用前需要重新核对许可。
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
