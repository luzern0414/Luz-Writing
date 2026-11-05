#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理 Luz Writing 的输出会话：D:\\Codes\\skill输出\\Luz-Writing\\NNN-主题\\{NNN-主题.html, raw\\}

  py -X utf8 03-session.py new --topic "主题" [--card <类型> …] [--project <状态根或项目目录>] [--stage <阶段>]
  py -X utf8 03-session.py import-crawl "<会话目录>" "<Luz-Crawl begin 返回的任务目录>"
  py -X utf8 03-session.py summary "<会话目录>" [--title 标题] --deliverable "位置|用途" … [--force]
  py -X utf8 03-session.py check "<会话目录>" [--strict] [--project-linked]

new 打印新会话的绝对路径，并把规则卡（06-context.py）存进 raw/00-rules/<类型>.md：--card 可重复，
不写时按主题关键词推断，推断不出用 general。读完规则卡再写，并在 raw/01-brief.md 的“采用的规则”逐行
写出本次落实的写作指南小节或偏好 key；结束前用 04-experience.py note 写入或确认至少一条经验，把 key 填进
“本次沉淀”。02-article_builder.py 打包前两栏都会检查。
有 Luz-Project 项目上下文（--project，或环境变量 LUZ_PROJECT_ROOT，指项目状态根；给项目目录时按
skill输出\\Luz-Project\\<目录名>\\raw 找状态根，旧项目的项目根自己带 project.json 也行）时，会话记下状态根和成果目录
（project.json 的 deliver_root，旧项目没有就是状态根），之后 check 自动按项目任务检查：根目录只有汇总页和 raw/，
文字成果由 Luz-Project 渲染进项目目录的 docs，本会话不放成品。
import-crawl 把 Luz-Crawl 的任务目录（begin "主题" --new 返回的 folder：<输出根>\\NNN-主题，旧任务是 NNN_主题，爬取的全部内容在其下 raw\\，
任务标记是 raw\\luz-task.json，总结 html 与 raw\\ 同级；旧任务的标记在 luz-task.json）整份复制到
raw/05-crawl/ 并登记到 raw/manifest.json；旧版合集（Luz-Crawl 输出根下一层的 NNN_主题 目录）也接受。
summary 给成品不是 HTML 的会话写汇总页 NNN-主题.html（用 make_summary.py 的版式）：成果（名称、用途、位置）、
依据（简报里采用的规则）、过程文件（raw 下的主要文件和用途）；--deliverable 的“位置”，独立任务是会话根里的文件名，
项目任务是成果目录里的相对路径（docs\\01-需求对接\\01-名称.pdf）。成品本身是 HTML（文章、文案）时，
02-article_builder.py 生成的页面就是汇总页，不用本命令。
check 调用 check_output_layout.py 的 session 检查（目录名、根目录内容、raw 与汇总页、h1 在最前、不禁用缩放），
并确认有规则卡；已交付成品时“采用的规则”不为空、“本次沉淀”的 key 都在 experience/notes.json 且确认日期
不早于会话创建日（建卡之前的旧会话豁免）；--strict 时不论是否交付都查这两栏，规则卡过期（写作指南改过）也报错。
旧会话（序号不是三位加短横线，或建于本布局规范之前）的布局问题只提示不报错。
--root 只用于测试，正式输出固定写入 OUTPUT_ROOT。
"""

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 经验库（04-experience.py 写入）；模块级变量，测试可替换成临时文件。同目录 git 忽略的 *.local.json 也算。
# LUZ_EXPERIENCE_STORE names another notes file for tests and rehearsals; the skill's own notes and catalog stay untouched.
NOTES_FILE = Path(os.environ.get("LUZ_EXPERIENCE_STORE") or HERE.parent / "experience" / "notes.json")
OUTPUT_ROOT = Path(r"D:\Codes\skill输出\Luz-Writing")
CRAWL_ROOT = Path(r"D:\Codes\skill输出\Luz-Crawl")
PROJECT_OUTPUT_ROOT = Path(os.environ.get("LUZ_PROJECT_OUTPUT") or r"D:\Codes\skill输出\Luz-Project")  # 模块级变量，测试可替换
SESSION_NAME = re.compile(r"^(\d{3})-.+$")
LEGACY_SESSION_NAME = re.compile(r"^(\d{2,3})[-_].+$")  # 旧格式：两位序号或下划线；保留原样、仍可读取
LAYOUT_VERSION = 2  # 写进 manifest：会话按“根目录只有 raw 和同名汇总页”的布局规范建立；没有它的是旧会话
CRAWL_NAME = re.compile(r"^\d+[-_].+$")  # Luz-Crawl 输出根下一层的 NNN-主题 或旧版 NNN_主题
CRAWL_TASK_FILE = "luz-task.json"     # begin 建的任务目录都有它（kind: task_archive），在 raw/ 下；旧任务在任务目录根
CRAWL_SUMMARY = "爬取总结.html"        # 旧任务 raw/ 下的汇总页；现在的总结 html 是与 raw/ 同级的 <任务目录名>.html
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# 规则卡（scripts/06-context.py，定义在 references/cards.json）：不写 --card 且主题推断不出时用 general。
DEFAULT_CARD = "general"
RULES_DIR = "00-rules"
BRIEF = "01-brief.md"
RULES_HEADING = "## 采用的规则"
SEDIMENT_HEADING = "## 本次沉淀"
CONTEXT_COMMAND = 'py -X utf8 scripts/06-context.py {kind} --session "<会话目录>"'
NOTE_COMMAND = 'py -X utf8 scripts/04-experience.py note --kind preference|lesson|fact --key {key} --text "<一句话原则>"'

RAW_FILES = {
    BRIEF: (
        "# 简报\n\n## 用户原话\n\n## 交付物\n\n## 读者与渠道\n\n## 约束\n\n"
        f"{RULES_HEADING}\n\n"
        "<!-- 读完 raw/00-rules/ 里的规则卡后逐行填写：写作指南 › 小节（或偏好 key）→ 本次怎么落实。"
        "打包成品前至少一行，02-article_builder.py 会检查。 -->\n\n"
        "| 规则（写作指南 › 小节 或 偏好 key） | 本次怎么落实 |\n| --- | --- |\n\n"
        f"{SEDIMENT_HEADING}\n\n"
        "<!-- 结束前用 py -X utf8 scripts/04-experience.py note 写入或确认经验（同 key 再写即确认），每条一行："
        "用户新偏好、规则纠正、有效的写法与结构、调研来源与范围、生成参数。至少一行；02-article_builder.py 会核对 key "
        "存在于 experience/notes.json 且确认日期不早于本会话创建日。 -->\n\n"
        "| 经验 key | 类型 | 一句话 |\n| --- | --- | --- |\n"
    ),
    # 列与 references/02 的 Claim log 一致；支持状态只用 02 › 声明分级 的五个词。
    "02-claims.md": ("# 声明与来源\n\n<!-- 支持状态：已核验 / 有边界支持 / 尚未解决 / 已反驳 / 不真实（见 references/02 › 声明分级） -->\n\n"
                     "| 声明 | 来源与定位 | 事件日期 | 访问日期 | 支持状态 | 限制与冲突 | 正文口径 |\n"
                     "| --- | --- | --- | --- | --- | --- | --- |\n"),
    "03-outline.md": "# 提纲\n",
    "04-draft.txt": "",
}
RAW_DIRS = ["05-crawl", "06-images"]

_CONTEXT = None
_SIBLINGS: dict[str, object] = {}

# raw 下的主要文件和用途，汇总页“过程文件”一节按实际存在的列出。
RAW_USES = {
    "00-rules": "规则卡", "00-crawl": "前置检索记录与结论页", BRIEF: "简报（用户原话、交付物、采用的规则、本次沉淀）",
    "02-claims.md": "声明与来源", "03-outline.md": "提纲", "04-draft.txt": "正文源", "05-crawl": "Luz-Crawl 任务目录副本",
    "06-images": "图片原图与生成记录", "07-copy-keys.csv": "文案键表源数据", "manifest.json": "会话与导入记录",
    "99-delivery": "交付清单与审批",
}


def load_sibling(name: str, filename: str):
    """同目录的脚本按路径加载（check_output_layout.py、make_summary.py 是七个技能共用的镜像，不带数字前缀）。"""
    if name not in _SIBLINGS:
        spec = importlib.util.spec_from_file_location(name, HERE / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SIBLINGS[name] = module
    return _SIBLINGS[name]


def crawl_errors(session, *, caller="luz-writing", stage=None):
    spec = importlib.util.spec_from_file_location("luz_writing_crawl_gate", HERE / "08-crawl_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.crawl_errors(session, stage=stage, caller=caller)


def load_context():
    """规则卡命令 scripts/06-context.py；文件名带编号，按路径加载。"""
    global _CONTEXT
    if _CONTEXT is None:
        spec = importlib.util.spec_from_file_location("luz_writing_context", HERE / "06-context.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CONTEXT = module
    return _CONTEXT


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_topic(topic: str) -> str:
    name = FORBIDDEN.sub("", topic)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        sys.exit("主题清理后为空")
    return name[:64]


def next_number(root: Path) -> int:
    """输出根内现有最大序号加一（旧格式的会话也算），不补洞、不复用。"""
    numbers = [int(m.group(1)) for p in root.iterdir() if p.is_dir() and (m := LEGACY_SESSION_NAME.match(p.name))]
    return max(numbers, default=0) + 1


def load_manifest(session: Path) -> dict:
    path = session / "raw" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_manifest(session: Path, data: dict) -> None:
    path = session / "raw" / "manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_session(path: str, *, need_raw: bool = True) -> Path:
    """NNN-主题 会话目录；旧格式（两位序号或下划线）的会话仍可读取。need_raw=False 让 check 对缺 raw 的旧会话只提示。"""
    session = Path(path).resolve()
    if not session.is_dir() or not LEGACY_SESSION_NAME.match(session.name) or (need_raw and not (session / "raw").is_dir()):
        sys.exit(f"不是有效的 NNN-主题 会话目录：{session}")
    return session


def project_state_root(path) -> Path | None:
    """给一个路径找项目状态根：该路径下有 project.json 就是状态根（旧项目的项目根也适用）；
    否则当作项目目录，状态根是 skill输出\\Luz-Project\\<目录名>\\raw。找不到返回 None。"""
    path = Path(path).resolve()
    if (path / "project.json").is_file():
        return path
    candidate = PROJECT_OUTPUT_ROOT / path.name / "raw"
    return candidate if (candidate / "project.json").is_file() else None


def project_context(path) -> dict | None:
    """项目状态根、成果目录和检索证据索引。成果目录读 project.json 的 deliver_root，旧项目没有它，成果仍在原项目根（即状态根）；
    证据索引 crawl.evidence_index 相对状态根。"""
    state = project_state_root(path)
    if state is None:
        return None
    try:
        project = json.loads((state / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(project, dict):
        return None
    deliver = Path(project["deliver_root"]) if project.get("deliver_root") else state
    index = (project.get("crawl") or {}).get("evidence_index")
    return {"state_root": str(state), "deliver_root": str(deliver),
            "evidence_index": str(state / index) if isinstance(index, str) and index else None}


def old_layout(session: Path) -> bool:
    """旧会话：序号不是“三位加短横线”，或建于本布局规范之前（manifest 没有 layout_version）。"""
    return not SESSION_NAME.match(session.name) or int(load_manifest(session).get("layout_version") or 0) < LAYOUT_VERSION


def guess_cards(topic: str) -> list[str]:
    """主题里命中关键词最多的那张卡（区分大小写，避免 AI 误配 email；同分取 cards.json 里靠前的）；都不命中用 general。"""
    context = load_context()
    cards = context.load_json(context.CARDS_FILE, {"cards": {}})["cards"]
    scores = {kind: sum(1 for word in card.get("keywords", []) if word and word in topic) for kind, card in cards.items()}
    best = max(scores, key=lambda kind: scores[kind]) if scores else DEFAULT_CARD
    return [best if scores.get(best) else DEFAULT_CARD]


def table_rows(brief_text: str, heading: str) -> list[list[str]] | None:
    """简报某个小节下 Markdown 表格里填了的行；没有这个小节时返回 None。跳过注释、表头和分隔线。"""
    if heading not in brief_text:
        return None
    section = brief_text.split(heading, 1)[1].split("\n## ", 1)[0]
    section = re.sub(r"<!--.*?-->", "", section, flags=re.S)
    lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
    separator = re.compile(r"^\|(\s*:?-{2,}:?\s*\|)+\s*$")
    rows = []
    for i, line in enumerate(lines):
        if separator.match(line) or (i + 1 < len(lines) and separator.match(lines[i + 1])):
            continue  # 分隔线本身，或紧挨在它上面的表头
        cells = [c.strip() for c in line.strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    return rows


def adopted_rules(brief_text: str) -> list[tuple[str, str]] | None:
    """简报“采用的规则”表里填了的行（规则 → 本次怎么落实）；没有这个小节时返回 None。"""
    rows = table_rows(brief_text, RULES_HEADING)
    if rows is None:
        return None
    return [(cells[0], cells[1]) for cells in rows if len(cells) >= 2 and cells[0] and cells[1]]


def experience_notes() -> dict[str, dict]:
    """经验库里的全部条目（notes.json 加同目录 git 忽略的 *.local.json），按 key 索引。"""
    if os.environ.get("LUZ_EXPERIENCE_STORE"):
        print(f"注意：LUZ_EXPERIENCE_STORE 已设置，本次沉淀按 {NOTES_FILE} 核对，经验不会进入技能（只用于测试和演练，正式交付不要设置）", file=sys.stderr)
    notes: dict[str, dict] = {}
    for store in [NOTES_FILE, *sorted(NOTES_FILE.parent.glob("*.local.json"))]:
        try:
            for note in json.loads(store.read_text(encoding="utf-8")).get("notes", []):
                notes.setdefault(note.get("key", ""), note)
        except (OSError, ValueError, AttributeError):
            continue
    return notes


def sediment_errors(raw: Path, since: str) -> list[str]:
    """每次调用都留下经验：简报“本次沉淀”列出的 key 都在经验库里，且确认日期不早于会话创建日（YYYY-MM-DD）。"""
    brief = raw / BRIEF
    rows = table_rows(brief.read_text(encoding="utf-8"), SEDIMENT_HEADING) if brief.is_file() else None
    if rows is None:
        return [f"raw/{BRIEF} 缺少“本次沉淀”小节：加上 `{SEDIMENT_HEADING}` 和表格“| 经验 key | 类型 | 一句话 |”，"
                f"用 `{NOTE_COMMAND.format(key='<主题>')}` 写入或确认至少一条经验后把 key 填进去"]
    keys = [cells[0].strip("` ") for cells in rows if cells and cells[0].strip("` ")]
    if not keys:
        return [f"raw/{BRIEF} 的“本次沉淀”为空：每次调用至少写入或确认一条经验（preference、lesson 或 fact），"
                f"命令 `{NOTE_COMMAND.format(key='<主题>')}`，再把 key 填进表格"]
    notes = experience_notes()
    errors = []
    for key in keys:
        note = notes.get(key)
        if not note:
            errors.append(f"“本次沉淀”的 key「{key}」不在 experience/notes.json：先运行 `{NOTE_COMMAND.format(key=key)}`")
        elif since and str(note.get("last_confirmed", "")) < since:
            errors.append(f"“本次沉淀”的 key「{key}」最近确认于 {note.get('last_confirmed')}，早于本会话创建日 {since}："
                          f"用同一 key 再写一次确认或更新：`{NOTE_COMMAND.format(key=key)}`")
    return errors


def created_date(session: Path) -> str:
    """会话创建日 YYYY-MM-DD（manifest 的 created）。"""
    return str(load_manifest(session).get("created", ""))[:10]


def rule_card_errors(raw: Path, *, require_adopted: bool, check_current: bool) -> list[str]:
    """每个会话都从规则卡开始（06-context.py），并在简报里写明采用了哪些规则。"""
    context = load_context()
    kinds = context.card_kinds()
    cards = sorted(p for p in (raw / RULES_DIR).glob("*.md") if p.stem in kinds)
    errors: list[str] = []
    if not cards:
        errors.append(f"缺少规则卡 raw/{RULES_DIR}/：先运行 `{CONTEXT_COMMAND.format(kind='<类型>')}`"
                      "（类型见 `py -X utf8 scripts/06-context.py list`），读完再写")
    elif check_current:
        for card in cards:
            if not context.card_is_current(card):
                errors.append(f"规则卡 raw/{RULES_DIR}/{card.name} 已过期（写作指南改过）：重新运行 "
                              f"`{CONTEXT_COMMAND.format(kind=card.stem)}`，按新卡复核成稿和“采用的规则”")
    if require_adopted:
        brief = raw / BRIEF
        rows = adopted_rules(brief.read_text(encoding="utf-8")) if brief.is_file() else None
        if rows is None:
            errors.append(f"raw/{BRIEF} 缺少“采用的规则”小节：加上 `{RULES_HEADING}` 和表格"
                          "“| 规则（写作指南 › 小节 或 偏好 key） | 本次怎么落实 |”，逐行填写")
        elif not rows:
            errors.append(f"raw/{BRIEF} 的“采用的规则”为空：读完规则卡后逐行写出本次落实的写作指南小节或偏好 key，以及怎么落实")
    return errors


def listing_errors(session: Path) -> list[str]:
    """没有项目目录的任务，根目录里的成品（PDF、XLSX 等）都要在汇总页里列出。"""
    summary = session / f"{session.name}.html"
    if not summary.is_file():
        return []
    text = html.unescape(summary.read_text(encoding="utf-8", errors="replace"))
    return [f"汇总页没有列出根目录的成品 {item.name}：用 `03-session.py summary` 生成汇总页（成果一节写名称、用途、位置）"
            for item in sorted(session.iterdir()) if item.is_file() and item != summary and item.name not in text]


def layout_report(session: Path, project_linked: bool | None = None) -> tuple[list[str], list[str]]:
    """会话布局检查（check_output_layout.py session）：新会话的问题是错误，旧会话的问题只是提示。
    project_linked 缺省时按 manifest 里有没有项目上下文决定。"""
    if project_linked is None:
        project_linked = bool(load_manifest(session).get("project"))
    errors, notes = load_sibling("luz_writing_output_layout", "check_output_layout.py").check_session(session, project_linked)
    if not project_linked:
        errors = [*errors, *listing_errors(session)]
    if old_layout(session):
        return [], [*notes, *(f"旧会话布局（保留原样，新建会话不要这样）：{e}" for e in errors)]
    return errors, notes


def session_report(session: Path, strict: bool = False, project_linked: bool | None = None) -> tuple[list[str], list[str]]:
    """（错误，提示）。会话根目录只有 raw/ 和同名汇总页（没有项目目录的任务可再有成品文件）；有规则卡；
    交付了成品时“采用的规则”不为空、“本次沉淀”的经验已写入；--strict 时不论是否交付都查这两栏，规则卡也不能过期。"""
    errors, notes = layout_report(session, project_linked)
    raw = session / "raw"
    legacy = "rule_cards" not in load_manifest(session) and not (raw / RULES_DIR).is_dir()  # 建卡之前的旧会话
    if strict or (session / f"{session.name}.html").is_file():
        stage = (load_manifest(session).get("project") or {}).get("stage")
        errors.extend(crawl_errors(session, caller="luz-writing", stage=stage))
    final = session / f"{session.name}.html"
    if final.is_file():
        checker = Path(r"D:\Codes\Luz-Design\scripts\check_document.py")
        if not checker.is_file():
            errors.append(f"文档校验器不存在: {checker}")
        else:
            result = subprocess.run([sys.executable, "-X", "utf8", str(checker), str(final)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if result.returncode:
                errors.extend(f"文档检查: {line}" for line in (result.stdout + result.stderr).splitlines() if line.startswith("ERROR"))
                if not any(e.startswith("文档检查:") for e in errors):
                    errors.append("文档检查未通过: " + (result.stderr or result.stdout).strip())
    if not legacy:
        delivered = (session / f"{session.name}.html").is_file()
        errors.extend(rule_card_errors(raw, require_adopted=delivered or strict, check_current=strict))
        if delivered or strict:
            errors.extend(sediment_errors(raw, created_date(session)))
    return errors, notes


def session_errors(session: Path, strict: bool = False, project_linked: bool | None = None) -> list[str]:
    return session_report(session, strict, project_linked)[0]


def packaging_errors(session: Path) -> list[str]:
    """打包成品前的卡口：当前规则卡、“采用的规则”不为空、“本次沉淀”的经验已写入或确认（旧会话也不豁免）。"""
    raw = session / "raw"
    stage = (load_manifest(session).get("project") or {}).get("stage")
    return [*crawl_errors(session, caller="luz-writing", stage=stage), *rule_card_errors(raw, require_adopted=True, check_current=True),
            *sediment_errors(raw, created_date(session))]


def cmd_new(args) -> None:
    context = load_context()
    kinds = list(dict.fromkeys(args.card)) if args.card else guess_cards(args.topic)
    unknown = [kind for kind in kinds if kind not in context.card_kinds()]
    if unknown:
        sys.exit(f"未知规则卡类型：{', '.join(unknown)}；可选：{', '.join(context.card_kinds())}")
    project = None
    explicit = args.project or None
    given = explicit or os.environ.get("LUZ_PROJECT_ROOT")
    if given:
        project = project_context(given)
        if project is None:
            message = f"找不到项目状态根（没有 project.json）：{given}"
            if explicit:
                sys.exit(message)
            print(f"注意：LUZ_PROJECT_ROOT 无效，按独立任务建会话。{message}", file=sys.stderr)
    if args.stage and project is None:
        sys.exit("--stage 只用于项目任务：同时给 --project（或设置 LUZ_PROJECT_ROOT）")
    if project is not None and args.stage:
        project["stage"] = args.stage
    root = Path(args.root).resolve() if args.root else OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    name = f"{next_number(root):03d}-{safe_topic(args.topic)}"
    session = root / name
    raw = session / "raw"
    raw.mkdir(parents=True)
    try:
        for filename, content in RAW_FILES.items():
            (raw / filename).write_text(content, encoding="utf-8")
        for directory in RAW_DIRS:
            (raw / directory).mkdir()
        # 本次任务的规则、偏好、教训、工具和检查，从写作指南原文切出；读完再写。
        cards = [context.save_card(raw, kind, args.topic.split()) for kind in kinds]
        manifest = {"session": name, "topic": args.topic, "created": now(), "layout_version": LAYOUT_VERSION,
                    "final_html": f"{name}.html", "rule_cards": kinds, "crawl_imports": [], "images": []}
        if project is not None:
            manifest["project"] = project
        save_manifest(session, manifest)
    except Exception:
        shutil.rmtree(session, ignore_errors=True)
        raise
    print(session)
    if project is not None:
        print(f"项目任务：状态根 {project['state_root']}；成果目录 {project['deliver_root']}。文字成果由 Luz-Project 渲染进成果目录的 docs，"
              "本会话只有汇总页和 raw/（用 `03-session.py summary` 写汇总页，check 自动按项目任务检查）。", file=sys.stderr)
    if not args.card:
        print(f"规则卡按主题推断为 {kinds[0]}；类型不对时运行 `{CONTEXT_COMMAND.format(kind='<类型>')}` 补一张"
              "（类型见 06-context.py list）。", file=sys.stderr)
    print("下一步：读完规则卡再写：", file=sys.stderr)
    for card in cards:
        print(f"  {card}", file=sys.stderr)
    print(f"打包前在 raw/{BRIEF} 填“采用的规则”；结束前用 `{NOTE_COMMAND.format(key='<主题>')}` 写入或确认经验，"
          "把 key 填进“本次沉淀”。", file=sys.stderr)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def crawl_task(folder: Path) -> dict | None:
    """Luz-Crawl 任务目录（begin 返回的 folder）的任务标记：先认 raw/luz-task.json，没有再认旧位置 luz-task.json；不是任务目录时返回 None。"""
    for marker in (folder / "raw" / CRAWL_TASK_FILE, folder / CRAWL_TASK_FILE):
        try:
            task = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(task, dict) and task.get("kind") == "task_archive":
            return task
    return None


def crawl_source_errors(folder: Path, allow_any: bool = False) -> list[str]:
    """能导入的来源：Luz-Crawl 任务目录（有 raw/luz-task.json，旧任务是 luz-task.json；位置不限），或输出根下一层的旧版 NNN_主题 合集。"""
    if not folder.is_dir():
        return [f"不是目录：{folder}"]
    if crawl_task(folder) is not None or allow_any:
        return []
    if CRAWL_NAME.match(folder.name) and folder.parent == CRAWL_ROOT.resolve():
        return []  # 旧版合集
    return [f"不是 Luz-Crawl 任务目录（缺 raw/{CRAWL_TASK_FILE}）：{folder}。传入 Luz-Crawl `begin \"主题\" --new` 返回的 folder"]


def crawl_summary(folder: Path) -> Path | None:
    """任务目录的总结 html：与 raw/ 同级的 <任务目录名>.html；旧任务是 raw/爬取总结.html。"""
    for candidate in (folder / f"{folder.name}.html", folder / "raw" / CRAWL_SUMMARY):
        if candidate.is_file():
            return candidate
    return None


def cmd_import_crawl(args) -> None:
    session = require_session(args.session)
    collection = Path(args.collection).resolve()
    errors = crawl_source_errors(collection, args.allow_any)
    if errors:
        sys.exit(errors[0])
    target = session / "raw" / "05-crawl" / collection.name
    if target.exists():
        sys.exit(f"已导入过：{target}")
    shutil.copytree(collection, target, ignore=shutil.ignore_patterns(".collection.lock", "*.lock"))
    summary = crawl_summary(target)
    manifest = load_manifest(session)
    manifest.setdefault("crawl_imports", []).append({
        "collection": str(collection),
        "kind": "task" if crawl_task(collection) is not None else "legacy",
        "copied_to": str(target.relative_to(session)),
        "summary": str(summary.relative_to(session)) if summary else None,
        "summary_sha256": sha256(summary) if summary else None,
        "imported": now(),
    })
    save_manifest(session, manifest)
    print(target)


DOC_LOCATION = re.compile(r"^docs[\\/](01-需求对接|02-产品开发|03-验收交付)[\\/]\d{2}-[^\\/]+$")


def summary_spec(session: Path, title: str, rows: list[list[str]]) -> dict:
    """汇总页的内容：成果（名称、用途、位置）、依据（采用的规则）、过程文件（raw 下的主要文件和用途）；没有内容的节不写。"""
    sections = [{"title": "成果", "table": {"caption": "表 1 成果清单", "columns": ["名称", "用途", "位置"], "rows": rows}}]
    brief = session / "raw" / BRIEF
    adopted = (adopted_rules(brief.read_text(encoding="utf-8")) if brief.is_file() else None) or []
    if adopted:
        sections.append({"title": "依据", "table": {"caption": f"表 {len(sections) + 1} 采用的规则",
                                                    "columns": ["规则", "本次怎么落实"], "rows": [list(pair) for pair in adopted]}})
    raw = session / "raw"

    def used(path: Path) -> bool:  # 建会话时的空骨架（空目录、没填的表头）不算过程文件
        if path.is_dir():
            return any(path.iterdir())
        return path.is_file() and path.read_text(encoding="utf-8", errors="replace") not in ("", RAW_FILES.get(path.name))

    files = [[f"raw\\{name}" + ("\\" if (raw / name).is_dir() else ""), use] for name, use in RAW_USES.items() if used(raw / name)]
    if files:
        sections.append({"title": "过程文件", "table": {"caption": f"表 {len(sections) + 1} raw 下的主要文件",
                                                        "columns": ["文件", "用途"], "rows": files}})
    return {"title": title, "sections": sections}


def cmd_summary(args) -> None:
    session = require_session(args.session)
    manifest = load_manifest(session)
    project = manifest.get("project")
    linked = bool(project) or args.project_linked
    target = session / f"{session.name}.html"
    if target.exists() and not args.force:
        sys.exit(f"已有汇总页 {target.name}（文章、文案类的成品 HTML 本身就是汇总页）；确要用本命令覆盖，加 --force")
    if not args.deliverable:
        sys.exit("至少一个 --deliverable \"位置|用途\"：独立任务写会话根里的文件名，项目任务写成果目录里的相对路径（docs\\01-需求对接\\01-名称.pdf）")
    rows = []
    for item in args.deliverable:
        location, _, purpose = (part.strip() for part in item.partition("|"))
        if not location or not purpose:
            sys.exit(f"--deliverable 要写成“位置|用途”：{item}")
        if linked:
            if not DOC_LOCATION.match(location):
                sys.exit(f"项目任务的成果位置写成果目录里的相对路径，如 docs\\01-需求对接\\01-名称.pdf（docs 下三个目录，文件名 NN-名称）：{location}")
            if project and not (Path(project["deliver_root"]) / location).is_file():
                sys.exit(f"成果目录里没有 {location}（{project['deliver_root']}）：先让 Luz-Project 把成果写进项目目录")
        else:
            if Path(location).name != location or location == target.name or not (session / location).is_file():
                sys.exit(f"会话根里没有成品文件 {location}：独立任务的非 HTML 成品放在会话根，位置写文件名")
        rows.append([re.sub(r"^\d{2,3}-", "", Path(location).stem), purpose, location])
    if not linked:
        listed = {row[2] for row in rows}
        unlisted = [p.name for p in sorted(session.iterdir()) if p.is_file() and p != target and p.name not in listed]
        if unlisted:
            sys.exit(f"会话根里的成品都要列出，还差：{', '.join(unlisted)}")
    spec = summary_spec(session, args.title or manifest.get("topic") or session.name, rows)
    target.write_text(load_sibling("luz_writing_make_summary", "make_summary.py").render(spec), encoding="utf-8")
    print(target)
    errors, notes = layout_report(session, linked)
    for note in notes:
        print(f"提示: {note}")
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        sys.exit(1)


def cmd_check(args) -> None:
    session = require_session(args.session, need_raw=False)
    errors, notes = session_report(session, strict=args.strict, project_linked=True if args.project_linked else None)
    for note in notes:
        print(f"提示: {note}")
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        sys.exit(1)
    print(f"PASS: {session.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="管理 Luz Writing 输出会话")
    sub = ap.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="创建下一个 NNN-主题 会话，并把规则卡存进 raw/00-rules/")
    p_new.add_argument("--topic", required=True)
    p_new.add_argument("--card", action="append",
                       help="规则卡类型，可重复：tech-news、marketing-copy、opinion-explainer、narrative-fiction、"
                            "client-document、academic-professional、channel-adaptation、polish-review、fact-check、"
                            "visual-production、general；不写时按主题推断（06-context.py list 看说明）")
    p_new.add_argument("--root", help="测试用输出根目录")
    p_new.add_argument("--project", help="项目状态根（Luz-Project 会话的 raw 目录）或项目目录；缺省读环境变量 LUZ_PROJECT_ROOT")
    p_new.add_argument("--stage", help="项目阶段（只用于项目任务）；前置检索记录按阶段分开")
    p_new.set_defaults(func=cmd_new)

    p_imp = sub.add_parser("import-crawl", help="把 Luz-Crawl 任务目录复制到 raw/05-crawl/")
    p_imp.add_argument("session")
    p_imp.add_argument("collection", help="Luz-Crawl `begin \"主题\" --new` 返回的任务目录（folder）；旧版 NNN_主题 合集也可")
    p_imp.add_argument("--allow-any", action="store_true", help="测试用，允许任意目录")
    p_imp.set_defaults(func=cmd_import_crawl)

    p_sum = sub.add_parser("summary", help="给非 HTML 成品的会话写汇总页 NNN-主题.html")
    p_sum.add_argument("session")
    p_sum.add_argument("--title", help="汇总页主标题，缺省用会话主题")
    p_sum.add_argument("--deliverable", action="append", default=[],
                       help="成果，写成“位置|用途”，可重复；位置：独立任务是会话根里的文件名，项目任务是成果目录里的 docs\\… 相对路径")
    p_sum.add_argument("--project-linked", action="store_true", help="项目任务（会话没有记下项目上下文时用）：成品在项目目录，会话根不放成品")
    p_sum.add_argument("--force", action="store_true", help="覆盖已有汇总页")
    p_sum.set_defaults(func=cmd_summary)

    p_chk = sub.add_parser("check", help="检查会话布局（check_output_layout）、规则卡与“采用的规则”")
    p_chk.add_argument("session")
    p_chk.add_argument("--strict", action="store_true", help="规则卡过期（写作指南改过）也报错")
    p_chk.add_argument("--project-linked", action="store_true", help="项目任务：成品已写入项目目录，根目录只有汇总页和 raw/")
    p_chk.set_defaults(func=cmd_check)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
