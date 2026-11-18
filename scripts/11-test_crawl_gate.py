#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The project-mode expiry waiver of 08-crawl_gate.py: in a Luz-Project project, a Crawl record of a stage the project has completed no longer has to be younger than
seven days (Luz-Project references/runbook.md, section 12). The waiver block is the same text in Luz-Ops, Luz-System, Luz-Dev and Luz-Writing; test_the_four_skills_carry_the_same_block
is the sync check (no script copies crawl_gate.py). A project task of this skill records its stage and state root in the session manifest; 03-session.py passes both."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load("luz_writing_crawl_gate_test", "08-crawl_gate.py")
session_mod = load("luz_writing_session_test", "03-session.py")

GATES = {"Luz-Ops": "scripts/crawl_gate.py", "Luz-System": "scripts/crawl_gate.py", "Luz-Dev": "scripts/crawl_gate.py", "Luz-Writing": "scripts/08-crawl_gate.py"}
BEGIN, END = "# ---- project-mode expiry waiver", "# ---- end of project-mode expiry waiver ----"
EXPIRED = "Crawl 前置检索 luz-writing/requirements: 检索记录超过七天，请按当前需求复核"
OTHER = "Crawl 前置检索 luz-writing/requirements: 缺少补充信息"


def fake_api(waived: bool, calls: list | None = None) -> types.ModuleType:
    module = types.ModuleType("approval_docs")

    def crawl_expiry_waived(project, stage):
        if calls is not None:
            calls.append((str(project), stage))
        return waived

    module.crawl_expiry_waived = crawl_expiry_waived  # type: ignore[attr-defined]
    return module


def fake_crawl_root(folder: str) -> Path:
    """A Luz-Crawl whose validator always reports the age finding and one other finding."""
    scripts = Path(folder, "scripts")
    scripts.mkdir()
    scripts.joinpath("crawl_preflight.py").write_text(f"def validate_preflight(session, caller, stage=None):\n    return [{EXPIRED!r}, {OTHER!r}]\n", encoding="utf-8")
    return Path(folder)


