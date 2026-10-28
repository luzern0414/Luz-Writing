#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for 04-experience.py: upsert replaces, caps prune, duplicates fail."""

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


class ExperienceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = str(Path(self.tmp.name) / "store.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def entries(self) -> list[dict]:
        return json.loads(Path(self.store).read_text(encoding="utf-8"))["entries"]

    def test_upsert_replaces_in_place(self) -> None:
        run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用 3D 潮玩")
        code, out = run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用软陶质感")
        self.assertEqual(code, 0, out)
        entries = self.entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "封面用软陶质感")
        self.assertEqual(entries[0]["previous"]["text"], "封面用 3D 潮玩")
        self.assertEqual(entries[0]["uses"], 2)
        run("--store", self.store, "note", "--kind", "preference", "--key", "封面风格", "--text", "封面用扁平插画")
        self.assertEqual(self.entries()[0]["previous"]["text"], "封面用软陶质感")

    def test_same_text_under_new_key_is_rejected(self) -> None:
        run("--store", self.store, "note", "--kind", "lesson", "--key", "a", "--text", "不要堆数字。")
        code, _ = run("--store", self.store, "note", "--kind", "lesson", "--key", "b", "--text", "不要 堆数字")
        self.assertEqual(code, 1)
        self.assertEqual(len(self.entries()), 1)

    def test_cap_prunes_least_valuable(self) -> None:
        data = {"entries": []}
        for i in range(exp.CAPS["preference"]):
            exp.upsert(data, "preference", f"k{i}", f"规则 {i}", on="2026-01-01")
        exp.upsert(data, "preference", "k0", "规则 0 新版", on="2026-02-01")
        exp.upsert(data, "preference", "new", "新规则", on="2026-03-01")
        removed = exp.prune(data)
        self.assertEqual(len(removed), 1)
        self.assertNotIn(removed[0]["key"], {"k0", "new"})
        self.assertEqual(sum(e["kind"] == "preference" for e in data["entries"]), exp.CAPS["preference"])

    def test_drop_stale(self) -> None:
        data = {"entries": []}
        exp.upsert(data, "fact", "old", "旧信息", on="2025-01-01")
        exp.upsert(data, "fact", "fresh", "新信息", on="2026-10-01")
        removed = exp.prune(data, drop_stale=True, now=date(2026, 10, 28))
        self.assertEqual([e["key"] for e in removed], ["old"])

    def test_check_detects_duplicates_overflow_and_privacy(self) -> None:
        entry = {"kind": "lesson", "key": "x", "text": "同一句话", "last_confirmed": "2026-10-28"}
        data = {"entries": [dict(entry), dict(entry, key="y"), dict(entry, key="x", text="另一句")]}
        found = " ".join(exp.problems(data))
        self.assertIn("key 重复", found)
        self.assertIn("内容重复", found)
        many = {"entries": [dict(entry, kind="preference", key=f"p{i}", text=f"偏好{i}")
                            for i in range(exp.CAPS["preference"] + 1)]}
        self.assertTrue(any("超出上限" in p for p in exp.problems(many)))
        private = {"entries": [dict(entry, text="联系 13800138000")]}
        self.assertTrue(any("手机号" in p for p in exp.problems(private)))

    def test_note_rejects_private_data_unless_local(self) -> None:
        code, _ = run("--store", self.store, "note", "--kind", "fact", "--key", "c", "--text", "发到 a@b.com")
        self.assertEqual(code, 1)
        local = str(Path(self.tmp.name) / "me.local.json")
        code, _ = run("--store", local, "note", "--kind", "fact", "--key", "c", "--text", "发到 a@b.com")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
