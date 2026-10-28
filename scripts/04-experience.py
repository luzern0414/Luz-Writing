#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Luz Writing 经验库：偏好、教训、有效信息。按 key 更新替换，不追加重复条目。

  python -X utf8 04-experience.py search "封面"
  python -X utf8 04-experience.py list [--kind preference]
  python -X utf8 04-experience.py note --kind preference --key 封面风格 --text "…" [--why "…"]
  python -X utf8 04-experience.py prune [--drop-stale]
  python -X utf8 04-experience.py check
  python -X utf8 04-experience.py render

note 按 key 更新：key 已存在时替换原文，旧文只保留一条 previous，uses 加一，刷新
last_confirmed；超出上限时自动裁剪，并重新生成 experience/catalog.md。
check 在重复 key、规范化后相同的文本、超出上限或疑似个人信息时失败。
个人信息只能写进被 git 忽略的 *.local.json（--store 指定），不进公开仓库。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "experience" / "experience.json"
KINDS = {"preference": "偏好", "lesson": "教训", "fact": "有效信息"}
CAPS = {"preference": 60, "lesson": 120, "fact": 120}
STALE_DAYS = 180
KEY_RE = re.compile(r"^[\w一-鿿][\w一-鿿-]{0,39}$")
PRIVATE_PATTERNS = [
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "手机号"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "邮箱"),
    (re.compile(r"(微信号|wxid_|vx[:：])", re.I), "微信号"),
    (re.compile(r"[A-Za-z]:\\Users\\", re.I), "个人目录路径"),
    (re.compile(r"(api[_-]?key|token|password|密码)\s*[:=：]", re.I), "凭据"),
]


def today() -> str:
    return date.today().isoformat()


def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text).lower()


