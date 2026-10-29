#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理 Luz Writing 的输出会话：D:\\Codes\\skill输出\\Luz-Writing\\NNN-主题\\{NNN-主题.html, raw\\}

  py -X utf8 03-session.py new --topic "主题" [--card <类型> …]
  py -X utf8 03-session.py import-crawl "<会话目录>" "<Luz-Crawl begin 返回的任务目录>"
  py -X utf8 03-session.py check "<会话目录>" [--strict]

new 打印新会话的绝对路径，并把规则卡（06-context.py）存进 raw/00-rules/<类型>.md：--card 可重复，
不写时按主题关键词推断，推断不出用 general。读完规则卡再写，并在 raw/01-brief.md 的“采用的规则”逐行
写出本次落实的写作指南小节或偏好 key；结束前用 04-experience.py note 写入或确认至少一条经验，把 key 填进
“本次沉淀”。02-article_builder.py 打包前两栏都会检查。
import-crawl 把 Luz-Crawl 的任务目录（begin "主题" --new 返回的 folder，内有 luz-task.json）整份复制到
raw/05-crawl/ 并登记到 raw/manifest.json；旧版合集（Luz-Crawl 输出根下一层的 NNN_主题 目录）也接受。
check 确认会话根目录只有一个同名 HTML 和 raw/，且有规则卡；已交付成品时“采用的规则”不为空、“本次沉淀”
的 key 都在 experience/notes.json 且确认日期不早于会话创建日（建卡之前的旧会话豁免）；--strict 时
不论是否交付都查这两栏，规则卡过期（写作指南改过）也报错。
--root 只用于测试，正式输出固定写入 OUTPUT_ROOT。
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 经验库（04-experience.py 写入）；模块级变量，测试可替换成临时文件。同目录 git 忽略的 *.local.json 也算。
# LUZ_EXPERIENCE_STORE names another notes file for tests and rehearsals; the skill's own notes and catalog stay untouched.
NOTES_FILE = Path(os.environ.get("LUZ_EXPERIENCE_STORE") or HERE.parent / "experience" / "notes.json")
OUTPUT_ROOT = Path(r"D:\Codes\skill输出\Luz-Writing")
CRAWL_ROOT = Path(r"D:\Codes\skill输出\Luz-Crawl")
SESSION_NAME = re.compile(r"^(\d{3})-.+$")
CRAWL_NAME = re.compile(r"^\d+_.+$")  # 旧版合集：Luz-Crawl 输出根下一层的 NNN_主题
CRAWL_TASK_FILE = "luz-task.json"     # begin 建的任务目录都有它（kind: task_archive）
CRAWL_SUMMARY = "爬取总结.html"        # 任务目录 raw/ 下的汇总页
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
    numbers = [int(m.group(1)) for p in root.iterdir() if p.is_dir() and (m := SESSION_NAME.match(p.name))]
    return max(numbers, default=0) + 1


def load_manifest(session: Path) -> dict:
    path = session / "raw" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def save_manifest(session: Path, data: dict) -> None:
    path = session / "raw" / "manifest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require_session(path: str) -> Path:
    session = Path(path).resolve()
    if not session.is_dir() or not SESSION_NAME.match(session.name) or not (session / "raw").is_dir():
        sys.exit(f"不是有效的 NNN-主题 会话目录：{session}")
    return session


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


def session_errors(session: Path, strict: bool = False) -> list[str]:
    """会话根目录只有同名 HTML 和 raw/；有规则卡；交付了成品时“采用的规则”不为空、“本次沉淀”的经验已写入；
    --strict 时不论是否交付都查这两栏，规则卡也不能过期。"""
    errors: list[str] = []
    expected = {f"{session.name}.html", "raw"}
    entries = {p.name for p in session.iterdir()}
    extra = sorted(entries - expected)
    missing = sorted(expected - entries)
    if extra:
        errors.append(f"会话根目录只能有 {session.name}.html 和 raw/，多出：{', '.join(extra)}")
    if missing:
        errors.append(f"会话缺少：{', '.join(missing)}")
    raw = session / "raw"
    legacy = "rule_cards" not in load_manifest(session) and not (raw / RULES_DIR).is_dir()  # 建卡之前的旧会话
    if not legacy:
        delivered = (session / f"{session.name}.html").is_file()
        errors.extend(rule_card_errors(raw, require_adopted=delivered or strict, check_current=strict))
        if delivered or strict:
            errors.extend(sediment_errors(raw, created_date(session)))
    return errors