class WaiverBlockTests(unittest.TestCase):
    def test_the_four_skills_carry_the_same_block(self) -> None:
        blocks = {}
        for skill, rel in GATES.items():
            path = SKILLS / skill / rel
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertIn(BEGIN, text, skill)
                blocks[skill] = text[text.index(BEGIN):text.index(END) + len(END)]
        self.assertIn("Luz-Writing", blocks)
        self.assertEqual({skill: block == blocks["Luz-Writing"] for skill, block in blocks.items()}, {skill: True for skill in blocks}, "edit the block in one skill and copy it into the others")

    def test_the_phrase_is_the_one_luz_crawl_writes(self) -> None:
        self.assertEqual(gate.EXPIRY_MARK, "检索记录超过七天")
        crawl = SKILLS / "Luz-Crawl" / "scripts" / "crawl_preflight.py"
        if crawl.is_file():
            self.assertIn("检索记录超过七天", crawl.read_text(encoding="utf-8"))

    def test_only_the_age_finding_goes_and_only_when_luz_project_waives_the_stage(self) -> None:
        calls: list = []
        with mock.patch.dict(sys.modules, {"approval_docs": fake_api(True, calls)}):
            self.assertEqual(gate.drop_expired([EXPIRED, OTHER], "state", "requirements"), [OTHER])
        self.assertEqual(calls, [("state", "requirements")])
        with mock.patch.dict(sys.modules, {"approval_docs": fake_api(False)}):
            self.assertEqual(gate.drop_expired([EXPIRED, OTHER], "state", "requirements"), [EXPIRED, OTHER])

    def test_a_standalone_call_or_a_record_without_the_age_finding_never_asks(self) -> None:
        calls: list = []
        with mock.patch.dict(sys.modules, {"approval_docs": fake_api(True, calls)}):
            self.assertEqual(gate.drop_expired([EXPIRED, OTHER], "session", None), [EXPIRED, OTHER])
            self.assertEqual(gate.drop_expired([OTHER], "state", "requirements"), [OTHER])
        self.assertEqual(calls, [])

    def test_without_luz_project_or_when_it_cannot_answer_nothing_is_waived(self) -> None:
        errors = [EXPIRED, OTHER]
        with tempfile.TemporaryDirectory() as empty, mock.patch.dict(os.environ, {"LUZ_PROJECT_SCRIPTS": empty}), mock.patch.dict(sys.modules, {"approval_docs": fake_api(True)}):
            self.assertEqual(gate.drop_expired(errors, "state", "requirements"), errors)
        broken = types.ModuleType("approval_docs")
        broken.crawl_expiry_waived = mock.Mock(side_effect=RuntimeError("interface changed"))  # type: ignore[attr-defined]
        with mock.patch.dict(sys.modules, {"approval_docs": broken}):
            self.assertEqual(gate.drop_expired(errors, "state", "requirements"), errors)
        with mock.patch.dict(sys.modules, {"approval_docs": types.ModuleType("approval_docs")}):
            self.assertEqual(gate.drop_expired(errors, "state", "requirements"), errors)

    def test_the_import_appends_and_sys_path_is_left_as_it_was(self) -> None:
        without_project = [p for p in sys.path if "Luz-Project" not in p]
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "approval_docs.py").write_text("def crawl_expiry_waived(project, stage):\n    return True\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LUZ_PROJECT_SCRIPTS": tmp}), mock.patch.dict(sys.modules), mock.patch.object(sys, "path", list(without_project)):
                sys.modules.pop("approval_docs", None)
                self.assertTrue(gate.expiry_waived("state", "requirements"))
                self.assertEqual(sys.path, without_project)
                sys.modules.pop("approval_docs", None)

    def test_crawl_errors_takes_the_project_stage_and_state_root_of_a_skill_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = fake_crawl_root(tmp)
            state, session = Path(tmp, "state-root"), Path(tmp, "session-folder")
            for project in (state, session):
                project.mkdir()
                (project / "project.json").write_text("{}", encoding="utf-8")
            asked: list = []
            with mock.patch.dict(os.environ, {"LUZ_CRAWL_ROOT": str(root)}), mock.patch.dict(sys.modules, {"approval_docs": fake_api(True, asked)}):
                self.assertEqual(gate.crawl_errors(str(session), "requirements", "luz-writing", state_root=str(state)), [OTHER])
                self.assertEqual(gate.crawl_errors(str(session), "requirements", "luz-writing"), [OTHER])
                self.assertEqual(gate.crawl_errors(str(session), None, "luz-writing", state_root=str(state)), [EXPIRED, OTHER])
            self.assertEqual(asked, [(str(state), "requirements"), (str(session), "requirements")])
            with mock.patch.dict(os.environ, {"LUZ_CRAWL_ROOT": str(Path(tmp, "nowhere"))}):
                self.assertIn("校验器不存在", gate.crawl_errors("session-folder", "requirements", "luz-writing")[0])


