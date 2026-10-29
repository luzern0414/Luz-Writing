#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the Luz Writing package, its rule cards and invocation protocol, and smoke-test the session gates."""

from __future__ import annotations

import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REQUIRED_DIRS = ["references", "assets", "scripts", "evals", "experience"]
REQUIRED_ROOT_FILES = ["SKILL.md", "README.md", "NOTICE.md"]
REQUIRED_FILES = ["scripts/06-context.py", "scripts/07-test_context.py", "references/cards.json"]
# Templates are skeletons; each says so in its first lines and points to the rule card.
SKELETON_TEMPLATES = ["assets/01-article-template.html", "assets/03-visual-production-brief.md"]
# The shared rule-card core is identical in every Luz skill; Luz-Design holds the reference copy.
CORE_REFERENCE = Path(r"D:\Codes\Luz-Design\scripts\context.py")
CORE_START = b"# ---- shared rule-card core"
CORE_END = b"# ---- end of shared rule-card core"
# .git is version-control metadata of the repository, not packaged content.
FORBIDDEN_ROOT_ENTRIES = [".research", "__pycache__", "working", "raw", "outputs"]
REQUIRED_REFERENCES = [f"{i:02d}-" for i in range(1, 18)]
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        fail("SKILL.md is missing YAML frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    if set(("name", "description")) - fields.keys():
        fail("frontmatter must contain name and description")
    if not re.fullmatch(r"[a-z0-9-]+", fields["name"]):
        fail("skill name must contain only lowercase letters, digits, and hyphens")
    if len(fields["description"]) > 1024:
        fail("description exceeds 1024 characters")
    return fields


def check_links() -> int:
    checked = 0
    markdown_files = sorted(ROOT.rglob("*.md"))
    for md in markdown_files:
        text = md.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.strip().split("#", 1)[0]
            if not target or target.startswith(SKIP_LINK_PREFIXES):
                continue
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                fail(f"broken link in {md.relative_to(ROOT)}: {target}")
            checked += 1
    return checked


def check_layout() -> None:
    for filename in REQUIRED_ROOT_FILES:
        if not (ROOT / filename).is_file():
            fail(f"missing root file: {filename}")
    for entry in FORBIDDEN_ROOT_ENTRIES:
        if (ROOT / entry).exists():
            fail(f"development-only entry must not be packaged: {entry}")
    for directory in REQUIRED_DIRS:
        if not (ROOT / directory).is_dir():
            fail(f"missing directory: {directory}")
    refs = sorted(p.name for p in (ROOT / "references").glob("*.md"))
    for prefix in REQUIRED_REFERENCES:
        if not any(name.startswith(prefix) for name in refs):
            fail(f"missing numbered reference {prefix}")
    for path in sorted((ROOT / "references").glob("*.md")):
        if not re.match(r"^\d{2}-", path.name):
            fail(f"reference is not numbered: {path.name}")
    for directory in ("assets", "examples", "scripts"):
        for path in sorted((ROOT / directory).iterdir()):
            if path.is_file() and not re.match(r"^\d{2}-", path.name):
                fail(f"{directory} file is not numbered: {path.name}")


def check_evals() -> None:
    data = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
    if data.get("skill_name") != "luz-writing":
        fail("evals.json skill_name must be luz-writing")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 6:
        fail("evals.json needs at least six regression cases")
    for item in evals:
        for key in ("id", "prompt", "expected_output", "assertions"):
            if key not in item:
                fail(f"eval {item.get('id', '?')} is missing {key}")
        if not item["prompt"].strip() or not item["expected_output"].strip():
            fail(f"eval {item['id']} has empty prompt or expected output")


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-X", "utf8", *args], cwd=ROOT, text=True,
                          capture_output=True, encoding="utf-8", errors="replace", check=False)


