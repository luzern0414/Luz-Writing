#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""管理 Luz Writing 的输出会话：D:\\Codes\\skill输出\\Luz-Writing\\NNN-主题\\{NNN-主题.html, raw\\}

  python -X utf8 03-session.py new --topic "主题"
  python -X utf8 03-session.py import-crawl "<会话目录>" "D:\\Codes\\skill输出\\Luz-Crawl\\NNN_主题"
  python -X utf8 03-session.py check "<会话目录>"

new 打印新会话的绝对路径。import-crawl 把 Luz-Crawl 合集整份复制到 raw/05-crawl/ 并登记到
raw/manifest.json。check 确认会话根目录只有一个同名 HTML 和 raw/。
--root 只用于测试，正式输出固定写入 OUTPUT_ROOT。
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_ROOT = Path(r"D:\Codes\skill输出\Luz-Writing")
CRAWL_ROOT = Path(r"D:\Codes\skill输出\Luz-Crawl")
SESSION_NAME = re.compile(r"^(\d{3})-.+$")
CRAWL_NAME = re.compile(r"^\d+_.+$")
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

RAW_FILES = {
    "01-brief.md": "# 简报\n\n## 用户原话\n\n## 交付物\n\n## 读者与渠道\n\n## 约束\n",
    "02-claims.md": "# 声明与来源\n\n| 声明 | 来源与定位 | 事件日期 | 访问日期 | 状态 | 限制 |\n| --- | --- | --- | --- | --- | --- |\n",
    "03-outline.md": "# 提纲\n",
    "04-draft.txt": "",
}
RAW_DIRS = ["05-crawl", "06-images"]


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


def cmd_new(args) -> None:
    root = Path(args.root).resolve() if args.root else OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    name = f"{next_number(root):03d}-{safe_topic(args.topic)}"
    session = root / name
    raw = session / "raw"
    raw.mkdir(parents=True)
    for filename, content in RAW_FILES.items():
        (raw / filename).write_text(content, encoding="utf-8")
    for directory in RAW_DIRS:
        (raw / directory).mkdir()
    save_manifest(session, {"session": name, "topic": args.topic, "created": now(),
                            "final_html": f"{name}.html", "crawl_imports": [], "images": []})
    print(session)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cmd_import_crawl(args) -> None:
    session = require_session(args.session)
    if args.latest:
        candidates = [d for d in CRAWL_ROOT.iterdir() if d.is_dir() and CRAWL_NAME.match(d.name)]
        if not candidates:
            sys.exit(f"{CRAWL_ROOT} 下没有合集")
        collection = max(candidates, key=lambda d: int(d.name.split("_", 1)[0])).resolve()
    elif args.collection:
        collection = Path(args.collection).resolve()
    else:
        sys.exit("需要合集目录或 --latest")
    if not collection.is_dir() or not CRAWL_NAME.match(collection.name):
        sys.exit(f"不是 Luz-Crawl 合集目录（NNN_主题）：{collection}")
    if collection.parent != CRAWL_ROOT.resolve() and not args.allow_any:
        sys.exit(f"合集不在 Luz-Crawl 固定根目录 {CRAWL_ROOT} 下")
    target = session / "raw" / "05-crawl" / collection.name
    if target.exists():
        sys.exit(f"已导入过：{target}")
    shutil.copytree(collection, target, ignore=shutil.ignore_patterns(".collection.lock"))
    summary = target / f"{collection.name}.html"
    manifest = load_manifest(session)
    manifest.setdefault("crawl_imports", []).append({
        "collection": str(collection),
        "copied_to": str(target.relative_to(session)),
        "summary_sha256": sha256(summary) if summary.is_file() else None,
        "imported": now(),
    })
    save_manifest(session, manifest)
    print(target)


def cmd_check(args) -> None:
    session = require_session(args.session)
    expected = {f"{session.name}.html", "raw"}
    entries = {p.name for p in session.iterdir()}
    extra = sorted(entries - expected)
    missing = sorted(expected - entries)
    if extra:
        sys.exit(f"会话根目录只能有 {session.name}.html 和 raw/，多出：{', '.join(extra)}")
    if missing:
        sys.exit(f"会话缺少：{', '.join(missing)}")
    print(f"PASS: {session.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="管理 Luz Writing 输出会话")
    sub = ap.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="创建下一个 NNN-主题 会话")
    p_new.add_argument("--topic", required=True)
    p_new.add_argument("--root", help="测试用输出根目录")
    p_new.set_defaults(func=cmd_new)

    p_imp = sub.add_parser("import-crawl", help="把 Luz-Crawl 合集复制到 raw/05-crawl/")
    p_imp.add_argument("session")
    p_imp.add_argument("collection", nargs="?", help="Luz-Crawl 返回的 NNN_主题 合集目录")
    p_imp.add_argument("--latest", action="store_true", help="取 Luz-Crawl 根目录下编号最大的合集")
    p_imp.add_argument("--allow-any", action="store_true", help="测试用，允许固定根目录之外的合集")
    p_imp.set_defaults(func=cmd_import_crawl)

    p_chk = sub.add_parser("check", help="检查会话根目录结构")
    p_chk.add_argument("session")
    p_chk.set_defaults(func=cmd_check)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
