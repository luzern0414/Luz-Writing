#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate the Luz Writing package and smoke-test its article builder."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REQUIRED_DIRS = ["references", "assets", "scripts", "evals", "experience"]
REQUIRED_ROOT_FILES = ["SKILL.md", "README.md", "NOTICE.md"]
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


def smoke_builder() -> None:
    session_script = str(ROOT / "scripts" / "03-session.py")
    builder = str(ROOT / "scripts" / "02-article_builder.py")
    with tempfile.TemporaryDirectory(prefix="luz-writing-") as td:
        proc = run([session_script, "new", "--topic", "测试主题", "--root", td])
        if proc.returncode != 0:
            fail(f"session new failed: {proc.stderr or proc.stdout}")
        session = Path(proc.stdout.strip())
        if session.name != "001-测试主题" or not (session / "raw" / "manifest.json").is_file():
            fail(f"session layout is wrong: {session}")
        (session / "raw" / "04-draft.txt").write_text(
            "## 发生了什么\n\n开场事实。\n\n**10月26日**，产品上线。\n\n==这句话是关键。==\n\n> 引用的原话。\n",
            encoding="utf-8",
        )
        proc = run([builder, "--title", "测试标题", "--session", str(session)])
        if proc.returncode != 0:
            fail(f"article builder smoke test failed: {proc.stderr or proc.stdout}")
        html = (session / f"{session.name}.html").read_text(encoding="utf-8")
        for marker in ("id=\"copy-area\"", "<strong", "<span", "<h2", "<blockquote"):
            if marker not in html:
                fail(f"article builder output is missing {marker}")
        for leaked_marker in ("**", "==", "{{"):
            if leaked_marker in html:
                fail(f"article builder output contains unrendered marker: {leaked_marker}")
        proc = run([session_script, "check", str(session)])
        if proc.returncode != 0:
            fail(f"session check failed: {proc.stderr or proc.stdout}")


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
    smoke_builder()
    print(f"PASS: {fields['name']} · {len(text.splitlines())} SKILL lines · {link_count} internal links")


if __name__ == "__main__":
    main()
