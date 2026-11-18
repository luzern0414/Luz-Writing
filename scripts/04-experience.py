#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Luz Writing 经验库 experience/notes.json：偏好、教训、有效信息，按 key 更新替换。

文件、字段与命令在 Luz-System、Luz-Design、Luz-Dev、Luz-Writing 四个技能中完全一致：
  py -X utf8 scripts/04-experience.py note --kind preference|lesson|fact --key K --text "…" [--why "…"]
                                           [--scope project|maintenance] [--codified "<规范页 › 小节>"]   这三类不印在规则卡上
  py -X utf8 scripts/04-experience.py list [--kind K]
  py -X utf8 scripts/04-experience.py search <关键词> [--kind K]
  py -X utf8 scripts/04-experience.py prune
  py -X utf8 scripts/04-experience.py check
本仓库另有 render（重新生成 experience/catalog.md）和 --store（个人数据只写进被 git 忽略的 *.local.json）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_STORE = ROOT / "experience" / "notes.json"
# LUZ_EXPERIENCE_STORE names another notes file for tests and rehearsals; the skill's own notes and catalog stay untouched.
STORE = Path(os.environ.get("LUZ_EXPERIENCE_STORE") or SKILL_STORE)


# ---------------------------------------------------------------- notes store (identical in Luz-System, Luz-Design, Luz-Dev, Luz-Writing)
# experience/notes.json = {"schema_version": "1.0", "caps": {...}, "notes": [{key, kind, text, why?, uses, first_seen,
# last_confirmed, previous?, scope?, codified?}]}. A note on an existing key replaces its text (one `previous` kept); the same
# statement under another key confirms that note; over a cap the fewest uses, then the oldest confirmation, are dropped.
# scope says where a note applies: absent = every task of this skill; shared/ui/app/web/poster/documents = a Luz-Design
# category; project = one project only (the text names it); maintenance = only when the skill itself is being changed.
# codified names the rule page that now states the note. Project, maintenance and codified notes stay searchable but no rule
# card prints them and they do not use up the caps; Luz-Design keeps the master copy (scripts/sync_rule_core.py).
NOTES_SCHEMA_VERSION = "1.0"
NOTE_KINDS = {"preference": "偏好", "lesson": "教训", "fact": "有效信息"}
NOTE_CAPS = {"preference": 80, "lesson": 120, "fact": 120}
NOTE_FIELDS = ("key", "kind", "text", "why", "uses", "first_seen", "last_confirmed", "previous", "scope", "codified")
NOTE_REQUIRED = ("key", "kind", "text", "uses", "first_seen", "last_confirmed")
NOTE_SCOPES = ("shared", "ui", "app", "web", "poster", "documents", "project", "maintenance")
NOTE_ARCHIVE_SCOPES = ("project", "maintenance")
NOTE_ARCHIVE_CAP = 240
# Explicit user requirements a skill never lets capacity pruning drop; a skill assigns its own set after this block.
PROTECTED_NOTE_KEYS: frozenset = frozenset()
NOTE_STALE_DAYS = 180
NOTE_TEXT_MAX = 400
NOTE_KEY_RE = re.compile(r"[\w一-鿿][\w一-鿿-]{0,47}")
NOTE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
NOTE_PRIVATE_RES = (
    (re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"), "phone number"),
    (re.compile(r"[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?!(?:png|jpe?g|gif|svg|webp)\b)[A-Za-z]{2,}\b"), "email address"),
    (re.compile(r"(?i)\bwxid_\w+|(?:微信号?|wechat(?:\s*id)?|weixin|vx)\s*[:：]\s*[A-Za-z][\w-]{5,}"), "WeChat ID"),
    (re.compile(r"(?i)\b[A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]|(?<![\w.])/(?:Users|home)/\w"), "user-home path"),
    (re.compile(r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\s*[:=：]\s*\S+"
                r"|(?:密码|口令|密钥)\s*[:=：]\s*\S+|\b(?:sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,})"), "credential"),
)


def note_today() -> str:
    return date.today().isoformat()


def note_normalize(text: str) -> str:
    """Comparison form of a statement: NFKC, lower case, without whitespace, punctuation or symbols."""
    return "".join(c for c in unicodedata.normalize("NFKC", str(text or "")).lower()
                   if not c.isspace() and unicodedata.category(c)[0] not in "PS")


def note_private_hits(text: str) -> list[str]:
    return [label for pattern, label in NOTE_PRIVATE_RES if pattern.search(text or "")]


def note_listed(note: dict) -> bool:
    """True when rule cards may print the note: it applies to every task of its category and no rule page states it yet."""
    return note.get("scope") not in NOTE_ARCHIVE_SCOPES and not note.get("codified")


def new_notes_doc() -> dict:
    return {"schema_version": NOTES_SCHEMA_VERSION, "caps": dict(NOTE_CAPS), "notes": []}


def load_notes(path: Path) -> dict:
    if not path.is_file():
        return new_notes_doc()
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("notes"), list):
        raise ValueError(f"{path.name} must be an object with a notes array")
    return doc