def run_session(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-X", "utf8", str(HERE / "03-session.py"), *args], capture_output=True, text=True, encoding="utf-8")


class SessionPassesTheProjectTests(unittest.TestCase):
    """A project stage can ask its state root; a named standalone stage never asks for project expiry waiver."""

    def make_project(self, base: Path) -> Path:
        state = base / "skill输出" / "Luz-Project" / "014-示例项目" / "raw"
        (state / "00-crawl").mkdir(parents=True)
        (state / "project.json").write_text(json.dumps({"name": "示例项目", "deliver_root": str(base / "014-示例项目")}, ensure_ascii=False), encoding="utf-8")
        (base / "014-示例项目" / "docs").mkdir(parents=True)
        return state

    def test_a_project_session_asks_with_its_stage_and_state_root_and_a_standalone_one_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            state = self.make_project(base)
            project = run_session("new", "--topic", "需求说明书文字", "--root", str(base / "out"), "--card", "client-document", "--project", str(state), "--stage", "requirements")
            self.assertEqual(project.returncode, 0, project.stderr)
            standalone = run_session("new", "--topic", "一篇文章", "--root", str(base / "out"), "--card", "general")
            self.assertEqual(standalone.returncode, 0, standalone.stderr)
            project_session, standalone_session = Path(project.stdout.strip()), Path(standalone.stdout.strip())
            (base / "crawl").mkdir()
            root = fake_crawl_root(str(base / "crawl"))
            asked: list = []
            with mock.patch.dict(os.environ, {"LUZ_CRAWL_ROOT": str(root)}), mock.patch.dict(sys.modules, {"approval_docs": fake_api(True, asked)}):
                self.assertEqual(session_mod.project_crawl_errors(project_session), [OTHER])
                self.assertEqual([e for e in session_mod.packaging_errors(project_session) if "Crawl" in e], [OTHER])
                self.assertEqual(asked, [(str(state.resolve()), "requirements")] * 2)
                asked.clear()
                self.assertEqual(session_mod.project_crawl_errors(standalone_session), [EXPIRED, OTHER], "a standalone session keeps every finding")
                self.assertEqual(asked, [])
            with mock.patch.dict(os.environ, {"LUZ_CRAWL_ROOT": str(root)}), mock.patch.dict(sys.modules, {"approval_docs": fake_api(False)}):
                self.assertEqual(session_mod.project_crawl_errors(project_session), [EXPIRED, OTHER], "a stage still being worked on keeps the seven days")


class RealLuzProjectTests(unittest.TestCase):
    """The real ``approval_docs`` on a project made by Luz-Project; only the verdict "stage complete" is forced."""

    def setUp(self) -> None:
        self.scripts = SKILLS / "Luz-Project" / "scripts"
        if not (self.scripts / "approval_docs.py").is_file():
            self.skipTest("Luz-Project is not here")

    def make_project(self, tmp: str) -> Path:
        """A project made by Luz-Project itself. Its code imports ``crawl_gate`` by name and means its own module (the one that takes ``waive_expiry``), so that one is
        in sys.modules while the project is made."""
        spec = importlib.util.spec_from_file_location("project_crawl_gate", self.scripts / "project_crawl_gate.py")
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"project_crawl_gate": module}):
            sys.path.append(str(self.scripts))
            spec.loader.exec_module(module)
            from project_core import create_project  # type: ignore[import-not-found]

            return create_project("豁免", Path(tmp) / "项目" / "001-豁免", Path(tmp) / "luz-project")

    def test_the_real_interface_answers_a_bool_for_a_real_project_and_for_a_missing_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"LUZ_PROJECT_OUTPUT": str(Path(tmp) / "luz-project")}), \
                mock.patch.object(sys, "path", list(sys.path)), mock.patch.dict(sys.modules):
            state = self.make_project(tmp)
            self.assertFalse(gate.expiry_waived(state, "requirements"), "a stage that is being worked on keeps the seven days")
            self.assertFalse(gate.expiry_waived(state, "no-such-stage"))
            self.assertFalse(gate.expiry_waived(Path(tmp) / "没有的项目", "requirements"), "not a project: nothing is waived")
            import approval_docs  # type: ignore[import-not-found]

            with mock.patch.object(approval_docs, "stage_complete", return_value=True):
                self.assertTrue(gate.expiry_waived(state, "requirements"))
                self.assertTrue(gate.expiry_waived(Path(state).parent, "requirements"), "the Luz-Project session folder names the project as well")
                self.assertEqual(gate.drop_expired([EXPIRED, OTHER], state, "requirements"), [OTHER])


if __name__ == "__main__":
    unittest.main()