def packaging_errors(session: Path) -> list[str]:
    """打包成品前的卡口：当前规则卡、“采用的规则”不为空、“本次沉淀”的经验已写入或确认（旧会话也不豁免）。"""
    raw = session / "raw"
    return [*rule_card_errors(raw, require_adopted=True, check_current=True), *sediment_errors(raw, created_date(session))]


def cmd_new(args) -> None:
    context = load_context()
    kinds = list(dict.fromkeys(args.card)) if args.card else guess_cards(args.topic)
    unknown = [kind for kind in kinds if kind not in context.card_kinds()]
    if unknown:
        sys.exit(f"未知规则卡类型：{', '.join(unknown)}；可选：{', '.join(context.card_kinds())}")
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
        save_manifest(session, {"session": name, "topic": args.topic, "created": now(),
                                "final_html": f"{name}.html", "rule_cards": kinds, "crawl_imports": [], "images": []})
    except Exception:
        shutil.rmtree(session, ignore_errors=True)
        raise
    print(session)
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
    """Luz-Crawl 任务目录（begin 返回的 folder）的 luz-task.json；不是任务目录时返回 None。"""
    try:
        task = json.loads((folder / CRAWL_TASK_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return task if isinstance(task, dict) and task.get("kind") == "task_archive" else None


def crawl_source_errors(folder: Path, allow_any: bool = False) -> list[str]:
    """能导入的来源：Luz-Crawl 任务目录（有 luz-task.json，位置不限），或输出根下一层的旧版 NNN_主题 合集。"""
    if not folder.is_dir():
        return [f"不是目录：{folder}"]
    if crawl_task(folder) is not None or allow_any:
        return []
    if CRAWL_NAME.match(folder.name) and folder.parent == CRAWL_ROOT.resolve():
        return []  # 旧版合集
    return [f"不是 Luz-Crawl 任务目录（缺 {CRAWL_TASK_FILE}）：{folder}。传入 Luz-Crawl `begin \"主题\" --new` 返回的 folder"]


def crawl_summary(folder: Path) -> Path | None:
    """任务目录的 raw/爬取总结.html；旧版合集是同名 HTML。"""
    for candidate in (folder / "raw" / CRAWL_SUMMARY, folder / f"{folder.name}.html"):
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


def cmd_check(args) -> None:
    session = require_session(args.session)
    errors = session_errors(session, strict=args.strict)
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
                            "academic-professional、channel-adaptation、polish-review、fact-check、visual-production、"
                            "general；不写时按主题推断（06-context.py list 看说明）")
    p_new.add_argument("--root", help="测试用输出根目录")
    p_new.set_defaults(func=cmd_new)

    p_imp = sub.add_parser("import-crawl", help="把 Luz-Crawl 任务目录复制到 raw/05-crawl/")
    p_imp.add_argument("session")
    p_imp.add_argument("collection", help="Luz-Crawl `begin \"主题\" --new` 返回的任务目录（folder）；旧版 NNN_主题 合集也可")
    p_imp.add_argument("--allow-any", action="store_true", help="测试用，允许任意目录")
    p_imp.set_defaults(func=cmd_import_crawl)

    p_chk = sub.add_parser("check", help="检查会话根目录结构、规则卡与“采用的规则”")
    p_chk.add_argument("session")
    p_chk.add_argument("--strict", action="store_true", help="规则卡过期（写作指南改过）也报错")
    p_chk.set_defaults(func=cmd_check)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