def load_script(name: str, filename: str):
    """Numbered scripts cannot be imported by name; load them by path."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def smoke_builder() -> None:
    session_script = str(ROOT / "scripts" / "03-session.py")
    builder = str(ROOT / "scripts" / "02-article_builder.py")
    with tempfile.TemporaryDirectory(prefix="luz-writing-") as td:
        proc = run([session_script, "new", "--topic", "测试主题", "--root", td])
        if proc.returncode != 0:
            fail(f"session new failed: {proc.stderr or proc.stdout}")
        session = Path(proc.stdout.strip())
        raw = session / "raw"
        if session.name != "001-测试主题" or not (raw / "manifest.json").is_file():
            fail(f"session layout is wrong: {session}")
        if not list((raw / "00-rules").glob("*.md")):
            fail("session new did not save a rule card to raw/00-rules/")
        (raw / "04-draft.txt").write_text(
            "## 发生了什么\n\n开场事实。\n\n**10月26日**，产品上线。\n\n==这句话是关键。==\n\n> 引用的原话。\n",
            encoding="utf-8",
        )
        # The gate: a brief without 采用的规则 and 本次沉淀 is refused and nothing is written.
        proc = run([builder, "--title", "测试标题", "--session", str(session)])
        if proc.returncode == 0 or "采用的规则" not in proc.stderr or "本次沉淀" not in proc.stderr:
            fail("article builder packaged a session whose 采用的规则 and 本次沉淀 are empty")
        if (session / f"{session.name}.html").exists():
            fail("a refused build still wrote the final HTML")
        # Fill both tables the way an agent does; the note goes to a temporary store, the real library stays untouched.
        store = Path(td) / "notes.json"
        proc = run([str(ROOT / "scripts" / "04-experience.py"), "--store", str(store), "note", "--kind", "lesson",
                    "--key", "smoke-test-note", "--text", "自检会话写入的经验"])
        if proc.returncode != 0:
            fail(f"experience note into a temporary store failed: {proc.stderr or proc.stdout}")
        brief = raw / "01-brief.md"
        head, tail = brief.read_text(encoding="utf-8").split("## 本次沉淀", 1)
        brief.write_text(head.rstrip("\n") + "\n| 15 · 只交付要求的文案 › 自检 | 页面只有标题和正文 |\n\n## 本次沉淀"
                         + tail.rstrip("\n") + "\n| smoke-test-note | lesson | 自检会话写入的经验 |\n", encoding="utf-8")
        builder_module = load_script("luz_writing_builder_smoke", "02-article_builder.py")
        session_module = builder_module.load_session_module()
        session_module.NOTES_FILE = store
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                builder_module.main(["--title", "测试标题", "--session", str(session)])
        except SystemExit as exc:
            if exc.code:
                fail(f"article builder smoke test failed: {exc.code}\n{err.getvalue() or out.getvalue()}")
        html = (session / f"{session.name}.html").read_text(encoding="utf-8")
        for marker in ("id=\"copy-area\"", "<strong", "<span", "<h2", "<blockquote"):
            if marker not in html:
                fail(f"article builder output is missing {marker}")
        for leaked_marker in ("**", "==", "{{", "06-context.py"):
            if leaked_marker in html:
                fail(f"article builder output contains unrendered marker: {leaked_marker}")
        errors = session_module.session_errors(session, strict=True)
        if errors:
            fail("session check failed: " + "; ".join(errors))


def check_rule_cards(text: str) -> None:
    """Rule cards resolve, the shared core matches Luz-Design, and SKILL.md opens with the invocation protocol."""
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}")
    try:
        json.loads((ROOT / "references" / "cards.json").read_text(encoding="utf-8"))
    except ValueError as exc:
        fail(f"references/cards.json is not valid JSON: {exc}")
    # Every card resolves to existing reference headings, so renaming a heading cannot silently empty a card.
    context = load_script("luz_writing_context_validate", "06-context.py")
    errors = context.check_cards()
    if errors:
        fail("rule cards: " + "; ".join(errors))
    if "general" not in context.card_kinds():
        fail("references/cards.json needs the card general (the session default)")
    mine = (ROOT / "scripts" / "06-context.py").read_bytes()
    if CORE_START not in mine or CORE_END not in mine:
        fail("scripts/06-context.py lost the shared rule-card core markers")
    if CORE_REFERENCE.is_file():
        def core(data: bytes) -> bytes:
            start = data.index(CORE_START)
            end = data.index(b"\n", data.index(CORE_END)) + 1
            return data[start:end].replace(b"\r\n", b"\n")
        if core(mine) != core(CORE_REFERENCE.read_bytes()):
            fail(f"scripts/06-context.py shared core differs from {CORE_REFERENCE}; copy it byte for byte")

    normalized = text.replace("\r\n", "\n")
    sections = re.findall(r"(?m)^## (.+)$", normalized)
    if not sections or not sections[0].startswith("调用协议"):
        fail("SKILL.md must open with the section 调用协议 (invocation protocol) before any other section")
    if len(sections) < 2 or sections[1] != "Deliver only the requested copy":
        fail("SKILL.md must keep 'Deliver only the requested copy' right after 调用协议")
    protocol = normalized.split("\n## ", 2)[1]
    for phrase in ("scripts/06-context.py", "采用的规则", "本次沉淀", "04-experience.py note"):
        if phrase not in protocol:
            fail(f"SKILL.md 调用协议 must mention {phrase}")
    # Agents choose skills from the parsed frontmatter; an unquoted ": " inside the description breaks it silently.
    front = normalized.split("---", 2)[1]
    try:
        import yaml
        parsed = yaml.safe_load(front)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("description"), str):
            fail("SKILL.md frontmatter does not parse to a name and a description string")
        description = parsed["description"]
    except ImportError:
        description = (re.search(r"(?m)^description: (.+)$", front) or [None, ""])[1]
        if ": " in description:
            fail("SKILL.md description contains ': ' which breaks YAML; use a dash instead")
    except Exception as exc:  # yaml.YAMLError
        fail(f"SKILL.md frontmatter is not valid YAML: {exc}")
    if "context.py" not in description:
        fail("SKILL.md description must tell agents to start with scripts/06-context.py")
    if len(description) > 1024:
        fail("SKILL.md description exceeds 1024 characters")
    for rel in SKELETON_TEMPLATES:
        head = (ROOT / rel).read_text(encoding="utf-8").splitlines()[:4]
        if not any("06-context.py" in line for line in head):
            fail(f"{rel} must say at the top that it is a skeleton and point to scripts/06-context.py")
    proc = run([str(ROOT / "scripts" / "07-test_context.py")])
    if proc.returncode != 0:
        fail(f"rule card tests failed: {proc.stderr or proc.stdout}")


def check_experience() -> None:
    proc = run([str(ROOT / "scripts" / "04-experience.py"), "check"])
    if proc.returncode != 0:
        fail(f"experience store check failed: {proc.stderr or proc.stdout}")
    proc = run([str(ROOT / "scripts" / "05-test_experience.py")])
    if proc.returncode != 0:
        fail(f"experience unit tests failed: {proc.stderr or proc.stdout}")


def main() -> None:
    check_layout()
    check_experience()
    text = SKILL.read_text(encoding="utf-8")
    fields = check_frontmatter(text)
    if len(text.splitlines()) > 500:
        fail("SKILL.md exceeds 500 lines")
    link_count = check_links()
    check_evals()
    check_rule_cards(text)
    smoke_builder()
    print(f"PASS: {fields['name']} · {len(text.splitlines())} SKILL lines · {link_count} internal links")


if __name__ == "__main__":
    main()
