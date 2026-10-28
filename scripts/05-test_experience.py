#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for 04-experience.py: upsert replaces, same text confirms, caps prune, check fails, shared notes shape."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("experience", HERE / "04-experience.py")
exp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp)


def run(*argv: str) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = exp.main(list(argv))
    return code, out.getvalue() + err.getvalue()


def note(key: str, text: str, kind: str = "preference", uses: int = 1, day: str = "2026-01-01") -> dict:
    return {"key": key, "kind": kind, "text": text, "uses": uses, "first_seen": day, "last_confirmed": day}


class ExperienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = str(Path(self.tmp.name) / "notes.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def notes(self) -> list[dict]:
        return json.loads(Path(self.store).read_text(encoding="utf-8"))["notes"]

    def test_upsert_replaces_in_place(self) -> None:
        run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用 3D 潮玩")
        code, out = run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用软陶质感")
        self.assertEqual(code, 0, out)
        notes = self.notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["text"], "封面用软陶质感")
        self.assertEqual(notes[0]["previous"], {"text": "封面用 3D 潮玩", "replaced_at": date.today().isoformat()})
        self.assertEqual(notes[0]["uses"], 2)
        run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用扁平插画")
        self.assertEqual(self.notes()[0]["previous"]["text"], "封面用软陶质感")

    def test_same_text_under_new_key_confirms_existing(self) -> None:
        run("--store", self.store, "note", "--kind", "lesson", "--key", "a", "--text", "不要堆数字。")
        code, out = run("--store", self.store, "note", "--kind", "lesson", "--key", "b", "--text", "不要 堆数字")
        self.assertEqual(code, 0, out)
        self.assertIn("confirmed lesson a", out)
        self.assertEqual([(n["key"], n["uses"]) for n in self.notes()], [("a", 2)])

    def test_cap_prunes_fewest_uses_then_oldest(self) -> None:
        cap = exp.NOTE_CAPS["preference"]
        doc = {**exp.new_notes_doc(), "notes": [note(f"k{i}", f"规则 {i}", uses=2) for i in range(cap - 2)]}
        doc["notes"] += [note("rare-old", "很少用且旧", day="2025-01-01"), note("rare-new", "很少用但新", day="2026-02-01")]
        action, _, removed = exp.upsert_note(doc, "preference", "new", "新规则", on="2026-03-01")
        self.assertEqual(action, "added")
        self.assertEqual([n["key"] for n in removed], ["rare-old"])
        self.assertEqual(sum(n["kind"] == "preference" for n in doc["notes"]), cap)

    def test_prune_lists_stale(self) -> None:
        exp.save_notes(Path(self.store), {**exp.new_notes_doc(), "notes": [note("old", "旧信息", "fact", day="2025-01-01")]})
        code, out = run("--store", self.store, "prune")
        self.assertEqual(code, 0, out)
        self.assertIn("not confirmed for 180 days (confirm or replace): old", out)
        self.assertEqual(len(exp.stale_notes(exp.load_notes(Path(self.store)), now=date(2026, 10, 28))), 1)

    def test_check_detects_duplicates_overflow_shape_and_privacy(self) -> None:
        doc = {**exp.new_notes_doc(), "notes": [note("x", "同一句话", "lesson"), note("y", "同一句话", "lesson"),
                                                note("x", "另一句", "lesson")]}
        found = " ".join(exp.check_notes(doc))
        self.assertIn("duplicate note key x", found)
        self.assertIn("repeats the statement of x", found)
        many = {**exp.new_notes_doc(), "notes": [note(f"p{i}", f"偏好{i}") for i in range(exp.NOTE_CAPS["preference"] + 1)]}
        self.assertTrue(any("exceed the cap" in p for p in exp.check_notes(many)))
        private = {**exp.new_notes_doc(), "notes": [note("x", "联系 13800138000")]}
        self.assertTrue(any("phone number" in p for p in exp.check_notes(private)))
        old = {"version": 1, "entries": [{**note("x", "旧格式"), "created": "2026-01-01"}]}
        self.assertTrue(any("top-level fields" in p for p in exp.check_notes(old)))

    def test_note_rejects_private_data_unless_local(self) -> None:
        for text in ("发到 a@b.com", "微信号：abc_12345", r"放在 C:\Users\me\a.md", "password=hunter22"):
            code, _ = run("--store", self.store, "note", "--kind", "fact", "--key", "c", "--text", text)
            self.assertEqual(code, 1, text)
        local = str(Path(self.tmp.name) / "me.local.json")
        code, _ = run("--store", local, "note", "--kind", "fact", "--key", "c", "--text", "发到 a@b.com")
        self.assertEqual(code, 0)


class SharedNotesSpecTest(unittest.TestCase):
    """experience/notes.json has the shape shared by Luz-System, Luz-Design, Luz-Dev and Luz-Writing."""

    def test_committed_notes_file_matches_shared_spec(self) -> None:
        path = HERE.parent / "experience" / "notes.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(list(doc), ["schema_version", "caps", "notes"])
        self.assertEqual(doc["schema_version"], "1.0")
        self.assertEqual(doc["caps"], {"preference": 60, "lesson": 120, "fact": 120})
        allowed = {"key", "kind", "text", "why", "uses", "first_seen", "last_confirmed", "previous"}
        for n in doc["notes"]:
            self.assertLessEqual({"key", "kind", "text", "uses", "first_seen", "last_confirmed"}, set(n), n.get("key"))
            self.assertLessEqual(set(n), allowed, n.get("key"))
            self.assertIn(n["kind"], ("preference", "lesson", "fact"))
            self.assertRegex(n["first_seen"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex(n["last_confirmed"], r"^\d{4}-\d{2}-\d{2}$")
            if "previous" in n:
                self.assertEqual(set(n["previous"]), {"text", "replaced_at"})
        self.assertEqual(len({n["key"] for n in doc["notes"]}), len(doc["notes"]))
        self.assertEqual(exp.check_notes(doc), [])
        self.assertFalse((path.parent / "experience.json").exists() or (path.parent / "preferences.json").exists()
                         or (path.parent / "lessons.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
