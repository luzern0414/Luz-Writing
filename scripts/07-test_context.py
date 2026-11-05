#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rule cards: every card resolves to the numbered references, carries the user's preferences and the always-on rules,
and a session cannot be packaged without a current card, the 采用的规则 table and a dated 本次沉淀 note."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.append(str(ROOT.parent / "Luz-Crawl/scripts"))
from test_crawl_preflight import complete_fixture


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


context = load("luz_writing_context_test", "06-context.py")
builder = load("luz_writing_builder_test", "02-article_builder.py")
session_mod = builder.load_session_module()  # the same module object the builder uses, so NOTES_FILE can be swapped
NOTES_FILE = session_mod.NOTES_FILE

SECTIONS = ["## 1 用户偏好", "## 2 相关教训与有效做法", "## 3 规则", "## 4 用什么做", "## 5 交付前必须通过", "## 6 收尾"]
TODAY = date.today().isoformat()


def run(*args: str) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if key != "LUZ_PROJECT_ROOT"}  # these sessions are standalone tasks
    return subprocess.run([sys.executable, "-X", "utf8", *args], cwd=ROOT, text=True, capture_output=True, env=env,
                          encoding="utf-8", errors="replace", check=False)


def rules_of(text: str) -> str:
    return text.split("## 3 规则", 1)[1].split("## 4 用什么做", 1)[0]


def fill_brief(raw: Path, rule: str | None = None, note_key: str | None = None) -> None:
    """Fill 采用的规则 and/or 本次沉淀 the way an agent does after reading the card and writing a note."""
    brief = raw / "01-brief.md"
    text = brief.read_text(encoding="utf-8")
    head, tail = text.split("## 本次沉淀", 1)
    if rule:
        head = head.rstrip("\n") + f"\n| {rule} | 按卡落实 |\n\n"
    if note_key:
        tail = tail.rstrip("\n") + f"\n| {note_key} | lesson | 测试会话写入的经验 |\n"
    brief.write_text(head + "## 本次沉淀" + tail, encoding="utf-8")


