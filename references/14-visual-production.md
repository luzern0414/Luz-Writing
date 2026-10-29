# 14 · 视觉素材与设计排版

本路线把文字内容和视觉生产连起来：明确图片要承担什么阅读任务，先准备无文字素材，再由设计系统完成层级、排版和交付。生成图片本身不是完成品。

## 一、先选对生产方式

| 需求 | 使用 | 原因 |
| --- | --- | --- |
| 封面、话题分隔图、氛围插画、概念视觉 | `D:\Codes\Imagegen` | 生成原创位图素材，适合承担气氛、场景和主题提示 |
| 精确图表、流程图、数据卡、表格、完整文案海报 | HTML/CSS/SVG、设计工具或 `Luz-Design` 的排版流程 | 文字、数据和控件必须可编辑、可核对 |
| 海报、页面视觉系统、封面族、多渠道活动视觉 | `D:\Codes\Luz-Design` | 处理视觉定位、信息层级、组件、安全区和导出验收 |
| 修改已有视觉但保留结构 | `Imagegen/src/imagegen_edit.py` | 用原图作为实际参考输入，而不是只在提示词里描述“类似” |
| 新闻现场照片、用户证言图、真实产品截图 | 授权实拍或真实资产 | 生成图不能被当作事件证据 |

纯文字任务不需要为了“显得完整”而生成图片。只有用户要求配图、成品渠道需要封面/插图，或已明确要制作海报、页面和视觉包时，才进入本路线。

## 二、调用入口

本机入口：

- 图片生成：`D:\Codes\Imagegen\src\imagegen.py`
- 参考图编辑：`D:\Codes\Imagegen\src\imagegen_edit.py`
- 视觉设计：`D:\Codes\Luz-Design\SKILL.md`

使用 Luz-Design 时先读它的规则卡，不直接翻规范页：海报、封面族与活动视觉 `py -X utf8 D:\Codes\Luz-Design\scripts\context.py poster`，阅读型页面 `context.py reading-html`，配色 `context.py palette`。规则卡里有用户偏好、规范原文、工具和检查。

不要读取、打印、复制或写入 `Imagegen\docs\apikey.txt`。密钥由 Imagegen 自己解析。

## 三、一页视觉简报

生成前把以下内容写清；可使用 `assets/03-visual-production-brief.md`：

- 图片在文中的任务：封面、解释、分隔、证据、情绪还是 CTA。
- 对应段落或话题，以及图片应该让读者更快理解什么。
- 目标渠道、摆放位置、实际显示尺寸和裁切风险。
- 画幅、主题、视觉系统、背景、材质、光线和密度。
- 必须出现的主体；明确排除的文字、水印、Logo、真实人物、界面和错误事实。
- 图片之外的可编辑文字：标题、标签、数据、说明和来源。
- 替代文本、图注、素材来源和使用范围。
- 原始文件、设计源文件和导出文件的保存位置。

图不是装饰。相邻段落已经说清的内容，不要求图片把同一句话再造一遍；图片要补充可见对象、关系、过程或氛围，且不能与前文冲突。

## 四、Imagegen 生成

### 1. 先离线检查

在 `D:\Codes\Imagegen` 执行：

