#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rule cards: every card resolves to the numbered references, carries the user's preferences and the always-on rules,
and a session cannot be packaged without a current card, the 采用的规则 table and a dated 本次沉淀 note."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
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
    return subprocess.run([sys.executable, "-X", "utf8", *args], cwd=ROOT, text=True, capture_output=True,
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
            self.assertEqual(session_mod.session_errors(session), [])
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
            code, out = build(argv)
            self.assertEqual(code, 0, out)
            page = (session / f"{session.name}.html").read_text(encoding="utf-8")
            self.assertNotIn("06-context.py", page)  # the template's skeleton note stays out of the deliverable
            self.assertEqual(session_mod.session_errors(session, strict=True), [])

            # A rule page edited after the card was saved makes the card stale: packaging is refused again.
            card = raw / "00-rules" / "fact-check.md"
            card.write_text(card.read_text(encoding="utf-8").replace("rules-sha256: ", "rules-sha256: 0", 1), encoding="utf-8")
            self.assertTrue(any("已过期" in e for e in session_mod.packaging_errors(session)))
            self.assertTrue(any("已过期" in e for e in session_mod.session_errors(session, strict=True)))
            self.assertEqual(session_mod.session_errors(session), [])



class CrawlImportTests(unittest.TestCase):
    """import-crawl takes the task folder that Luz-Crawl `begin "主题" --new` returns (it holds luz-task.json)."""

    def new_session(self, root: Path) -> Path:
        proc = run(str(HERE / "03-session.py"), "new", "--topic", "导入测试", "--root", str(root / "out"), "--card", "general")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(proc.stdout.strip())

    def test_task_folder_from_begin_is_imported_with_its_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.new_session(root)
            task = root / "Luz-Crawl" / "raw" / "031_AI 资讯"  # <output root>/<category>/raw/NNN_需求, as Luz-Crawl lays it out
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

    def test_folders_that_are_not_crawl_tasks_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = self.new_session(root)
            stray = root / "012_随便一个目录"  # an NNN_ name alone is not enough outside the Luz-Crawl output root
            stray.mkdir()
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session), str(stray))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("luz-task.json", proc.stderr)
            proc = run(str(HERE / "03-session.py"), "import-crawl", str(session))
            self.assertNotEqual(proc.returncode, 0)  # the folder is required; --latest is gone


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
        radii = set(re.findall(r"border-radius:\s*(\d+px)", page))
        self.assertEqual(radii, {builder.RADIUS})
        self.assertIn("font-size:24px;line-height:1.3;font-weight:700", page)
        self.assertRegex(page, r"h1 \{[^}]*font-weight: 700")

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
        self.assertIn(f"border-left:3px solid {theme['action']}", page)
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