def build(argv: list[str]) -> tuple[int, str]:
    """Run the article builder in this process (so the swapped NOTES_FILE applies); return exit code and output."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            builder.main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if not isinstance(exc.code, int) and exc.code:
                print(exc.code, file=sys.stderr)
    return code, out.getvalue() + err.getvalue()


class RuleCardTests(unittest.TestCase):
    def tearDown(self) -> None:
        session_mod.NOTES_FILE = NOTES_FILE  # some tests point it at a temporary store

    def test_every_card_resolves_to_reference_sections(self) -> None:
        self.assertEqual(context.check_cards(), [])
        self.assertIn(session_mod.DEFAULT_CARD, context.card_kinds())

    def test_every_card_has_the_six_parts_and_real_rule_text(self) -> None:
        for kind in context.card_kinds():
            text, digest = context.make_card(kind, [])
            for heading in SECTIONS:
                self.assertIn(heading, text, f"{kind}: {heading}")
            self.assertRegex(digest, r"^[0-9a-f]{12}$")
            rules = rules_of(text)
            self.assertNotRegex(rules, r"<(p|td|th|tr|li|ul|div|section|h[1-6])[\s>]", f"{kind}: HTML left in the card")
            size = len(rules.encode("utf-8"))
            self.assertGreaterEqual(size, 8_000, f"{kind}: rule text too short ({size} bytes)")
            self.assertLessEqual(size, 35_000, f"{kind}: rule text too long ({size} bytes); narrow its sections")

    def test_always_on_rules_are_on_every_card(self) -> None:
        for kind in context.card_kinds():
            text, _ = context.make_card(kind, [])
            self.assertIn("### 15 · 只交付要求的文案（全文", text, kind)
            self.assertIn("### 01 · 工作流与写作简报 › 先锁定交付对象", text, kind)
            # Delivering only the requested copy comes first among the rules.
            self.assertLess(text.index("15 · 只交付要求的文案"), text.index("01 · 工作流与写作简报"), kind)

    def test_preferences_are_always_on_the_card(self) -> None:
        notes = context.load_json(context.NOTES_FILE, {"notes": []})["notes"]
        prefs = [n["key"] for n in notes if n["kind"] == "preference"]
        self.assertTrue(prefs)
        for kind in context.card_kinds():
            text, _ = context.make_card(kind, [])
            for key in prefs:
                self.assertIn(f"（{key}）", text, f"{kind}: preference {key}")

    def test_cards_carry_their_own_rules(self) -> None:
        expected = {
            "tech-news": ("数字预算", "事实门", "Luz 资讯声音", "02-article_builder.py", "check_document.py"),
            "marketing-copy": ("三道门槛", "CTA", "合规"),
            "visual-production": ("3D 潮玩", "软陶质感", "imagegen.py", "风格菜单"),
            "polish-review": ("防止矫枉过正", "Gate 8", "五个诊断层级"),
            "academic-professional": ("学术审校", "结构化文档", "翻译腔"),
            "fact-check": ("Claim log", "Gate 2", "Luz-Crawl"),
        }
        for kind, phrases in expected.items():
            text, _ = context.make_card(kind, [])
            for phrase in phrases:
                self.assertIn(phrase, text, f"{kind}: {phrase}")

    def test_markdown_section_ends_at_the_next_heading_of_the_same_level(self) -> None:
        page = ROOT / "references" / "11-quality-gates.md"
        gate = context.section_text(page, ["Gate 2 · 事实与证据"])
        self.assertIn("数字是否有来源", gate)
        self.assertNotIn("改写前后对照", gate)  # first line of Gate 3
        whole = context.section_text(page, ["11 · 质量闸门"])
        self.assertNotIn("# 11 · 质量闸门", whole)  # the whole file through its title, without the title line
        self.assertIn("交付前快速提问", whole)

    def test_command_order_is_not_cut_short(self) -> None:
        # The section must carry every command; headings inside fenced code blocks are skipped by the card cutter.
        steps = context.section_text(ROOT / "references" / "16-output-paths-and-tools.md", ["命令顺序"])
        for phrase in ("06-context.py", "03-session.py new", "import-crawl", "02-article_builder.py", "03-session.py check"):
            self.assertIn(phrase, steps)

    def test_saved_card_records_its_hash_and_goes_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            card = context.save_card(Path(temp), "tech-news")
            self.assertTrue(context.card_is_current(card))
            first, rest = card.read_text(encoding="utf-8").split("\n", 1)
            card.write_text(first.replace(first[first.index(":") + 2:first.index(":") + 14], "000000000000") + "\n" + rest,
                            encoding="utf-8")
            self.assertFalse(context.card_is_current(card))

    def test_card_tells_what_to_sediment(self) -> None:
        text, _ = context.make_card("tech-news", [])
        for phrase in ("本次沉淀", "preference", "lesson", "fact", "调研来源与范围", "同一 key", "04-experience.py note"):
            self.assertIn(phrase, text)

    def test_topic_picks_a_card_or_falls_back_to_general(self) -> None:
        self.assertEqual(session_mod.guess_cards("大模型发布速览"), ["tech-news"])
        self.assertEqual(session_mod.guess_cards("小红书种草文案"), ["marketing-copy"])
        self.assertEqual(session_mod.guess_cards("去 AI 味润色"), ["polish-review"])
        self.assertEqual(session_mod.guess_cards("Email 营销"), ["marketing-copy"])  # "AI" is case-sensitive
        self.assertEqual(session_mod.guess_cards("随便聊聊"), ["general"])

    def test_transaction_copy_and_agreements_pick_their_cards(self) -> None:
        for topic in ("门店停业公告", "优惠券使用规则", "新人礼弹窗文案", "健身房活动规则", "价格说明", "自动续费说明"):
            self.assertEqual(session_mod.guess_cards(topic), ["marketing-copy"], topic)
        for topic in ("小程序隐私政策", "用户服务协议"):
            self.assertEqual(session_mod.guess_cards(topic), ["academic-professional"], topic)
        marketing, _ = context.make_card("marketing-copy", [])
        self.assertIn("前台文字以文案键表交付", marketing)
        academic, _ = context.make_card("academic-professional", [])
        self.assertIn("协议与政策文本", academic)

    def test_client_files_have_their_own_card_and_the_old_routes_still_carry_the_core(self) -> None:
        # Luz-Project still routes the proposal to general and the manual to academic-professional; both keep the shared core.
        for topic in ("方案说明书", "给客户的使用说明", "业务逻辑确认表", "建设方案"):
            self.assertEqual(session_mod.guess_cards(topic), ["client-document"], topic)
        self.assertEqual(session_mod.guess_cards("营销方案"), ["marketing-copy"])
        self.assertEqual(session_mod.guess_cards("用户服务协议"), ["academic-professional"])
        card, _ = context.make_card("client-document", [])
        for phrase in ("先分析", "不提及其他文件", "不写价格", "09-text_check.py", "proposal.json", "业务逻辑确认表", "使用说明"):
            self.assertIn(phrase, card, phrase)
        for kind, phrases in {"general": ("不提及其他文件", "项目背景与需求分析"), "academic-professional": ("不提及其他文件", "入口")}.items():
            text, _ = context.make_card(kind, [])
            for phrase in phrases:
                self.assertIn(phrase, text, f"{kind}: {phrase}")

    def test_chinese_text_checklist_is_on_the_cards_that_write_chinese(self) -> None:
        for kind in ("client-document", "general", "academic-professional", "marketing-copy", "opinion-explainer",
                     "narrative-fiction", "channel-adaptation"):
            text, _ = context.make_card(kind, [])
            self.assertIn("GB/T 15834", text, kind)
            self.assertTrue("GB/T 15835" in text or "数值范围" in text, kind)

    def test_no_reference_presents_gb_t_7714_2015_as_current(self) -> None:
        # GB/T 7714—2025 replaced the 2015 edition on 2026-07-01 (openstd.samr.gov.cn).
        pages = [*(ROOT / "references").glob("*.md"), ROOT / "SKILL.md", ROOT / "README.md"]
        for page in pages:
            for line in page.read_text(encoding="utf-8").splitlines():
                if re.search(r"7714\s*[—-]\s*2015", line):
                    self.assertTrue(re.search(r"代替|废止|2015 版", line), f"{page.name}: {line[:60]}")

    def test_client_file_rules_agree_with_each_other(self) -> None:
        # 18 is the one home of the client-file rules: no price in the proposal, no pointer to other files, no placeholders.
        text = (ROOT / "references" / "18-client-documents.md").read_text(encoding="utf-8")
        for phrase in ("不提及其他文件", "不写价格", "先分析客户的需求，再给方案", "标题不手打序号", "第三方费用由客户承担"):
            self.assertIn(phrase, text)
        for stale in ("客户信息收集表", "信息收集表"):
            self.assertNotIn(stale, text)
        structure = (ROOT / "references" / "09-academic-and-professional.md").read_text(encoding="utf-8")
        self.assertIn("客户方案不用这条结构", structure)

    def test_one_status_vocabulary_and_one_gap_marker(self) -> None:
        # 02 › 声明分级 is the only set of claim states; [待核实：…] the only visible gap.
        texts = [p.read_text(encoding="utf-8") for p in (ROOT / "references").glob("*.md")]
        texts += [(ROOT / "SKILL.md").read_text(encoding="utf-8"), (ROOT / "references" / "cards.json").read_text(encoding="utf-8")]
        for text in texts:
            for stale in ("[NEED:", "[待核对]", "已验证/部分", "已验证 / 部分支持"):
                self.assertNotIn(stale, text)
        claims = session_mod.RAW_FILES["02-claims.md"]
        self.assertIn("| 声明 | 来源与定位 | 事件日期 | 访问日期 | 支持状态 | 限制与冲突 | 正文口径 |", claims)


class GateTests(unittest.TestCase):
    def tearDown(self) -> None:
        session_mod.NOTES_FILE = NOTES_FILE

    def test_adopted_rules_ignore_header_separator_and_comment(self) -> None:
        brief = "# 简报\n\n## 采用的规则\n\n<!-- | 示例 | 示例 | -->\n\n| 规则（写作指南 › 小节 或 偏好 key） | 本次怎么落实 |\n| --- | --- |\n"
        self.assertEqual(session_mod.adopted_rules(brief), [])
        self.assertEqual(session_mod.adopted_rules(brief + "| 语气 | 口语化 |\n"), [("语气", "口语化")])
        self.assertIsNone(session_mod.adopted_rules("# 简报\n"))
        self.assertEqual(session_mod.adopted_rules(brief + "\n## 本次沉淀\n\n| a | lesson | b |\n"), [])

    def test_session_without_card_or_adopted_rules_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp)
            (raw / "01-brief.md").write_text("# 简报\n\n## 采用的规则\n\n| 规则 | 落实 |\n| --- | --- |\n", encoding="utf-8")
            errors = session_mod.rule_card_errors(raw, require_adopted=True, check_current=True)
            self.assertTrue(any("00-rules" in e and "06-context.py" in e for e in errors))
            self.assertTrue(any("“采用的规则”为空" in e for e in errors))
            context.save_card(raw, "polish-review")
            (raw / "01-brief.md").write_text("# 简报\n\n## 采用的规则\n\n| 语气 | 口语化 |\n", encoding="utf-8")
            self.assertEqual(session_mod.rule_card_errors(raw, require_adopted=True, check_current=True), [])
            card = raw / "00-rules" / "polish-review.md"
            card.write_text(card.read_text(encoding="utf-8").replace("rules-sha256: ", "rules-sha256: 0", 1), encoding="utf-8")
            self.assertTrue(any("已过期" in e for e in session_mod.rule_card_errors(raw, require_adopted=True, check_current=True)))

    def test_every_session_leaves_a_dated_note_behind(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp)
            notes = raw / "notes.json"
            notes.write_text(json.dumps({"notes": [
                {"key": "fresh", "kind": "fact", "text": "有效做法", "last_confirmed": "2026-10-29"},
                {"key": "old", "kind": "lesson", "text": "旧教训", "last_confirmed": "2026-10-01"},
            ]}, ensure_ascii=False), encoding="utf-8")
            (raw / "personal.local.json").write_text(json.dumps({"notes": [
                {"key": "local", "kind": "preference", "text": "个人偏好", "last_confirmed": "2026-10-29"},
            ]}, ensure_ascii=False), encoding="utf-8")
            session_mod.NOTES_FILE = notes
            (raw / "01-brief.md").write_text("# 简报\n", encoding="utf-8")
            self.assertIn("缺少“本次沉淀”", session_mod.sediment_errors(raw, "2026-10-29")[0])
            base = "# 简报\n\n## 本次沉淀\n\n<!-- | x | fact | 注释不算 | -->\n\n| 经验 key | 类型 | 一句话 |\n| --- | --- | --- |\n"
            (raw / "01-brief.md").write_text(base, encoding="utf-8")
            self.assertIn("“本次沉淀”为空", session_mod.sediment_errors(raw, "2026-10-29")[0])
            (raw / "01-brief.md").write_text(base + "| missing | fact | 不存在 |\n", encoding="utf-8")
            self.assertIn("不在 experience/notes.json", session_mod.sediment_errors(raw, "2026-10-29")[0])
            (raw / "01-brief.md").write_text(base + "| old | lesson | 旧教训 |\n", encoding="utf-8")
            self.assertIn("早于本会话创建日", session_mod.sediment_errors(raw, "2026-10-29")[0])
            (raw / "01-brief.md").write_text(base + "| fresh | fact | 有效做法 |\n| `local` | preference | 个人偏好 |\n", encoding="utf-8")
            self.assertEqual(session_mod.sediment_errors(raw, "2026-10-29"), [])

    def test_out_cannot_write_into_the_output_root(self) -> None:
        self.assertTrue(builder.inside_output_root(builder.OUTPUT_ROOT / "001-主题" / "001-主题.html"))
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(builder.inside_output_root(Path(temp) / "测试.html"))

    def test_templates_are_marked_as_skeletons_and_the_note_is_stripped(self) -> None:
        for name in ("01-article-template.html", "03-visual-production-brief.md"):
            head = (ROOT / "assets" / name).read_text(encoding="utf-8").splitlines()[:4]
            self.assertTrue(any("06-context.py" in line for line in head), name)
        template = (ROOT / "assets" / "01-article-template.html").read_text(encoding="utf-8")
        stripped = builder.TEMPLATE_NOTE.sub("", template)
        self.assertNotIn("06-context.py", stripped)
        self.assertTrue(stripped.startswith("<!doctype html>\n<html"))

    def test_legacy_session_is_exempt_from_check_but_not_from_packaging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            session = Path(temp) / "001-旧会话"
            (session / "raw").mkdir(parents=True)
            (session / "raw" / "manifest.json").write_text(json.dumps({"session": session.name, "created": "2026-10-01T09:00:00+08:00"}), encoding="utf-8")
            (session / "raw" / "01-brief.md").write_text("# 简报\n", encoding="utf-8")
            (session / f"{session.name}.html").write_text("<!doctype html>", encoding="utf-8")
            self.assertTrue(any("Crawl" in e for e in session_mod.session_errors(session)))
            errors = session_mod.packaging_errors(session)
            self.assertTrue(any("00-rules" in e for e in errors))
            self.assertTrue(any("本次沉淀" in e for e in errors))

    def test_session_flow_refuses_packaging_until_rules_and_sediment_are_filled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = run(str(HERE / "03-session.py"), "new", "--topic", "测试 稿件", "--root", str(root / "out"), "--card", "nope")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("未知规则卡类型", proc.stderr)
            self.assertFalse((root / "out" / "001-测试 稿件").exists())

            proc = run(str(HERE / "03-session.py"), "new", "--topic", "测试 稿件", "--root", str(root / "out"),
                       "--card", "polish-review", "--card", "fact-check")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            session = Path(proc.stdout.strip())
            raw = session / "raw"
            self.assertEqual(sorted(p.name for p in (raw / "00-rules").glob("*.md")), ["fact-check.md", "polish-review.md"])
            self.assertEqual(json.loads((raw / "manifest.json").read_text(encoding="utf-8"))["rule_cards"], ["polish-review", "fact-check"])
            brief = (raw / "01-brief.md").read_text(encoding="utf-8")
            self.assertLess(brief.index("## 采用的规则"), brief.index("## 本次沉淀"))
            self.assertIn("polish-review.md", proc.stderr)
            (raw / "04-draft.txt").write_text("## 发生了什么\n\n开场事实。\n", encoding="utf-8")

            notes = root / "notes.json"
            session_mod.NOTES_FILE = notes
            argv = ["--title", "测试标题", "--session", str(session), "--no-check"]
            code, out = build(argv)
            self.assertNotEqual(code, 0)
            self.assertIn("“采用的规则”为空", out)
            self.assertIn("“本次沉淀”", out)
            self.assertIn("06-context.py", out)  # the card hint on stderr
            self.assertFalse((session / f"{session.name}.html").exists())

            fill_brief(raw, rule="15 · 只交付要求的文案 › 自检")
            code, out = build(argv)
            self.assertNotEqual(code, 0)
            self.assertIn("“本次沉淀”为空", out)

            proc = run(str(HERE / "04-experience.py"), "--store", str(notes), "note", "--kind", "lesson",
                       "--key", "test-session-note", "--text", "测试会话写入的经验")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            fill_brief(raw, note_key="test-session-note")
            # A real task also needs the separately completed research contract.
            self.assertTrue(any("Crawl" in e for e in session_mod.packaging_errors(session)))
            complete_fixture(session, "luz-writing")
            code, out = build(argv)
            self.assertEqual(code, 0, out)
            page = (session / f"{session.name}.html").read_text(encoding="utf-8")
            self.assertNotIn("06-context.py", page)  # the template's skeleton note stays out of the deliverable
            self.assertEqual(session_mod.session_errors(session, strict=True), [])

            invalid_template = root / "invalid-template.html"
            template = builder.TEMPLATE.read_text(encoding="utf-8")
            invalid_template.write_text(template.replace("</head>", "<style>h1 {font-size:10px}</style></head>"), encoding="utf-8")
            code, out = build([*argv, "--template", str(invalid_template)])
            self.assertNotEqual(code, 0, "--no-check must not bypass final-session document checks")
            self.assertTrue(any("font size below" in e for e in session_mod.session_errors(session, strict=True)))
            code, out = build(argv)
            self.assertEqual(code, 0, out)

            # A rule page edited after the card was saved makes the card stale: packaging is refused again.
            card = raw / "00-rules" / "fact-check.md"
            card.write_text(card.read_text(encoding="utf-8").replace("rules-sha256: ", "rules-sha256: 0", 1), encoding="utf-8")
            self.assertTrue(any("已过期" in e for e in session_mod.packaging_errors(session)))
            self.assertTrue(any("已过期" in e for e in session_mod.session_errors(session, strict=True)))
            self.assertEqual(session_mod.session_errors(session), [])



class CrawlImportTests(unittest.TestCase):
    """import-crawl takes the task folder that Luz-Crawl `begin "主题" --new` returns (it holds raw/luz-task.json; older tasks luz-task.json)."""

    def new_session(self, root: Path) -> Path:
        proc = run(str(HERE / "03-session.py"), "new", "--topic", "导入测试", "--root", str(root / "out"), "--card", "general")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(proc.stdout.strip())

    def test_task_folder_from_begin_is_imported_with_its_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.new_session(root)
            task = root / "Luz-Crawl" / "085-AI 资讯"  # <output root>/NNN-主题: raw/ holds everything crawled, the summary html sits beside it
            (task / "raw" / "0001_页面").mkdir(parents=True)
            (task / "raw" / "luz-task.json").write_text(json.dumps({"schema_version": 1, "kind": "task_archive",
                                                                    "delivery_layout": "task_folder_v2", "title": "AI 资讯"}), encoding="utf-8")
            (task / "085-AI 资讯.html").write_text("<!doctype html><title>汇总</title>", encoding="utf-8")
            (task / "raw" / "search-1.json").write_text("{}", encoding="utf-8")
            (task / "raw" / "0001_页面" / "content.json").write_text("{}", encoding="utf-8")
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(task))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            copied = session / "raw" / "05-crawl" / task.name
            self.assertTrue((copied / "085-AI 资讯.html").is_file())
            self.assertTrue((copied / "raw" / "0001_页面" / "content.json").is_file())
            entry = json.loads((session / "raw" / "manifest.json").read_text(encoding="utf-8"))["crawl_imports"][0]
            self.assertEqual(entry["kind"], "task")
            self.assertTrue(entry["summary"].endswith("085-AI 资讯.html"))
            self.assertRegex(entry["summary_sha256"], r"^[0-9a-f]{64}$")
            again = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(task))
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("已导入过", again.stderr)

    def test_older_task_folder_is_still_imported_with_its_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.new_session(root)
            task = root / "Luz-Crawl" / "raw" / "031_AI 资讯"  # <output root>/<category>/raw/NNN_需求, as Luz-Crawl once laid it out
            (task / "raw").mkdir(parents=True)
            (task / "luz-task.json").write_text(json.dumps({"schema_version": 1, "kind": "task_archive",
                                                            "delivery_layout": "sibling_raw_v1", "title": "AI 资讯"}), encoding="utf-8")
            (task / "raw" / "爬取总结.html").write_text("<!doctype html><title>汇总</title>", encoding="utf-8")
            (task / "search-1.json").write_text("{}", encoding="utf-8")
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(task))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            copied = session / "raw" / "05-crawl" / task.name
            self.assertTrue((copied / "raw" / "爬取总结.html").is_file())
            entry = json.loads((session / "raw" / "manifest.json").read_text(encoding="utf-8"))["crawl_imports"][0]
            self.assertEqual(entry["kind"], "task")
            self.assertTrue(entry["summary"].endswith("爬取总结.html"))
            self.assertRegex(entry["summary_sha256"], r"^[0-9a-f]{64}$")
            again = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(task))
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("已导入过", again.stderr)

    def test_collection_names_accept_dash_and_underscore(self) -> None:
        # Luz-Crawl's task folders are NNN-主题 now, NNN_主题 before; a bare collection under its output root may carry either.
        with tempfile.TemporaryDirectory() as temp:
            crawl_root = Path(temp) / "Luz-Crawl"
            names = ("012-新格式合集", "013_旧格式合集")
            for name in names:
                (crawl_root / name).mkdir(parents=True)
            original = session_mod.CRAWL_ROOT
            session_mod.CRAWL_ROOT = crawl_root
            try:
                for name in names:
                    self.assertEqual(session_mod.crawl_source_errors((crawl_root / name).resolve()), [], name)
                (Path(temp) / "014-不在输出根下").mkdir()
                self.assertTrue(session_mod.crawl_source_errors((Path(temp) / "014-不在输出根下").resolve()))
            finally:
                session_mod.CRAWL_ROOT = original

    def test_folders_that_are_not_crawl_tasks_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.new_session(root)
            stray = root / "012-随便一个目录"  # an NNN-主题 name alone is not enough outside the Luz-Crawl output root
            stray.mkdir()
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(stray))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("luz-task.json", proc.stderr)
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session))
            self.assertNotEqual(proc.returncode, 0)  # the folder is required; --latest is gone


summary_mod = session_mod.load_sibling("luz_writing_make_summary_test", "make_summary.py")


class OutputLayoutTests(unittest.TestCase):
    """The session is NNN-主题 with raw/ and a same-named summary page; old sessions get hints, never errors."""

    def tearDown(self) -> None:
        session_mod.PROJECT_OUTPUT_ROOT = PROJECT_OUTPUT_ROOT

    def new_session(self, root: Path, topic: str = "门店活动文案键表", *extra: str) -> Path:
        proc = run(str(HERE / "03-session.py"), "new", "--topic", topic, "--root", str(root), "--card", "marketing-copy", *extra)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(proc.stdout.strip())

    def test_new_session_is_numbered_with_a_dash_and_marks_the_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "007_旧下划线会话").mkdir()
            (root / "12-旧两位序号").mkdir()
            session = self.new_session(root)
            self.assertEqual(session.name, "013-门店活动文案键表")  # the largest number counts, old formats included; no gaps filled
            self.assertEqual(sorted(p.name for p in session.iterdir()), ["raw"])
            manifest = json.loads((session / "raw" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["layout_version"], session_mod.LAYOUT_VERSION)
            self.assertNotIn("project", manifest)
            errors, notes = session_mod.layout_report(session)
            self.assertEqual(len(errors), 1)  # only the summary page is still missing
            self.assertIn("汇总页", errors[0])

    def test_article_page_is_the_summary_page_and_passes_the_layout_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            session = self.new_session(Path(temp), "科技资讯")
            body = session / "raw" / "04-draft.txt"
            body.write_text("## 发生了什么\n\n开场事实。\n\n| 键 | 文案 |\n| --- | --- |\n| a | 一句话 |\n", encoding="utf-8")
            page = session / f"{session.name}.html"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                builder.main(["--title", "科技资讯", "--body", str(body), "--out", str(page), "--no-check"])
            self.assertEqual(session_mod.layout_report(session), ([], []))
            text = page.read_text(encoding="utf-8")
            self.assertTrue(text.index("<h1>") < text.index("<h2>"))
            self.assertRegex(text, r'<html lang="zh-CN"')
            self.assertNotRegex(text, r"(?i)user-scalable|maximum-scale")
            self.assertIn('rel="icon"', text)
            proc = run(str(HERE / "check_output_layout.py"), "session", str(session))
            self.assertEqual(proc.returncode, 0, proc.stdout)
            # The article page and the generated summary page carry the same md-type block.
            block = re.search(r"/\* luz-md-type:start.*?/\* luz-md-type:end \*/", text, flags=re.S).group(0)
            self.assertEqual(block, summary_mod.MD_TYPE)

    def test_non_html_deliverable_sits_in_the_root_and_the_summary_page_lists_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            session = self.new_session(Path(temp))
            (session / "raw" / "07-copy-keys.csv").write_text("键,文案\na,一句话\n", encoding="utf-8")
            sheet = session / f"{session.name}.xlsx"
            sheet.write_bytes(b"PK")
            errors, _ = session_mod.layout_report(session)
            self.assertTrue(any("汇总页" in e for e in errors))  # no summary page yet
            proc = run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", f"{sheet.name}|后台录入和开发种子")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            page = (session / f"{session.name}.html").read_text(encoding="utf-8")
            self.assertEqual(session_mod.layout_report(session), ([], []))
            self.assertEqual(run(str(HERE / "check_output_layout.py"), "session", str(session)).returncode, 0)
            self.assertEqual(len(re.findall(r"<h1\b", page)), 1)
            self.assertLess(page.index("<h1>"), page.index("<h2>"))
            self.assertIn("<h2>成果</h2>", page)
            self.assertIn(sheet.name, page)
            self.assertIn("后台录入和开发种子", page)
            self.assertIn("raw\\07-copy-keys.csv", page)  # a process file that exists is listed ...
            self.assertNotIn("raw\\03-outline.md", page)  # ... the untouched skeletons are not
            self.assertNotIn("<h2>依据</h2>", page)  # nothing adopted yet, so no section
            self.assertEqual(page.count("<caption>"), page.count("<h2>"))  # every section has one captioned table
            self.assertEqual(run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", f"{sheet.name}|x").returncode, 1)  # no silent overwrite
            self.assertEqual(run(str(HERE / "03-session.py"), "summary", str(session), "--force", "--deliverable", f"{sheet.name}|x").returncode, 0)

    def test_summary_page_refuses_unlisted_or_missing_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            session = self.new_session(Path(temp))
            (session / "a.pdf").write_bytes(b"%PDF")
            (session / "b.docx").write_bytes(b"PK")
            proc = run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", "a.pdf|协议")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("b.docx", proc.stderr)  # every deliverable in the root is listed
            proc = run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", "c.pdf|协议")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("c.pdf", proc.stderr)
            self.assertEqual(run(str(HERE / "03-session.py"), "summary", str(session)).returncode, 1)  # at least one deliverable
            self.assertFalse((session / f"{session.name}.html").exists())
            # An article page that leaves a root file unlisted fails the session layout check.
            (session / f"{session.name}.html").write_text(
                '<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
                "<body><h1>标题</h1></body></html>", encoding="utf-8")
            errors, _ = session_mod.layout_report(session)
            self.assertTrue(any("a.pdf" in e for e in errors) and any("b.docx" in e for e in errors))

    def test_page_rules_h1_first_and_zoom_not_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            session = self.new_session(Path(temp))
            page = session / f"{session.name}.html"
            page.write_text('<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width, user-scalable=no">'
                            "</head><body><h2>先写了二级标题</h2><h1>标题</h1></body></html>", encoding="utf-8")
            errors, _ = session_mod.layout_report(session)
            self.assertTrue(any("h1" in e for e in errors))
            self.assertTrue(any("缩放" in e for e in errors))

    def test_old_sessions_only_get_hints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            underscore = root / "012_旧会话"  # old number format, no summary page, a stray file in the root
            (underscore / "raw").mkdir(parents=True)
            (underscore / "notes.txt").write_text("x", encoding="utf-8")
            two_digit = root / "05-旧会话"
            two_digit.mkdir()
            no_marker = root / "006-建会话时还没有布局标记"  # three digits and a dash, but created before the layout rule
            (no_marker / "raw").mkdir(parents=True)
            (no_marker / "raw" / "manifest.json").write_text(json.dumps({"session": no_marker.name, "created": "2026-10-30T09:00:00+08:00"}), encoding="utf-8")
            (no_marker / "stray").mkdir()
            for old in (underscore, two_digit, no_marker):
                errors, notes = session_mod.session_report(old)
                self.assertEqual(errors, [], f"{old.name}: {errors}")
                self.assertTrue(notes, old.name)
                proc = run(str(HERE / "03-session.py"), "check", str(old))
                self.assertEqual(proc.returncode, 0, f"{old.name}: {proc.stderr}")
                self.assertIn("提示", proc.stdout)
                self.assertTrue(session_mod.old_layout(old))
            # The same defects in a new session are errors.
            fresh = self.new_session(root, "新会话")
            (fresh / "stray").mkdir()
            errors, _ = session_mod.layout_report(fresh)
            self.assertTrue(any("stray" in e for e in errors))
            proc = run(str(HERE / "03-session.py"), "check", str(fresh))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("stray", proc.stderr)
            self.assertFalse(session_mod.old_layout(fresh))

    def write_project(self, base: Path, *, with_deliver_root: bool = True) -> dict[str, Path]:
        """A project the way Luz-Project lays it out: state root = the Luz-Project session's raw/, results in the project directory."""
        state = base / "skill输出" / "Luz-Project" / "014-示例项目" / "raw"
        deliver = base / "014-示例项目"
        (state / "00-crawl").mkdir(parents=True)
        (deliver / "docs" / "01-需求对接").mkdir(parents=True)
        (deliver / "docs" / "01-需求对接" / "01-需求说明书.pdf").write_bytes(b"%PDF")
        project = {"name": "示例项目", "crawl": {"evidence_index": "00-crawl/evidence-index.json"}}
        if with_deliver_root:
            project["deliver_root"] = str(deliver)
        (state / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
        return {"state": state, "deliver": deliver, "output": base / "skill输出" / "Luz-Project"}

    def test_project_context_reads_state_root_deliver_root_and_evidence_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(Path(temp))
            context_by_state = session_mod.project_context(paths["state"])
            self.assertEqual(context_by_state["state_root"], str(paths["state"].resolve()))
            self.assertEqual(context_by_state["deliver_root"], str(paths["deliver"]))
            self.assertEqual(context_by_state["evidence_index"], str(paths["state"].resolve() / "00-crawl/evidence-index.json"))
            # A project directory resolves to the state root under the Luz-Project output root.
            session_mod.PROJECT_OUTPUT_ROOT = paths["output"]
            self.assertEqual(session_mod.project_context(paths["deliver"]), context_by_state)
            self.assertIsNone(session_mod.project_context(Path(temp) / "没有这个项目"))

    def test_old_project_without_deliver_root_keeps_working(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            old_root = Path(temp) / "012-旧项目"  # old layout: project.json sits in the project root, results beside it
            old_root.mkdir()
            (old_root / "project.json").write_text(json.dumps({"name": "旧项目"}), encoding="utf-8")
            found = session_mod.project_context(old_root)
            self.assertEqual(found["state_root"], str(old_root.resolve()))
            self.assertEqual(found["deliver_root"], str(old_root.resolve()))
            self.assertIsNone(found["evidence_index"])

    def test_project_task_session_holds_only_the_summary_page_and_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = self.write_project(Path(temp))
            out = Path(temp) / "out"
            proc = run(str(HERE / "03-session.py"), "new", "--topic", "需求说明书文字", "--root", str(out), "--card", "client-document",
                       "--project", str(paths["state"]), "--stage", "requirements")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            session = Path(proc.stdout.strip())
            self.assertIn("项目任务", proc.stderr)
            manifest = json.loads((session / "raw" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["project"]["deliver_root"], str(paths["deliver"]))
            self.assertEqual(manifest["project"]["stage"], "requirements")
            location = "docs\\01-需求对接\\01-需求说明书.pdf"
            for bad in ("01-需求说明书.pdf", "docs\\01-需求对接\\需求说明书.pdf", "docs\\04-其他\\01-a.pdf"):
                self.assertEqual(run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", f"{bad}|需求说明书").returncode, 1, bad)
            missing = run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", "docs\\01-需求对接\\02-不存在.pdf|方案")
            self.assertEqual(missing.returncode, 1)
            self.assertIn("成果目录里没有", missing.stderr)
            proc = run(str(HERE / "03-session.py"), "summary", str(session), "--deliverable", f"{location}|需求说明书")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            page = (session / f"{session.name}.html").read_text(encoding="utf-8")
            self.assertIn(location, page)  # the location is the project-relative path
            self.assertIn("<td class=\"left\">需求说明书</td>", page)
            self.assertEqual(sorted(p.name for p in session.iterdir()), [f"{session.name}.html", "raw"])
            self.assertEqual(session_mod.layout_report(session), ([], []))
            self.assertEqual(run(str(HERE / "check_output_layout.py"), "session", str(session), "--project-linked").returncode, 0)
            # The deliverable is not duplicated into the session: a stray copy fails the project-linked check.
            (session / "02-另一份协议.pdf").write_bytes(b"%PDF")
            errors, _ = session_mod.layout_report(session)
            self.assertTrue(any("项目目录" in e for e in errors))
            self.assertTrue(any("项目目录" in e for e in session_mod.layout_report(session, True)[0]))
            self.assertTrue(any("没有列出" in e for e in session_mod.layout_report(session, False)[0]))  # a standalone task must list it

    def test_unusable_project_given_to_new(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            proc = run(str(HERE / "03-session.py"), "new", "--topic", "测试", "--root", str(out), "--card", "general", "--project", str(Path(temp) / "没有"))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("project.json", proc.stderr)
            proc = run(str(HERE / "03-session.py"), "new", "--topic", "测试", "--root", str(out), "--card", "general", "--stage", "proposal")
            self.assertEqual(proc.returncode, 1)
            self.assertIn("--stage", proc.stderr)


PROJECT_OUTPUT_ROOT = session_mod.PROJECT_OUTPUT_ROOT


class BuilderLayoutTests(unittest.TestCase):
    """The builder follows the Luz-Design reading-page values and the body format in references/16."""

    def build_page(self, title: str, body_text: str, image: bool = False) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "04-draft.txt"
            if image:
                (Path(tmp) / "06-images").mkdir()
                (Path(tmp) / "06-images" / "a.png").write_bytes(base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
            body.write_text(body_text, encoding="utf-8")
            out = Path(tmp) / "page.html"
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                builder.main(["--title", title, "--body", str(body), "--out", str(out), "--no-check", "--keep-original"])
            return out.read_text(encoding="utf-8"), err.getvalue()

    def test_image_line_carries_alt_text_and_caption(self) -> None:
        page, err = self.build_page("随笔", "[img] 06-images/a.png | 一只猫趴在窗台上 | 午后的窗台\n\n正文。\n", image=True)
        self.assertIn('alt="一只猫趴在窗台上"', page)
        self.assertIn("<figcaption", page)
        self.assertIn("午后的窗台", page)
        self.assertNotIn("替代文本", err)
        page, err = self.build_page("随笔", "[img] 06-images/a.png\n\n正文。\n", image=True)
        self.assertIn("替代文本", err)  # a missing alt text is warned about

    def test_pipe_lines_become_an_aligned_table(self) -> None:
        body = ("| 键 | 页面与位置 | 文案 | 字数上限 | 价格 |\n| --- | --- | --- | --- | --- |\n"
                "| home.popup_title | 首页 › 新人礼弹窗标题 | 新人礼已到账，去看看能用在哪些饮品上 | 8 | ¥32 |\n")
        page, _ = self.build_page("文案键表", body)
        self.assertIn("<table", page)
        self.assertEqual(page.count("<th "), 5)
        self.assertIn("text-align:left;", page)    # long copy
        self.assertIn("text-align:center;", page)  # short values and headers
        self.assertIn("text-align:right;", page)   # money

    def test_one_radius_and_heavy_titles_follow_luz_design(self) -> None:
        page, _ = self.build_page("随笔", "## 小标题\n\n**加粗** 与 ==高亮==。\n")
        # The Markdown type block is a verbatim copy of Luz-Design's master and carries its own code radius; the article has no code.
        outside = re.sub(r"/\* luz-md-type:start.*?/\* luz-md-type:end \*/", "", page, flags=re.S)
        radii = set(re.findall(r"border-radius:\s*(\d+px)", outside))
        self.assertEqual(radii, {builder.RADIUS})
        self.assertRegex(page, r"h1 \{[^}]*font-weight: 700")
        self.assertRegex(page, r"h2 \{[^}]*font-size: var\(--md-h2\)[^}]*font-weight: 700")

    def test_page_text_sizes_come_from_the_markdown_block_not_from_inline_styles(self) -> None:
        body = "## 小标题\n\n正文一段。\n\n### 三级\n\n> 引用的原话。\n\n| 键 | 文案 |\n| --- | --- |\n| a | 一句话 |\n"
        page, _ = self.build_page("随笔", body)
        template = builder.TEMPLATE.read_text(encoding="utf-8")
        block = re.search(r"/\* luz-md-type:start.*?/\* luz-md-type:end \*/", page, flags=re.S)
        self.assertIsNotNone(block)
        self.assertEqual(block.group(0), re.search(r"/\* luz-md-type:start.*?/\* luz-md-type:end \*/", template, flags=re.S).group(0))
        self.assertIn("--md-body: 16px", block.group(0))
        self.assertIn("--md-body: 18px", block.group(0))
        # Phone first, desktop from 768: the page breakpoint is the block's, so a 768 px window gets the desktop set.
        self.assertIn("@media (max-width: 767px)", page)
        outside = page.replace(block.group(0), "")
        self.assertNotRegex(outside, r"font-size:\s*\d+px;\s*line-height", "the template sets no body size of its own")
        self.assertNotRegex(outside, r"(?m)^\s*(h1|h2|h3)\s*\{")
        for tag in ("p", "h2", "h3", "blockquote"):
            self.assertRegex(page, rf"<{tag}>")
        self.assertNotRegex(page, r"<(p|h2|h3|blockquote|figcaption|table)\b[^>]*font-size")
        self.assertIn("#copy-area blockquote { border-left-color: var(--accent); }", page)

    def test_copy_button_pastes_the_phone_set_inline_and_leaves_the_page_alone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.txt"
            body.write_text("## 小标题\n\n正文。\n\n> 引用。\n", encoding="utf-8")
            out = Path(tmp) / "page.html"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                builder.main(["--title", "随笔", "--body", str(body), "--out", str(out), "--no-check", "--copy-button"])
            page = out.read_text(encoding="utf-8")
        script = page.split("<script>", 1)[1]
        for expected in ("font-size:16px;line-height:1.75", "font-size:24px;line-height:1.3;font-weight:700", "font-size:20px;line-height:1.4;font-weight:600", "font-size:14px;line-height:1.5"):
            self.assertIn(expected, script)
        self.assertIn("pasteHTML()", script)
        self.assertNotIn("__PASTE_STYLES__", page)
        self.assertNotRegex(page.split("<script>", 1)[0], r"<(p|h2|h3|blockquote)\b[^>]*font-size")

    def test_icon_follows_the_theme(self) -> None:
        self.assertEqual(builder.pick_icon("一套提示词模板火了", "", "ai-agent"), "tech")
        self.assertEqual(builder.pick_icon("周末随笔", "", "coffee"), "food")
        self.assertEqual(builder.pick_icon("城市旅行攻略", "", "template"), "travel")


class ThemeTests(unittest.TestCase):
    """The page takes its main colour from the Luz-Design industry themes, not from the template's neutral default."""

    def setUp(self) -> None:
        self.themes = builder.load_themes()
        if not self.themes:
            self.skipTest(f"no themes at {builder.THEMES_FILE}")

    def test_title_and_body_pick_an_industry_theme(self) -> None:
        self.assertEqual(builder.pick_theme("健身新手第一周", "", self.themes), "fitness-gym")
        self.assertEqual(builder.pick_theme("大模型周报", "", self.themes), "ai-agent")
        self.assertEqual(builder.pick_theme("周末随笔", "今天去宠物店给狗狗洗澡，宠物店的人很多。", self.themes), "pet")

    def test_no_industry_falls_back_to_the_template_colours(self) -> None:
        self.assertEqual(builder.pick_theme("一季度财报解读", "利润和现金流。", self.themes), "template")
        self.assertEqual(builder.pick_theme("随笔", "提到一次咖啡。", self.themes), "template")  # one passing mention is not a topic

    def test_theme_recolours_quote_highlight_and_icon(self) -> None:
        theme = self.themes["fitness-gym"]
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.txt"
            body.write_text("## 第一步\n\n**热身** 后再上==器械==。\n\n> 教练说：别急。\n", encoding="utf-8")
            out = Path(tmp) / "page.html"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                builder.main(["--title", "健身新手第一周", "--body", str(body), "--out", str(out)])
            page = out.read_text(encoding="utf-8")
        self.assertIn(f"--accent: {theme['action']}", page)
        self.assertIn("#copy-area blockquote { border-left-color: var(--accent); }", page)
        self.assertIn(f"background:{theme['actionTint']}", page)
        self.assertNotIn("#2b5f73", page.lower())
        self.assertNotIn("#e9f2f5", page.lower())

    def test_unknown_theme_is_refused_with_the_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.txt"
            body.write_text("正文。\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                builder.main(["--title", "随笔", "--body", str(body), "--out", str(Path(tmp) / "p.html"), "--theme", "nope"])
        self.assertIn("fitness-gym", str(raised.exception))


class ExperienceStoreOverrideTests(unittest.TestCase):
    """LUZ_EXPERIENCE_STORE (tests and rehearsals only) takes note writes and feeds the rule card; the skill's own files stay untouched."""

    def test_override_store_takes_writes_and_feeds_the_card(self) -> None:
        import os
        import subprocess
        skill_root = Path(__file__).resolve().parents[1]
        experience = {p: p.read_bytes() for p in (skill_root / "experience").iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "notes.json"
            env = {**os.environ, "LUZ_EXPERIENCE_STORE": str(store)}

            def run(*args: str) -> subprocess.CompletedProcess:
                return subprocess.run([sys.executable, "-X", "utf8", *args], cwd=skill_root, env=env, text=True,
                                      capture_output=True, encoding="utf-8", errors="replace", check=False)

            noted = run("scripts/04-experience.py", "note", "--kind", "preference", "--key", "override-probe", "--text", "探针偏好，只写测试库")
            self.assertEqual(noted.returncode, 0, noted.stderr)
            self.assertTrue(store.is_file())
            card = run("scripts/06-context.py", "tech-news")
            self.assertEqual(card.returncode, 0, card.stderr)
            self.assertIn("探针偏好", card.stdout)
        self.assertEqual({p: p.read_bytes() for p in (skill_root / "experience").iterdir() if p.is_file()}, experience)


if __name__ == "__main__":
    unittest.main()
