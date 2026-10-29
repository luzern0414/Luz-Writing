#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把正文文本和图片打包成单文件阅读型网页，排版遵循 Luz-Design 阅读型网页规范。

用法：
  py -X utf8 02-article_builder.py --title "标题" --body body.txt --session "D:\\Codes\\skill输出\\Luz-Writing\\001-主题"
  py -X utf8 02-article_builder.py --title "标题" --body body.txt --out 测试.html   # 仅用于测试

--session 时输出固定为 <会话>/<会话名>.html，正文源默认取 <会话>/raw/04-draft.txt，
生成后自动调用 D:\\Codes\\Luz-Design\\scripts\\check_document.py 和 03-session.py 的会话检查，报错即失败。

模板和本脚本只是骨架，不是规范：动笔前先运行 06-context.py <类型> 读完规则卡。--session 打包前检查
raw/00-rules/ 有当前规则卡（写作指南改过就要重新生成）、raw/01-brief.md 的“采用的规则”不为空、
“本次沉淀”的 key 已用 04-experience.py note 写入或确认（不早于会话创建日）；任何一项不满足就拒绝，
并写明要运行的命令。--out 只用于测试，不能写进 Luz-Writing 输出根目录。

body.txt 的格式（references/16 › 正文格式 是同一份说明）：
  - 空行分段，一段一个 <p>
  - 行首 "## " 二级标题，"### " 三级标题
  - 单独一行 "[img] 图片路径 | 替代文本 | 图注" 插入一张图；替代文本与图注可省略（省略替代文本会警告），
    相对路径相对正文文件解析
  - 行首 "> " 是逐字引用（第三方原话），不用于作者自己的提示或建议
  - 连续以 "|" 开头的行是表格：第一行表头，"| --- |" 分隔线可有可无；用于文案键表等整句表格
  - 段内 **文字** 加粗，==文字== 高亮；其余原样输出（会做 HTML 转义）

