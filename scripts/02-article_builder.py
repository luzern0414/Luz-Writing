#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把正文文本和图片打包成单文件阅读型网页，排版遵循 Luz-Design 阅读型网页规范。

用法：
  python -X utf8 02-article_builder.py --title "标题" --body body.txt --session "D:\\Codes\\skill输出\\Luz-Writing\\001-主题"
  python -X utf8 02-article_builder.py --title "标题" --body body.txt --out 测试.html   # 仅用于测试

--session 时输出固定为 <会话>/<会话名>.html，正文源默认取 <会话>/raw/04-draft.txt，
生成后自动调用 D:\\Codes\\Luz-Design\\scripts\\check_document.py，报错即失败。

body.txt 的格式：
  - 空行分段，一段一个 <p>
  - 行首 "## " 二级标题，"### " 三级标题
  - 单独一行 "[img] 图片路径" 插入一张图；相对路径相对正文文件解析
  - 行首 "> " 是逐字引用（第三方原话），不用于作者自己的提示或建议
  - 段内 **文字** 加粗，==文字== 高亮；其余原样输出（会做 HTML 转义）

图片默认转成 JPEG（质量 85，最长边 1600px）再 base64 内嵌；--keep-original 则原样内嵌。
--copy-button 只在用户明确要求“一键复制到公众号”时使用。
--icon 选浏览器标签页图标；默认 auto 按标题和正文关键词挑选，颜色取模板的 --accent / --tint。
"""

import argparse
import base64
import html
import io
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "01-article-template.html"
OUTPUT_ROOT = Path(r"D:\Codes\skill输出\Luz-Writing")
CHECK_DOCUMENT = Path(r"D:\Codes\Luz-Design\scripts\check_document.py")
SESSION_NAME = re.compile(r"^\d{3}-.+$")

# 公众号编辑器会剥掉 class，所以正文样式都写成内联；字阶取 Luz-Design 阅读型 14/16/20/24/32
P_STYLE = "font-size:16px;line-height:1.75;color:#202124;margin:0 0 16px;"
H2_STYLE = "font-size:24px;line-height:1.35;font-weight:600;color:#202124;margin:40px 0 16px;"
H3_STYLE = "font-size:20px;line-height:1.4;font-weight:600;color:#202124;margin:28px 0 12px;"
QUOTE_STYLE = ("font-size:16px;line-height:1.75;color:#5f6368;margin:0 0 16px;"
               "padding:2px 0 2px 14px;border-left:3px solid #2b5f73;")
STRONG_STYLE = "font-weight:600;color:#202124;"
HL_STYLE = "background:#e9f2f5;padding:0 4px;border-radius:4px;"
IMG_STYLE = "display:block;width:100%;height:auto;border-radius:12px;"
IMG_WRAP = "margin:24px 0;"

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


def pick_icon(title: str, body: str) -> str:
    """标题命中优先（按类别顺序），其次看正文前 2000 字里出现次数最多的类别。大小写敏感，避免 AI 误配 said。"""
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
    border: 0; border-radius: 999px; padding: 12px 20px; cursor: pointer; }"""
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


def inline(text: str) -> str:
    """转义后处理段内标记：**加粗**、==高亮==。"""
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", lambda m: f'<strong style="{STRONG_STYLE}">{m.group(1)}</strong>', s)
    s = re.sub(r"==(.+?)==", lambda m: f'<span style="{HL_STYLE}">{m.group(1)}</span>', s)
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


def parse_body(text: str):
    """返回 [("p"|"h2"|"h3"|"quote"|"img", 值)] 的列表。"""
    blocks = []
    buf = []

    def flush():
        if buf:
            blocks.append(("p", "".join(buf)))
            buf.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.lower().startswith("[img]"):
            flush()
            blocks.append(("img", line[5:].strip()))
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
    return blocks


def render(blocks, body_dir: Path, keep_original: bool):
    parts = []
    n_img = 0
    n_p = 0
    for kind, value in blocks:
        if kind == "img":
            img_path = Path(value)
            if not img_path.is_absolute():
                img_path = (body_dir / img_path).resolve()
            if not img_path.exists():
                sys.exit(f"找不到图片：{img_path}")
            src = encode_image(img_path, keep_original)
            n_img += 1
            parts.append(f'    <div style="{IMG_WRAP}"><img src="{src}" alt="插图{n_img}" style="{IMG_STYLE}"></div>')
        elif kind == "h2":
            parts.append(f'    <h2 style="{H2_STYLE}">{inline(value)}</h2>')
        elif kind == "h3":
            parts.append(f'    <h3 style="{H3_STYLE}">{inline(value)}</h3>')
        elif kind == "quote":
            parts.append(f'    <blockquote style="{QUOTE_STYLE}">{inline(value)}</blockquote>')
            n_p += 1
        else:
            parts.append(f'    <p style="{P_STYLE}">{inline(value)}</p>')
            n_p += 1
    return "\n".join(parts), n_p, n_img


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


def main():
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
                         "education 书本 / article 文章；默认 auto 按标题和正文关键词挑选")
    ap.add_argument("--no-check", action="store_true", help="跳过 Luz-Design 文档检查（仅测试）")
    args = ap.parse_args()

    if args.session:
        session = resolve_session(args.session)
        out = session / f"{session.name}.html"
        body_path = Path(args.body) if args.body else session / "raw" / "04-draft.txt"
    else:
        if not args.body:
            sys.exit("--out 模式需要 --body")
        out = Path(args.out)
        body_path = Path(args.body)
    if not body_path.is_file():
        sys.exit(f"找不到正文：{body_path}")

    text = body_path.read_text(encoding="utf-8-sig")
    body_html, n_p, n_img = render(parse_body(text), body_path.parent, args.keep_original)

    template = Path(args.template).read_text(encoding="utf-8")
    if "{{ICON}}" not in template:
        sys.exit("模板缺少 {{ICON}} 占位符：每个成品网页都必须有标签页图标")
    icon_kind = pick_icon(args.title, text) if args.icon == "auto" else args.icon
    page = (
        template
        .replace("{{ICON}}", icon_link(icon_kind, *template_colors(template)))
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
    print(f"段落 {n_p} 个，图片 {n_img} 张，标签页图标 {icon_kind}，大小 {size_mb:.2f} MB")
    if size_mb > SIZE_WARN_MB:
        print(f"警告：超过 {SIZE_WARN_MB} MB，减少图片或降低质量", file=sys.stderr)
    if not args.no_check:
        run_document_check(out)


if __name__ == "__main__":
    main()