~~~powershell
py -X utf8 src/imagegen.py `
  --prompt-file "D:\Codes\skill输出\Luz-Writing\NNN-主题\raw\06-images\01-cover-prompt.txt" `
  --ratio 16:9 `
  --resolution 2k `
  --quality xhigh `
  --format png `
  --output-dir "D:\Codes\skill输出\Luz-Writing\NNN-主题\raw\06-images" `
  --dry-run
~~~

检查提示词、画幅、分辨率、质量和输出目录。`--dry-run` 不读取密钥，也不联网。

### 2. 再生成原始图片

用户已明确要求配图，或当前交付物明确包含视觉生产时，移除 `--dry-run` 后执行。命令会联网并可能产生费用。不要在一次超时后自动重复提交；服务端可能仍在生成。

参考图编辑：

~~~powershell
py -X utf8 src/imagegen_edit.py `
  --image "D:\path\reference.png" `
  --prompt-file "D:\path\edit-prompt.txt" `
  --ratio 3:4 `
  --resolution 2k `
  --quality xhigh `
  --format png `
  --input-fidelity high `
  --count 1 `
  --output-dir "D:\Codes\skill输出\Luz-Writing\NNN-主题\raw\06-images" `
  --dry-run
~~~

参考图只借鉴允许借用的结构、材质和情绪，不复制品牌、受保护作品或原图文案。

### 3. 记录真实结果

Imagegen 只保存服务返回的原始图片字节，并生成同名 JSON。记录：

- 图片路径和生成提示词。
- 请求与实际尺寸、实际格式。
- `warnings`、生成张数和查询时间。
- 后续若为版式做过裁切、缩放、压缩或转码，另存导出文件并标为已加工。

服务可能不严格兑现请求比例或格式。不要把请求 3:4 写成“已获得原生 3:4”，也不要把 PNG 改名成 JPEG。做展示裁切时保留原始图片。

## 五、生成提示词

按以下顺序写：

1. 图片任务和读者要获得的视觉信息。
2. 主体、环境、动作与各对象关系。
3. 画幅、裁切、视角、景深和留白。
4. 视觉语言、材质、光线、色彩与明度关系。
5. 与文章和品牌一致的风格约束。
6. 必须避免的内容。

默认要求：

- 画面内不放文字、数字、Logo、水印、现成 UI 或不存在的品牌标识。
- 标题、图注、数据、CTA 和版权信息放在可编辑排版层。
- 不伪造新闻现场、真实用户、产品界面、评价、引用或证据。
- 不使用与内容无关的装饰性 3D 物体。
- 一张图只解决一个视觉任务。

### 封面与插图风格菜单

先按题材、语气和渠道选一种风格，一篇文章的封面和分隔图只用一种。用户点名的风格优先；没有点名时，科技资讯默认 3D 潮玩或软陶质感。提示词片段放在第 4 步“视觉语言”，按需改写，不整段照抄。

| 风格 | 适合 | 视觉特征 | 提示词片段 |
| --- | --- | --- | --- |
| **3D 潮玩** | 科技资讯、新品发布、轻松话题 | 圆润潮玩公仔、哑光质感、明快配色 | `designer-toy 3D figure, rounded proportions, matte vinyl, soft studio light` |
| **软陶质感** | 生活方式、AI 小工具、温和科普 | 手捏黏土、指纹细节、真实接触阴影、低饱和 | `soft polymer clay miniature, handmade texture, muted pastel palette, contact shadows` |
| 扁平插画 | 教程、科普、政策与流程解读 | 纯色块、无渐变、简化人物与物体 | `flat vector illustration, solid color shapes, no gradients, clean composition` |
| 线性图标风 | 工具清单、功能盘点、文档类封面 | 统一线宽线稿、白底、一个强调色 | `minimal line-art icons, uniform stroke weight, white background, single accent color` |
| 等距 2.5D | 系统架构、产业链、数据中心、流程 | 等距视角、模块化方块、层次清楚 | `isometric 2.5D scene, modular blocks, clean edges, soft ambient light` |
| 纸艺拼贴 / 剪纸 | 节日、文化、人文与故事类 | 纸张层叠、投影、手工剪边 | `layered paper-cut collage, visible paper texture, gentle drop shadows` |
| 极简排版 / 大字报 | 观点、评论、重大结论 | 大面积留白或纯色底，只留出给排版层放字的位置 | `minimal background, bold color field, large empty area reserved for typography` |
| 新中式水墨 | 传统文化、节气、国货与文旅 | 水墨晕染、留白、淡彩 | `contemporary Chinese ink wash, generous negative space, light color wash` |
| 胶片摄影感 | 人物故事、城市、深度报道的氛围图 | 颗粒、自然光、偏暖色调；不冒充真实现场 | `35mm film photography look, natural light, subtle grain, warm tones, staged scene` |
| 赛博霓虹 | 芯片、游戏、夜间经济、未来感话题 | 深色底、霓虹描边、高对比 | `cyberpunk neon, dark background, glowing edges, high contrast, rain reflections` |
| 手绘涂鸦 | 轻松吐槽、学生与职场日常 | 马克笔线条、随手涂抹、不规则边缘 | `hand-drawn doodle, marker strokes, playful sketchy lines, off-white paper` |
| 数据可视化封面 | 财报、榜单、调研与趋势 | 抽象图形暗示数据走势；真实数字只在排版层 | `abstract data-visualization motif, flowing bars and lines, no numbers, no text` |

这份菜单只管文章封面和插图。产品界面（小程序、后台、网站、智能体）一律按 Luz-System 与 Luz-Design 的扁平线性风格，不套用这里的 3D、拟物或霓虹风格。

## 六、交给 Luz-Design 编排

需要海报、成套封面、活动视觉或长页排版时，交给 Luz-Design（luz-design 技能，先读上面的规则卡）；小程序、后台、网站等产品界面与原型交给 Luz-System（luz-system 技能）。写作这边先做好：

1. 用一句话写定位：读者是谁，在什么场景看到，先看见什么，理解什么，下一步做什么。
2. 从定位推导色彩、字体层级、间距、形状、图像语言和密度。
3. 先搭文案层级与版式骨架，再把生成图片放入；不要先堆装饰。
4. 主要信息、次要信息、证明、时间和行动各有明确层级。
5. 文字、价格、日期、法律说明和二维码使用可编辑层并逐项核对。
6. 在海报或页面中保留安全区、出血、裁切和渠道遮挡空间。
7. 按 Luz-Design 规则卡的“交付前必须通过”与 `check_document.py` 完成视觉、可读性、可访问性和导出复核。

文章只需要封面或插图时，不必创建完整设计项目。依据文章结构确定一张封面、每几个话题一张图，或完全不配图；只有跨渠道视觉、详细排版或海报任务才进入完整 Luz-Design 工作流；产品界面走 Luz-System。

## 七、写作与版式结合

常见组合：

- **公众号科技资讯：** 封面 + 话题分隔图；正文使用 Luz-Design 阅读型模板和排版脚本，图片放在 `raw/06-images/`，通过 `[img] 路径 | 替代文本 | 图注` 接入。
- **公众号深度长文：** 先完成标题、摘要、正文层级，再设计封面族；版面保持短段和事实层级。
- **小红书：** 3:4 图文时先排每页的信息顺序，再生成无文字底图；文字放在排版层。
- **短视频：** 9:16 画幅只负责场景和视觉钩子；口播、字幕和事实不能交给图片生成。
- **电商、活动与海报：** 同时读本路线与 Luz-Design 的 poster 规则卡，先完成信息层级和精确文案。
- **网页或 UI：** 精确界面由 Luz-System 定义、视觉标准来自 Luz-Design，并由代码实现；Imagegen 只生成可用的无文字氛围素材。

公众号宽封面可向 Imagegen 请求自定义宽幅尺寸，例如 `--size 2368x1008`，但必须检查实际返回尺寸。其他渠道以当前平台规则和真实显示环境为准。

## 八、放置与验收

在 `raw/manifest.json` 的 `images` 或 `raw/06-images/` 的记录文件中为每张图登记：

| 位置 | 文件 | 任务 | 替代文本/图注 | 来源或生成记录 | 加工状态 |
| --- | --- | --- | --- | --- | --- |
| 封面/段落 | 本地路径 | 读者应获得什么 | 辅助阅读的文字 | JSON/授权记录 | 原始/已裁切 |

交付前检查：

- 图片确实对应相邻内容，不重复正文，也不暗示未发生的事实。
- 主体、对象、数据、产品方向和场景没有错误。
- 原图无乱码文字、水印、Logo、错误界面和不必要装饰。
- 实际宽高比适合渠道；裁切没有切掉主体，缩略图仍能识别。
- 排版层文字可编辑，图注、替代文本和来源完整；正文里的图片用 `[img] 路径 | 替代文本 | 图注` 写进去，builder 缺替代文本会警告。
- HTML 中图片路径有效，构建后能打开，封面和复制区完整。
- 素材权利、生成参数和加工状态可追溯。
- 任何失败都明确说明：没有生成、没有验证或依赖本机工具不可用。

## 九、失败与回退

- **Imagegen 不可用：** 继续完成文字，把 prompts 和视觉简报存进 `raw/06-images/`，对话里一句话说明图片未生成；不要声称图片已经生成。
- **只缺少视觉反馈：** 可用临时占位框检查层级；占位框不进入成品 HTML。
- **比例或格式不符：** 保留原图，记录偏差；按版式需求另做导出并标注加工。
- **生成图片含错误文字：** 不作为成品；重写 prompt，或使用设计排版层覆盖。不能靠肉眼忽略乱码。
- **Luz-Design 不可用：** 使用本路线的层级和验收规则产出基础排版方案，但不要声称已经通过 Luz-Design 验证。
- **图片不能证明事实：** 改回数据图、授权照片、原始截图或文字说明。

视觉生产完成后，回到 [11 · 质量闸门](11-quality-gates.md)，分别检查内容、素材和最终文件。