图片默认转成 JPEG（质量 85，最长边 1600px）再 base64 内嵌；--keep-original 则原样内嵌。
--copy-button 只在用户明确要求“一键复制到公众号”时使用。
--theme 选主色：默认 auto 按标题和正文关键词匹配 Luz-Design themes.json 的行业主题（健身、咖啡、宠物……），
取主题的 action / actionTint 作 --accent / --tint，引用线、高亮和标签页图标一起换色；没有匹配的行业时用
template（模板自带的 --accent / --tint）。也可以直接写主题 key，例如 --theme fitness-gym。
--icon 选浏览器标签页图标；默认 auto 先跟随选中的主题（ai-agent 用芯片、fitness-gym 用哑铃、餐饮类用碗），
主题没有对应图案时再按标题和正文关键词挑选。
"""

import argparse
import base64
import html
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "01-article-template.html"
OUTPUT_ROOT = Path(r"D:\Codes\skill输出\Luz-Writing")
CHECK_DOCUMENT = Path(r"D:\Codes\Luz-Design\scripts\check_document.py")
THEMES_FILE = Path(r"D:\Codes\Luz-Design\references\themes.json")
SESSION_NAME = re.compile(r"^\d{3}-.+$")
# 模板顶部“模板只是骨架”的注释只写给动笔的人看，成品里去掉。
TEMPLATE_NOTE = re.compile(r"<!--\s*模板只是骨架.*?-->[ \t]*\r?\n?", re.S)
CARD_HINT = ("规则卡：模板和本脚本只是骨架，内容、结构、声音与检查以规则卡为准；动笔前运行 "
             "`py -X utf8 scripts/06-context.py <类型>`（list 看类型）读完整张卡。")

# 公众号编辑器会剥掉 class，所以正文样式都写成内联。字号、字重、行高与间距按 Luz-Design file-design.html
# “阅读型网页 › 排版参数”：主标题 32/700、二级标题 24/700、三级标题 20/600、正文 16/400、图注与数字表格 14。
P_STYLE = "font-size:16px;line-height:1.75;color:#202124;margin:0 0 16px;"
H2_STYLE = "font-size:24px;line-height:1.3;font-weight:700;color:#202124;margin:48px 0 16px;"
H3_STYLE = "font-size:20px;line-height:1.4;font-weight:600;color:#202124;margin:28px 0 12px;"
# 阅读型产出圆角全篇统一一个值（visual-design.html：4–12 像素之间），图片、高亮与复制按钮共用。
RADIUS = "8px"
# 引用线和高亮底随主题换色：{accent} / {tint} 在生成时填入。
QUOTE_STYLE = ("font-size:16px;line-height:1.75;color:#5f6368;margin:0 0 16px;"
               "padding:2px 0 2px 14px;border-left:3px solid {accent};")
STRONG_STYLE = "font-weight:600;color:#202124;"
HL_STYLE = f"background:{{tint}};padding:0 4px;border-radius:{RADIUS};"
IMG_STYLE = f"display:block;width:100%;height:auto;border-radius:{RADIUS};"
FIGURE_STYLE = "margin:24px 0;"
CAPTION_STYLE = "font-size:14px;line-height:1.5;color:#5f6368;margin:8px 0 0;text-align:center;"
# 表格：表头浅底 600、居中；只有横向细线；长文字左对齐，短值居中，金额右对齐（等宽数字）。
TABLE_STYLE = "width:100%;border-collapse:collapse;margin:24px 0;font-size:16px;line-height:1.5;"
TH_STYLE = ("background:{tint};font-weight:600;color:#202124;text-align:center;padding:10px 12px;"
            "border-top:1px solid #dadce0;border-bottom:1px solid #dadce0;")
TD_STYLE = "padding:10px 12px;border-bottom:1px solid #dadce0;color:#202124;text-align:{align};vertical-align:top;"
SHORT_CELL = 8          # 不超过这么多字的列算短值，居中
MONEY = re.compile(r"^[-+]?\s*[¥￥$]\s*[\d,.]+|^[-+]?[\d,.]+\s*元$")

# 标签页图标：32×32 圆角浅色底 + 一笔主色线稿，最多 3 个图形、无文字，16px 下可辨认。
# 只放在 <head>，不进入 #copy-area，不影响复制到公众号。
ICONS = {
    "tech": ("M10 10h12v12H10z", "M13 6v4M19 6v4M13 22v4M19 22v4M6 13h4M6 19h4M22 13h4M22 19h4"),  # 芯片
    "fitness": ("M11 16h10", "M9 11v10M23 11v10", "M6 13.5v5M26 13.5v5"),  # 哑铃
    "food": ("M6 15h20c0 5.5-4.5 9.5-10 9.5S6 20.5 6 15z", "M13 6.5c-1.2 1.5 1.2 2.5 0 4.5M19 6.5c-1.2 1.5 1.2 2.5 0 4.5"),  # 碗
    "travel": ("M5.5 15 26 6.5 19.5 25.5 15 17.5z", "M15 17.5 26 6.5"),  # 纸飞机
    "finance": ("M7 6.5v18.5h18.5", "M11 19.5l4.5-5 3.5 3 6-7"),  # 折线
    "education": ("M16 10c-3-2-6.5-2.3-10-1.3v15c3.5-1 7-.7 10 1.3 3-2 6.5-2.3 10-1.3v-15c-3.5-1-7-.7-10 1.3z", "M16 10v15"),  # 书本
    "article": ("M8.5 5.5h15v21h-15z", "M12.5 11h7M12.5 15.5h7M12.5 20h4"),  # 文章
}
# 图标先跟随选中的主题，主色与图案出自同一个判断；主题没有对应图案（或用模板颜色）时才按关键词挑。
THEME_ICONS = {
    "ai-agent": "tech", "fitness-gym": "fitness",
    **{key: "food" for key in ("xiangcai", "sichuan-hotpot", "cantonese-cafe", "japanese-sushi", "bbq-snack", "coffee",
                               "milk-tea", "bakery-dessert", "fast-noodle", "western-light")},
}
# 关键词按顺序匹配，先命中的类别优先；都不命中用 article
ICON_KEYWORDS = (
    ("tech", ("AI", "人工智能", "大模型", "芯片", "算法", "科技", "GPT", "机器人", "智能体", "编程", "代码", "软件", "互联网")),
    ("fitness", ("健身", "运动", "训练", "增肌", "减脂", "跑步", "瑜伽", "体能", "马甲线", "腹肌", "减肥", "肌肉")),
    ("food", ("美食", "菜谱", "餐厅", "食谱", "烹饪", "厨房", "咖啡", "烘焙", "小吃", "做饭", "面条", "牛肉面", "火锅",
              "甜品", "早餐", "午餐", "晚餐")),
    ("travel", ("旅行", "旅游", "出行", "机票", "酒店", "景点", "自驾", "出游")),
    ("finance", ("财经", "金融", "股票", "基金", "投资", "理财", "经济", "营收", "财报", "利率")),
    ("education", ("教育", "学习", "课程", "考试", "学校", "读书", "老师", "学生")),
)
HEX6 = re.compile(r"#[0-9A-Fa-f]{6}")

# 主题关键词：主题自身的名称和细分（themes.json 的 label / subtype）之外补的常用说法；过于通用的细分词不参与匹配。
THEME_ALIASES = {
    "ai-agent": ("AI", "人工智能", "大模型", "智能体", "Agent", "GPT", "提示词"),
    "fitness-gym": ("健身", "运动", "训练", "增肌", "减脂", "跑步", "瑜伽", "体能", "撸铁", "私教"),
    "fast-noodle": ("牛肉面", "拉面", "米粉", "快餐"),
    "coffee": ("咖啡", "拿铁", "美式"),
    "milk-tea": ("奶茶", "果茶", "茶饮"),
    "bakery-dessert": ("蛋糕", "甜品", "面包", "烘焙"),
    "pharmacy": ("药店", "药房", "用药"),
    "pet": ("宠物", "猫咪", "狗狗", "猫粮", "狗粮"),
    "florist": ("鲜花", "花店", "花束"),
}
THEME_STOPWORDS = {"预约", "同城配送", "用品", "健康用品", "效率工具", "AI 助手"}


def load_themes() -> dict:
    """Luz-Design 行业主题表；读不到时返回空表，只能用 template。"""
    try:
        return json.loads(THEMES_FILE.read_text(encoding="utf-8")).get("themes", {})
    except (OSError, ValueError):
        return {}


def theme_keywords(key: str, theme: dict) -> list[str]:
    words = [w.strip() for w in re.split(r"[、/]", f"{theme.get('label', '')}/{theme.get('subtype', '')}")]
    words += THEME_ALIASES.get(key, ())
    return [w for w in dict.fromkeys(words) if len(w) >= 2 and w not in THEME_STOPWORDS]


def pick_theme(title: str, body: str, themes: dict) -> str:
    """标题命中优先（按主题表顺序），其次看正文前 2000 字里关键词出现次数最多的主题；都不命中用 template（模板自带颜色）。"""
    for key, theme in themes.items():
        if any(w in title for w in theme_keywords(key, theme)):
            return key
    head = body[:2000]
    scores = {key: sum(head.count(w) for w in theme_keywords(key, theme)) for key, theme in themes.items()}
    best = max(scores, key=lambda k: scores[k], default="template")
    return best if scores.get(best, 0) >= 2 else "template"


def apply_theme(template: str, accent: str, tint: str) -> str:
    """把模板 :root 的 --accent / --tint 换成主题色。"""
    template = re.sub(r"(--accent:\s*)#[0-9A-Fa-f]{6}", lambda m: m.group(1) + accent, template, count=1)
    return re.sub(r"(--tint:\s*)#[0-9A-Fa-f]{6}", lambda m: m.group(1) + tint, template, count=1)


def pick_icon(title: str, body: str, theme_key: str = "template") -> str:
    """先跟随主题（THEME_ICONS）；否则标题命中优先（按类别顺序），其次看正文前 2000 字里出现次数最多的类别。
    大小写敏感，避免 AI 误配 said。"""
    if theme_key in THEME_ICONS:
        return THEME_ICONS[theme_key]
    for kind, words in ICON_KEYWORDS:
        if any(w in title for w in words):
            return kind
    head = body[:2000]
    scores = {kind: sum(head.count(w) for w in words) for kind, words in ICON_KEYWORDS}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "article"


def template_colors(template: str):
    """模板 :root 里的 --accent（线稿）和 --tint（底色）。"""
    found = dict(re.findall(r"--(accent|tint):\s*(#[0-9A-Fa-f]{6})", template))
    return found.get("accent", "#2b5f73"), found.get("tint", "#e9f2f5")


def icon_link(kind: str, color: str, tint: str) -> str:
    if kind not in ICONS:
        sys.exit(f"未知图标：{kind}，可选 {', '.join(ICONS)}")
    if not (HEX6.fullmatch(color) and HEX6.fullmatch(tint)):
        sys.exit(f"图标颜色必须是 #RRGGBB：{color} / {tint}")
    paths = "".join(f"<path d='{d}'/>" for d in ICONS[kind])
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
           f"<rect width='32' height='32' rx='8' fill='{tint}'/>"
           f"<g fill='none' stroke='{color}' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>{paths}</g>"
           "</svg>")
    encoded = quote(svg, safe=" '=/:,.-")
    return f'<link rel="icon" href="data:image/svg+xml,{encoded}">'


COPY_CSS = """#copy-btn { position: fixed; right: 16px; bottom: calc(20px + env(safe-area-inset-bottom, 0px));
    font: inherit; font-size: 14px; font-weight: 600; color: #ffffff; background: var(--accent);
    border: 0; border-radius: """ + RADIUS + """; padding: 12px 20px; cursor: pointer; }"""
COPY_HTML = """<button id="copy-btn" type="button">复制正文</button>
<script>
(function () {
  var area = document.getElementById('copy-area');
  var btn = document.getElementById('copy-btn');
  function flash(text) { var old = btn.textContent; btn.textContent = text; setTimeout(function () { btn.textContent = old; }, 2200); }
  btn.addEventListener('click', function () {
    if (!navigator.clipboard || !window.ClipboardItem) { flash('请用 Chrome 或 Edge 打开'); return; }
    var item = new ClipboardItem({
      'text/html': new Blob(['<div>' + area.innerHTML + '</div>'], { type: 'text/html' }),
      'text/plain': new Blob([area.innerText], { type: 'text/plain' })
    });
    navigator.clipboard.write([item]).then(function () { flash('已复制'); }).catch(function () { flash('复制失败'); });
  });
})();
</script>"""

SIZE_WARN_MB = 15


def inline(text: str, accent: str = "#2b5f73", tint: str = "#e9f2f5") -> str:
    """转义后处理段内标记：**加粗**、==高亮==。"""
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: f'<strong style="{STRONG_STYLE}">{m.group(1)}</strong>', s)
    s = re.sub(r"==(.+?)==", lambda m: f'<span style="{HL_STYLE.format(tint=tint)}">{m.group(1)}</span>', s)
    return s


def encode_image(path: Path, keep_original: bool, max_side: int = 1600, quality: int = 85) -> str:
    data = path.read_bytes()
    if keep_original:
        ext = path.suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
        return f"data:image/{mime};base64," + base64.b64encode(data).decode("ascii")

    try:
        from PIL import Image
    except ImportError:
        print("警告：没有安装 Pillow，图片原样内嵌（文件会很大）", file=sys.stderr)
        return encode_image(path, True)

    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")

    w, h = im.size
    scale = max_side / max(w, h)
    if scale < 1:
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


TABLE_SEPARATOR = re.compile(r"^\|(\s*:?-{2,}:?\s*\|)+\s*$")


def table_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_image(value: str) -> tuple[str, str, str]:
    """"路径 | 替代文本 | 图注"：Windows 路径里不会有 |，所以按 | 切分安全。"""
    parts = [p.strip() for p in value.split("|")]
    parts += ["", ""]
    return parts[0], parts[1], parts[2]


def parse_body(text: str):
    """返回 [("p"|"h2"|"h3"|"quote"|"img"|"table", 值)] 的列表；img 的值是 (路径, 替代文本, 图注)，table 的值是行列表。"""
    blocks = []
    buf = []
    rows: list[list[str]] = []

    def flush():
        if buf:
            blocks.append(("p", "".join(buf)))
            buf.clear()

    def flush_table():
        if rows:
            blocks.append(("table", [r[:] for r in rows]))
            rows.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|"):
            flush()
            if not TABLE_SEPARATOR.match(line):
                rows.append(table_cells(line))
            continue
        flush_table()
        if not line:
            flush()
            continue
        if line.lower().startswith("[img]"):
            flush()
            blocks.append(("img", parse_image(line[5:].strip())))
            continue
        if line.startswith("### "):
            flush()
            blocks.append(("h3", line[4:].strip()))
            continue
        if line.startswith("## "):
            flush()
            blocks.append(("h2", line[3:].strip()))
            continue
        if line.startswith(">"):
            flush()
            blocks.append(("quote", line.lstrip("> ").strip()))
            continue
        buf.append(line)
    flush()
    flush_table()
    return blocks


def column_aligns(rows: list[list[str]]) -> list[str]:
    """每列一个对齐：金额右对齐，短值（不超过 SHORT_CELL 字）居中，长文字左对齐。表头另外居中。"""
    width = max(len(r) for r in rows)
    body = rows[1:] or rows
    aligns = []
    for i in range(width):
        cells = [r[i] for r in body if i < len(r) and r[i]]
        if cells and all(MONEY.match(c) for c in cells):
            aligns.append("right")
        elif cells and all(len(c) <= SHORT_CELL for c in cells):
            aligns.append("center")
        else:
            aligns.append("left")
    return aligns


def render_table(rows: list[list[str]], accent: str, tint: str) -> str:
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    aligns = column_aligns(rows)
    head = "".join(f'<th style="{TH_STYLE.format(tint=tint)}">{inline(c, accent, tint)}</th>' for c in rows[0])
    lines = [f'    <table style="{TABLE_STYLE}">', f"      <thead><tr>{head}</tr></thead>", "      <tbody>"]
    for row in rows[1:]:
        cells = "".join(
            f'<td style="{TD_STYLE.format(align=a)}{"font-variant-numeric:tabular-nums;" if a == "right" else ""}">'
            f"{inline(c, accent, tint)}</td>" for c, a in zip(row, aligns))
        lines.append(f"        <tr>{cells}</tr>")
    lines += ["      </tbody>", "    </table>"]
    return "\n".join(lines)


def render(blocks, body_dir: Path, keep_original: bool, accent: str = "#2b5f73", tint: str = "#e9f2f5"):
    parts = []
    n_img = 0
    n_p = 0
    for kind, value in blocks:
        if kind == "img":
            path, alt, caption = value
            img_path = Path(path)
            if not img_path.is_absolute():
                img_path = (body_dir / img_path).resolve()
            if not img_path.exists():
                sys.exit(f"找不到图片：{img_path}")
            src = encode_image(img_path, keep_original)
            n_img += 1
            if not alt:
                print(f"警告：第 {n_img} 张图没有替代文本，用“[img] 路径 | 替代文本 | 图注”补上（11 › Gate 10）", file=sys.stderr)
            alt_text = html.escape(alt or f"插图{n_img}", quote=True)
            figcaption = f'<figcaption style="{CAPTION_STYLE}">{inline(caption, accent, tint)}</figcaption>' if caption else ""
            parts.append(f'    <figure style="{FIGURE_STYLE}"><img src="{src}" alt="{alt_text}" style="{IMG_STYLE}">{figcaption}</figure>')
        elif kind == "table":
            parts.append(render_table(value, accent, tint))
        elif kind == "h2":
            parts.append(f'    <h2 style="{H2_STYLE}">{inline(value, accent, tint)}</h2>')
        elif kind == "h3":
            parts.append(f'    <h3 style="{H3_STYLE}">{inline(value, accent, tint)}</h3>')
        elif kind == "quote":
            parts.append(f'    <blockquote style="{QUOTE_STYLE.format(accent=accent)}">{inline(value, accent, tint)}</blockquote>')
            n_p += 1
        else:
            parts.append(f'    <p style="{P_STYLE}">{inline(value, accent, tint)}</p>')
            n_p += 1
    return "\n".join(parts), n_p, n_img


_SESSION_MODULE = None


def load_session_module():
    """会话脚本 03-session.py（卡口与会话检查都在那里）；文件名带编号，按路径加载，只加载一次（测试可替换其 NOTES_FILE）。"""
    global _SESSION_MODULE
    if _SESSION_MODULE is None:
        spec = importlib.util.spec_from_file_location("luz_writing_session", HERE / "03-session.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SESSION_MODULE = module
    return _SESSION_MODULE


def inside_output_root(path: Path) -> bool:
    """--out 指向 Luz-Writing 输出根目录（含其中的会话）时为 True；正式成品只能走 --session 卡口。"""
    root = OUTPUT_ROOT.resolve()
    target = path.resolve()
    return target == root or root in target.parents


def resolve_session(session: str) -> Path:
    folder = Path(session).resolve()
    if not folder.is_dir() or not SESSION_NAME.match(folder.name):
        sys.exit(f"会话目录必须是已创建的 NNN-主题 文件夹：{folder}")
    if folder.parent != OUTPUT_ROOT.resolve():
        print(f"警告：会话不在固定输出根目录 {OUTPUT_ROOT} 下", file=sys.stderr)
    if not (folder / "raw").is_dir():
        sys.exit(f"会话缺少 raw/：{folder}")
    return folder


def run_document_check(out: Path) -> None:
    if not CHECK_DOCUMENT.is_file():
        print(f"警告：找不到 {CHECK_DOCUMENT}，未运行文档检查", file=sys.stderr)
        return
    proc = subprocess.run([sys.executable, "-X", "utf8", str(CHECK_DOCUMENT), str(out)],
                          text=True, capture_output=True, encoding="utf-8", errors="replace")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        sys.exit("文档检查未通过，修正正文后重新生成")


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(description="把正文文本和图片打包成单文件阅读型网页")
    ap.add_argument("--title", required=True, help="大标题，也是页面第一行可见内容")
    ap.add_argument("--body", help="正文文本文件（UTF-8）；--session 时默认 raw/04-draft.txt")
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--session", help="NNN-主题 会话目录；输出 <会话>/<会话名>.html")
    target.add_argument("--out", help="任意输出路径，仅用于测试")
    ap.add_argument("--template", default=str(TEMPLATE), help="模板路径，默认 assets/01-article-template.html")
    ap.add_argument("--keep-original", action="store_true", help="图片不转 JPEG，原样内嵌")
    ap.add_argument("--copy-button", action="store_true", help="用户明确要求时才加复制按钮")
    ap.add_argument("--icon", default="auto", choices=["auto", *ICONS],
                    help="标签页图标：tech 芯片 / fitness 哑铃 / food 碗 / travel 纸飞机 / finance 折线 / "
                         "education 书本 / article 文章；默认 auto 先跟随主题，主题没有对应图案时按关键词挑选")
    ap.add_argument("--theme", default="auto",
                    help="主色：默认 auto 按标题和正文关键词匹配 Luz-Design 行业主题；template 用模板自带颜色；"
                         "或直接写主题 key，例如 fitness-gym")
    ap.add_argument("--no-check", action="store_true", help="跳过 Luz-Design 文档检查（仅测试）")
    args = ap.parse_args(argv)

    print(CARD_HINT, file=sys.stderr)
    session_module = None
    if args.session:
        session = resolve_session(args.session)
        session_module = load_session_module()
        cards = sorted((session / "raw" / session_module.RULES_DIR).glob("*.md"))
        if cards:
            print("本会话的规则卡：" + "、".join(str(card) for card in cards), file=sys.stderr)
        # 卡口：当前规则卡、“采用的规则”、“本次沉淀”，缺一项就不打包。
        errors = session_module.packaging_errors(session)
        if errors:
            for error in errors:
                print(f"拒绝打包：{error}", file=sys.stderr)
            sys.exit("先读完规则卡，填写 raw/01-brief.md 的“采用的规则”，用 04-experience.py note 写入或确认经验并填进"
                     "“本次沉淀”，再重新运行本命令")
        out = session / f"{session.name}.html"
        body_path = Path(args.body) if args.body else session / "raw" / "04-draft.txt"
    else:
        if not args.body:
            sys.exit("--out 模式需要 --body")
        out = Path(args.out)
        if inside_output_root(out):
            sys.exit(f"--out 只用于测试，不能写进 {OUTPUT_ROOT}；正式成品用 --session \"<会话目录>\"")
        body_path = Path(args.body)
    if not body_path.is_file():
        sys.exit(f"找不到正文：{body_path}")

    text = body_path.read_text(encoding="utf-8-sig")
    template = TEMPLATE_NOTE.sub("", Path(args.template).read_text(encoding="utf-8"))
    themes = load_themes()
    theme_key = pick_theme(args.title, text, themes) if args.theme == "auto" else args.theme
    if theme_key != "template":
        if theme_key not in themes:
            sys.exit(f"未知主题：{theme_key}，可选 auto、template、{'、'.join(themes) or '（读不到 ' + str(THEMES_FILE) + '）'}")
        template = apply_theme(template, themes[theme_key]["action"], themes[theme_key]["actionTint"])
    accent, tint = template_colors(template)
    body_html, n_p, n_img = render(parse_body(text), body_path.parent, args.keep_original, accent, tint)

    if "{{ICON}}" not in template:
        sys.exit("模板缺少 {{ICON}} 占位符：每个成品网页都必须有标签页图标")
    icon_kind = pick_icon(args.title, text, theme_key) if args.icon == "auto" else args.icon
    page = (
        template
        .replace("{{ICON}}", icon_link(icon_kind, accent, tint))
        .replace("{{TITLE}}", html.escape(args.title, quote=False))
        .replace("{{BODY}}", body_html)
        .replace("{{EXTRA_CSS}}", COPY_CSS if args.copy_button else "")
        .replace("{{EXTRA_HTML}}", COPY_HTML if args.copy_button else "")
    )
    if "{{" in page:
        sys.exit("模板里还有没替换的占位符，检查模板文件")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"已生成：{out}")
    print(f"段落 {n_p} 个，图片 {n_img} 张，标签页图标 {icon_kind}，主题 {theme_key}（{accent}），大小 {size_mb:.2f} MB")
    if size_mb > SIZE_WARN_MB:
        print(f"警告：超过 {SIZE_WARN_MB} MB，减少图片或降低质量", file=sys.stderr)
    if not args.no_check:
        run_document_check(out)
    if session_module is not None:
        errors = session_module.session_errors(session)
        if errors:
            for error in errors:
                print(f"FAIL: {error}", file=sys.stderr)
            sys.exit("会话检查未通过，按上面的提示修正后重新生成")


if __name__ == "__main__":
    main()