def load(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("entries", [])
    return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["entries"].sort(key=lambda e: (list(KINDS).index(e["kind"]), e["key"]))
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def privacy_hits(text: str) -> list[str]:
    return [label for pattern, label in PRIVATE_PATTERNS if pattern.search(text)]


def upsert(data: dict, kind: str, key: str, text: str, why: str = "", on: str | None = None) -> str:
    """Insert or replace by key. Returns 'added', 'replaced' or 'confirmed'."""
    on = on or today()
    for entry in data["entries"]:
        if entry["key"] != key:
            continue
        entry["uses"] = entry.get("uses", 1) + 1
        entry["last_confirmed"] = on
        if normalize(entry["text"]) == normalize(text) and entry["kind"] == kind:
            if why:
                entry["why"] = why
            return "confirmed"
        entry["previous"] = {"text": entry["text"], "replaced": on}
        entry.update(kind=kind, text=text, why=why or entry.get("why", ""))
        return "replaced"
    data["entries"].append({"kind": kind, "key": key, "text": text, "why": why,
                            "created": on, "last_confirmed": on, "uses": 1})
    return "added"


def _age_days(entry: dict, now: date) -> int:
    return (now - date.fromisoformat(entry["last_confirmed"])).days


def prune(data: dict, drop_stale: bool = False, now: date | None = None) -> list[dict]:
    """Enforce caps; drop least valuable first (lowest uses, then oldest confirmation)."""
    now = now or date.today()
    removed: list[dict] = []
    if drop_stale:
        keep = []
        for e in data["entries"]:
            (removed if _age_days(e, now) > STALE_DAYS and e.get("uses", 1) <= 1 else keep).append(e)
        data["entries"] = keep
    for kind, cap in CAPS.items():
        same = [e for e in data["entries"] if e["kind"] == kind]
        if len(same) <= cap:
            continue
        same.sort(key=lambda e: (e.get("uses", 1), e["last_confirmed"]))
        drop = {id(e) for e in same[: len(same) - cap]}
        removed += [e for e in same if id(e) in drop]
        data["entries"] = [e for e in data["entries"] if id(e) not in drop]
    return removed


def problems(data: dict, check_privacy: bool = True) -> list[str]:
    found: list[str] = []
    keys: dict[str, int] = {}
    texts: dict[str, str] = {}
    counts = {k: 0 for k in KINDS}
    for e in data["entries"]:
        for field in ("kind", "key", "text", "last_confirmed"):
            if not e.get(field):
                found.append(f"条目缺少 {field}：{e.get('key', '?')}")
        if e.get("kind") not in KINDS:
            found.append(f"未知类别 {e.get('kind')}：{e.get('key')}")
            continue
        counts[e["kind"]] += 1
        keys[e["key"]] = keys.get(e["key"], 0) + 1
        norm = normalize(e["text"])
        if norm in texts and texts[norm] != e["key"]:
            found.append(f"内容重复：{texts[norm]} 与 {e['key']}")
        texts.setdefault(norm, e["key"])
        if check_privacy:
            blob = " ".join([e.get("text", ""), e.get("why", ""), json.dumps(e.get("previous", {}), ensure_ascii=False)])
            for label in privacy_hits(blob):
                found.append(f"疑似{label}：{e['key']}")
    found += [f"key 重复：{k}" for k, n in keys.items() if n > 1]
    found += [f"{KINDS[k]}超出上限 {counts[k]}/{CAPS[k]}" for k in KINDS if counts[k] > CAPS[k]]
    return found


def render(data: dict, path: Path) -> None:
    lines = ["# 经验库", "", "由 `scripts/04-experience.py` 自动生成，不要手改。按 key 更新替换；"
             f"上限：偏好 {CAPS['preference']}、教训 {CAPS['lesson']}、有效信息 {CAPS['fact']}。", ""]
    for kind, label in KINDS.items():
        rows = [e for e in data["entries"] if e["kind"] == kind]
        lines += [f"## {label}", ""]
        if not rows:
            lines += ["暂无。", ""]
            continue
        lines += ["| key | 内容 | 依据 | 最近确认 | 次数 |", "| :---: | :---: | :---: | :---: | :---: |"]
        for e in rows:
            cells = [e["key"], e["text"], e.get("why", "") or "—", e["last_confirmed"], str(e.get("uses", 1))]
            lines.append("| " + " | ".join(c.replace("|", "／").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def catalog_for(store: Path) -> Path | None:
    return store.parent / "catalog.md" if store.resolve() == STORE.resolve() else None


def show(entries: list[dict]) -> None:
    for e in entries:
        print(f"[{KINDS[e['kind']]}] {e['key']}：{e['text']}" + (f"（{e['why']}）" if e.get("why") else ""))
    if not entries:
        print("无匹配条目")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Luz Writing 经验库")
    ap.add_argument("--store", default=str(STORE), help="经验库 JSON；个人数据用 *.local.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("note", help="按 key 新增或替换一条经验")
    p.add_argument("--kind", required=True, choices=list(KINDS))
    p.add_argument("--key", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--why", default="")
    p = sub.add_parser("search", help="按关键词检索")
    p.add_argument("query", nargs="+")
    p = sub.add_parser("list", help="列出条目")
    p.add_argument("--kind", choices=list(KINDS))
    p = sub.add_parser("prune", help="按上限裁剪")
    p.add_argument("--drop-stale", action="store_true", help=f"同时删除 {STALE_DAYS} 天未确认且只用过一次的条目")
    sub.add_parser("check", help="检查重复、超限与个人信息")
    sub.add_parser("render", help="重新生成 catalog.md")
    args = ap.parse_args(argv)

    store = Path(args.store)
    local = store.name.endswith(".local.json")
    data = load(store)
    catalog = catalog_for(store)

    if args.cmd == "note":
        key, text = args.key.strip(), " ".join(args.text.split())
        if not KEY_RE.match(key):
            print("FAIL: key 只能用中文、字母、数字、下划线和连字符，最长 40 字", file=sys.stderr)
            return 1
        hits = [] if local else privacy_hits(text + " " + args.why)
        if hits:
            print(f"FAIL: 疑似{'、'.join(hits)}，公开经验库不收个人信息；改写成通用规则或用 *.local.json", file=sys.stderr)
            return 1
        for e in data["entries"]:
            if e["key"] != key and normalize(e["text"]) == normalize(text):
                print(f"FAIL: 与 {e['key']} 内容相同，请用该 key 更新", file=sys.stderr)
                return 1
        result = upsert(data, args.kind, key, text, args.why.strip())
        removed = prune(data)
        save(store, data)
        if catalog:
            render(data, catalog)
        print({"added": "新增", "replaced": "已替换", "confirmed": "已确认"}[result] + f"：{key}")
        for e in removed:
            print(f"超出上限，已移除：{e['key']}")
        return 0
    if args.cmd == "search":
        terms = [normalize(q) for q in args.query]
        hits = [e for e in data["entries"]
                if all(t in normalize(" ".join([e["key"], e["text"], e.get("why", "")])) for t in terms)]
        show(hits)
        return 0
    if args.cmd == "list":
        show([e for e in data["entries"] if not args.kind or e["kind"] == args.kind])
        return 0
    if args.cmd == "prune":
        removed = prune(data, drop_stale=args.drop_stale)
        now = date.today()
        stale = [e["key"] for e in data["entries"] if _age_days(e, now) > STALE_DAYS]
        save(store, data)
        if catalog:
            render(data, catalog)
        print(f"移除 {len(removed)} 条" + (f"；{STALE_DAYS} 天未确认的候选：{'、'.join(stale)}" if stale else ""))
        return 0
    if args.cmd == "render":
        render(data, catalog or store.with_suffix(".md"))
        print("已生成目录")
        return 0
    # check
    found = problems(data, check_privacy=not local)
    if catalog and catalog.is_file():
        expected = catalog.with_suffix(".tmp-check")
        render(data, expected)
        same = expected.read_text(encoding="utf-8") == catalog.read_text(encoding="utf-8")
        expected.unlink()
        if not same:
            found.append("catalog.md 与经验库不同步，运行 render")
    if found:
        for item in found:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    counts = {k: sum(e["kind"] == k for e in data["entries"]) for k in KINDS}
    print("PASS: " + "，".join(f"{KINDS[k]} {counts[k]}/{CAPS[k]}" for k in KINDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