def save_notes(path: Path, doc: dict) -> None:
    """Write atomically, notes ordered by kind then key, fields in the shared order."""
    order = list(NOTE_KINDS)
    notes = sorted(doc["notes"], key=lambda n: (order.index(n["kind"]) if n.get("kind") in order else len(order), str(n.get("key", ""))))
    doc.update(schema_version=NOTES_SCHEMA_VERSION, caps=dict(NOTE_CAPS))
    doc["notes"] = [{**{f: n[f] for f in NOTE_FIELDS if n.get(f) not in (None, "")},
                     **{k: v for k, v in n.items() if k not in NOTE_FIELDS}} for n in notes]
    payload = {"schema_version": doc["schema_version"], "caps": doc["caps"], "notes": doc["notes"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def prune_notes(doc: dict, keep: dict | None = None) -> list[dict]:
    """Enforce the caps on the notes the cards print: fewest uses first, then the oldest confirmation; never the note just
    written nor a protected key. Archived notes (project, maintenance, codified) share one cap and go oldest first."""
    removed: list[dict] = []
    for kind, cap in NOTE_CAPS.items():
        group = [n for n in doc["notes"] if n.get("kind") == kind and note_listed(n)]
        overflow = len(group) - cap
        if overflow <= 0:
            continue
        ranked = sorted((n for n in group if n is not keep and n.get("key") not in PROTECTED_NOTE_KEYS),
                        key=lambda n: (int(n.get("uses") or 0), str(n.get("last_confirmed", ""))))
        removed += ranked[:overflow]
    archive = [n for n in doc["notes"] if not note_listed(n)]
    overflow = len(archive) - NOTE_ARCHIVE_CAP
    if overflow > 0:
        ranked = sorted((n for n in archive if n is not keep and n.get("key") not in PROTECTED_NOTE_KEYS),
                        key=lambda n: (str(n.get("last_confirmed", "")), int(n.get("uses") or 0)))
        removed += ranked[:overflow]
    gone = {id(n) for n in removed}
    doc["notes"] = [n for n in doc["notes"] if id(n) not in gone]
    return removed


def upsert_note(doc: dict, kind: str, key: str, text: str, why: str = "", on: str | None = None,
                privacy: bool = True, scope: str | None = None, codified: str | None = None) -> tuple[str, dict, list[dict]]:
    """Insert or replace one note by key. Returns (added|replaced|confirmed, note, pruned notes); raises ValueError.
    scope and codified change only when given: "global" clears the scope, an empty string clears codified."""
    if kind not in NOTE_KINDS:
        raise ValueError(f"--kind must be one of {', '.join(NOTE_KINDS)}")
    key = (key or "").strip()
    if not NOTE_KEY_RE.fullmatch(key):
        raise ValueError("--key must be a short slug: letters, digits, Chinese, - or _, at most 48 characters, no spaces")
    text, why = " ".join((text or "").split()), " ".join((why or "").split())
    if not text:
        raise ValueError("--text is empty")
    if len(text) > NOTE_TEXT_MAX:
        raise ValueError(f"--text is longer than {NOTE_TEXT_MAX} characters; record the general principle, not task details")
    if scope is not None and scope != "global" and scope not in NOTE_SCOPES:
        raise ValueError(f"--scope must be global or one of {', '.join(NOTE_SCOPES)}")
    codified = None if codified is None else " ".join(codified.split())
    if codified and len(codified) > 200:
        raise ValueError("--codified names the rule page and section, at most 200 characters")
    hits = note_private_hits(f"{text} {why} {codified or ''}") if privacy else []
    if hits:
        raise ValueError(f"notes are public; remove the {', '.join(hits)} and write the general principle")
    on = on or note_today()
    notes = doc["notes"]
    norm = note_normalize(text)
    entry = next((n for n in notes if n.get("key") == key), None)
    twin = next((n for n in notes if n is not entry and note_normalize(n.get("text", "")) == norm), None)
    if entry is None and twin is not None:
        entry, action = twin, "confirmed"
        if why and not entry.get("why"):
            entry["why"] = why
    elif entry is None:
        entry, action = {"key": key, "kind": kind, "text": text, "why": why, "uses": 0, "first_seen": on}, "added"
        notes.append(entry)
    elif twin is not None:
        raise ValueError(f"the same statement is stored under {twin['key']}; update that key instead")
    else:
        action = "confirmed"
        if note_normalize(entry.get("text", "")) != norm:
            entry["previous"] = {"text": entry.get("text", ""), "replaced_at": on}
            action = "replaced"
        entry.update(kind=kind, text=text)
        if why:
            entry["why"] = why
    if scope is not None:
        entry.pop("scope", None)
        if scope != "global":
            entry["scope"] = scope
    if codified is not None:
        entry.pop("codified", None)
        if codified:
            entry["codified"] = codified
    entry["uses"] = int(entry.get("uses") or 0) + 1
    entry["last_confirmed"] = on
    return action, entry, prune_notes(doc, keep=entry)


def stale_notes(doc: dict, now: date | None = None) -> list[dict]:
    """Notes not confirmed for NOTE_STALE_DAYS days: listed by prune and check, first to go when a cap is hit."""
    now = now or date.today()
    out = []
    for n in doc["notes"]:
        try:
            age = (now - date.fromisoformat(str(n.get("last_confirmed")))).days
        except ValueError:
            age = NOTE_STALE_DAYS + 1
        if age > NOTE_STALE_DAYS:
            out.append(n)
    return out


def check_notes(doc: dict, privacy: bool = True) -> list[str]:
    """Shape, fields, duplicate keys, duplicate statements, caps and private data."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["notes.json must be a JSON object"]
    if sorted(doc) != ["caps", "notes", "schema_version"]:
        errors.append(f"notes.json top-level fields must be schema_version, caps, notes (found {', '.join(sorted(doc))})")
    if doc.get("schema_version") != NOTES_SCHEMA_VERSION:
        errors.append(f"notes.json schema_version must be {NOTES_SCHEMA_VERSION}")
    if doc.get("caps") != NOTE_CAPS:
        errors.append(f"notes.json caps must be {json.dumps(NOTE_CAPS)}")
    notes = doc.get("notes")
    if not isinstance(notes, list):
        return errors + ["notes.json notes must be an array"]
    keys: dict[str, int] = {}
    texts: dict[str, str] = {}
    for n in notes:
        key = str(n.get("key", "")) if isinstance(n, dict) else ""
        if not isinstance(n, dict):
            errors.append("note is not an object")
            continue
        for field in NOTE_REQUIRED:
            if n.get(field) in (None, ""):
                errors.append(f"note {key or '?'} missing {field}")
        extra = sorted(set(n) - set(NOTE_FIELDS))
        if extra:
            errors.append(f"note {key} has unknown fields {', '.join(extra)}")
        if n.get("kind") not in NOTE_KINDS:
            errors.append(f"note {key} kind must be one of {', '.join(NOTE_KINDS)}")
        if n.get("scope") is not None and n["scope"] not in NOTE_SCOPES:
            errors.append(f"note {key} scope must be one of {', '.join(NOTE_SCOPES)}")
        if n.get("codified") is not None and (not isinstance(n["codified"], str) or not n["codified"].strip() or len(n["codified"]) > 200):
            errors.append(f"note {key} codified must name the rule page in at most 200 characters")
        if key and not NOTE_KEY_RE.fullmatch(key):
            errors.append(f"note key is not a short slug: {key}")
        if not isinstance(n.get("uses"), int) or isinstance(n.get("uses"), bool) or n.get("uses", 0) < 1:
            errors.append(f"note {key} uses must be a positive integer")
        for field in ("first_seen", "last_confirmed"):
            if n.get(field) and not NOTE_DATE_RE.fullmatch(str(n[field])):
                errors.append(f"note {key} {field} must be YYYY-MM-DD")
        previous = n.get("previous")
        if previous is not None and (not isinstance(previous, dict) or sorted(previous) != ["replaced_at", "text"]
                                     or not NOTE_DATE_RE.fullmatch(str(previous.get("replaced_at")))):
            errors.append(f"note {key} previous must be {{text, replaced_at: YYYY-MM-DD}}")
        if len(str(n.get("text", ""))) > NOTE_TEXT_MAX:
            errors.append(f"note {key} text is longer than {NOTE_TEXT_MAX} characters")
        keys[key] = keys.get(key, 0) + 1
        norm = note_normalize(n.get("text", ""))
        if norm and norm in texts and texts[norm] != key:
            errors.append(f"note {key} repeats the statement of {texts[norm]}; keep one key")
        texts.setdefault(norm, key)
        if privacy:
            hits = note_private_hits(f"{n.get('text', '')} {n.get('why', '')} {(previous or {}).get('text', '') if isinstance(previous, dict) else ''}")
            if hits:
                errors.append(f"note {key} contains a {', '.join(hits)}; notes are public")
    errors += [f"duplicate note key {k} ({c} entries); a key is replaced, never repeated" for k, c in keys.items() if c > 1]
    for kind, cap in NOTE_CAPS.items():
        count = sum(1 for n in notes if isinstance(n, dict) and n.get("kind") == kind and note_listed(n))
        if count > cap:
            errors.append(f"{count} {kind} notes exceed the cap {cap}; run prune")
    archived = sum(1 for n in notes if isinstance(n, dict) and not note_listed(n))
    if archived > NOTE_ARCHIVE_CAP:
        errors.append(f"{archived} archived notes (project, maintenance, codified) exceed the cap {NOTE_ARCHIVE_CAP}; run prune")
    return errors


def search_notes(doc: dict, words: list[str], kind: str | None = None) -> list[dict]:
    terms = [t for t in (note_normalize(w) for w in words or []) if t]
    return [n for n in doc["notes"] if (not kind or n.get("kind") == kind)
            and all(t in note_normalize(f"{n.get('key', '')} {n.get('text', '')} {n.get('why', '')}") for t in terms)]


def format_note(n: dict) -> str:
    why = f"（{n['why']}）" if n.get("why") else ""
    marks = "".join(f" [{label}]" for label in (n.get("scope"), "已入规范：" + n["codified"] if n.get("codified") else None) if label)
    return f"[{NOTE_KINDS.get(n.get('kind'), n.get('kind'))}] {n.get('key')}：{n.get('text')}{why}{marks}  （{n.get('uses', 1)} 次，最近 {n.get('last_confirmed')}）"


def note_counts(doc: dict) -> str:
    counts = "，".join(f"{NOTE_KINDS[k]} {sum(1 for n in doc['notes'] if n.get('kind') == k and note_listed(n))}/{cap}" for k, cap in NOTE_CAPS.items())
    return f"{counts}，不上卡 {sum(1 for n in doc['notes'] if not note_listed(n))}/{NOTE_ARCHIVE_CAP}"
# ---------------------------------------------------------------- end of notes store


def render(doc: dict, path: Path) -> None:
    lines = ["# 经验库", "", "由 `scripts/04-experience.py` 根据 `experience/notes.json` 自动生成，不要手改。按 key 更新替换；"
             f"上限：偏好 {NOTE_CAPS['preference']}、教训 {NOTE_CAPS['lesson']}、有效信息 {NOTE_CAPS['fact']}。", ""]
    for kind, label in NOTE_KINDS.items():
        rows = [n for n in doc["notes"] if n.get("kind") == kind]
        lines += [f"## {label}", ""]
        if not rows:
            lines += ["暂无。", ""]
            continue
        # 长文字（内容、依据）左对齐，短值（key、日期、次数）居中。
        lines += ["| key | 内容 | 依据 | 最近确认 | 次数 |", "| :---: | :--- | :--- | :---: | :---: |"]
        for n in rows:
            cells = [n["key"], n["text"], n.get("why", "") or "—", n["last_confirmed"], str(n.get("uses", 1))]
            lines.append("| " + " | ".join(c.replace("|", "／").replace("\n", " ") for c in cells) + " |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def catalog_for(store: Path) -> Path | None:
    return store.parent / "catalog.md" if store.resolve() == SKILL_STORE.resolve() else None


def show(notes: list[dict]) -> None:
    for n in notes:
        print(format_note(n))
    print(f"共 {len(notes)} 条")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Luz Writing 经验库 experience/notes.json")
    ap.add_argument("--store", default=str(STORE), help="经验库 JSON；个人数据用 *.local.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("note", help="按 key 新增或替换一条经验")
    p.add_argument("--kind", required=True, choices=list(NOTE_KINDS))
    p.add_argument("--key", required=True, help="稳定的主题键，例如 封面风格 或 cover-style")
    p.add_argument("--text", required=True, help="一句话通用原则")
    p.add_argument("--why", default="", help="依据或纠正来源")
    p.add_argument("--scope", choices=("global", *NOTE_SCOPES), help="经验的适用范围：global（缺省）每次任务都适用；project 只属于某个项目（正文写明项目）；maintenance 只在维护本技能时用；其余为设计类别")
    p.add_argument("--codified", help="规则已经写进的规范页和小节（之后由规范页给出，规则卡不再重复这条经验）；传空字符串取消")
    p = sub.add_parser("list", help="列出条目")
    p.add_argument("--kind", choices=list(NOTE_KINDS))
    p = sub.add_parser("search", help="按关键词检索，所有词都要命中")
    p.add_argument("words", nargs="*")
    p.add_argument("--kind", choices=list(NOTE_KINDS))
    sub.add_parser("prune", help=f"按上限裁剪，并列出 {NOTE_STALE_DAYS} 天未确认的条目")
    sub.add_parser("check", help="检查结构、重复、上限与个人信息")
    sub.add_parser("render", help="重新生成 catalog.md")
    args = ap.parse_args(argv)

    store = Path(args.store)
    local = store.name.endswith(".local.json")
    catalog = catalog_for(store)
    try:
        doc = load_notes(store)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.cmd == "note":
        try:
            action, entry, removed = upsert_note(doc, args.kind, args.key, args.text, args.why, privacy=not local,
                                                 scope=args.scope, codified=args.codified)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        save_notes(store, doc)
        if catalog:
            render(doc, catalog)
        print(f"{action} {entry['kind']} {entry['key']}：{entry['text']}")
        for n in removed:
            print(f"pruned {n['kind']} {n['key']} (cap {NOTE_CAPS[n['kind']]})")
        return 0
    if args.cmd == "search":
        show(search_notes(doc, args.words, args.kind))
        return 0
    if args.cmd == "list":
        show([n for n in doc["notes"] if not args.kind or n.get("kind") == args.kind])
        return 0
    if args.cmd == "prune":
        removed = prune_notes(doc)
        save_notes(store, doc)
        if catalog:
            render(doc, catalog)
        for n in removed:
            print(f"pruned {n['kind']} {n['key']}")
        stale = stale_notes(doc)
        if stale:
            print(f"not confirmed for {NOTE_STALE_DAYS} days (confirm or replace):", ", ".join(n["key"] for n in stale))
        print(f"pruned {len(removed)} notes")
        return 0
    if args.cmd == "render":
        render(doc, catalog or store.with_suffix(".md"))
        print("已生成目录")
        return 0
    # check
    if not store.is_file():
        print(f"FAIL: {store.name} is missing", file=sys.stderr)
        return 1
    found = check_notes(json.loads(store.read_text(encoding="utf-8")), privacy=not local)
    if catalog and catalog.is_file():
        expected = catalog.with_suffix(".tmp-check")
        render(doc, expected)
        same = expected.read_text(encoding="utf-8") == catalog.read_text(encoding="utf-8")
        expected.unlink()
        if not same:
            found.append("catalog.md 与经验库不同步，运行 render")
    if found:
        for item in found:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1
    stale = stale_notes(doc)
    if stale:
        print(f"UNCONFIRMED over {NOTE_STALE_DAYS} days (first to prune):", ", ".join(n["key"] for n in stale))
    print("PASS: " + note_counts(doc))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
