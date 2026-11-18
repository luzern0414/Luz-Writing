"""A non-HTML deliverable's formal summary has the same research boundary as an article."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1] / "Luz-Crawl" / "scripts"))
from test_crawl_preflight import complete_fixture

spec = importlib.util.spec_from_file_location("summary_session_gate", HERE / "03-session.py")
session_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_module)


def session_at(tmp_path, project=None):
    args = [sys.executable, "-B", "-X", "utf8", str(HERE / "03-session.py"), "new", "--topic", "summary gate", "--root", str(tmp_path / "sessions"), "--card", "client-document"]
    if project:
        args += ["--project", str(project), "--stage", "requirements"]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    return Path(result.stdout.strip())


@pytest.mark.parametrize("existing", [False, True])
def test_writing_summary_without_research_preserves_all_files(tmp_path, existing):
    session = session_at(tmp_path)
    (session / "deliverable.pdf").write_bytes(b"%PDF offline fixture")
    target = session / f"{session.name}.html"
    if existing:
        target.write_text("existing approved summary", encoding="utf-8")
    before = {p: p.read_bytes() for p in session.rglob("*") if p.is_file()}
    args = SimpleNamespace(session=str(session), title=None, force=existing, project_linked=False, deliverable=["deliverable.pdf|总结"])
    with pytest.raises(SystemExit, match="Crawl"):
        session_module.cmd_summary(args)
    assert {p: p.read_bytes() for p in session.rglob("*") if p.is_file()} == before


def test_writing_summary_reads_linked_stage_evidence_from_the_project(tmp_path):
    state = tmp_path / "state"
    deliver = tmp_path / "deliver"
    doc = deliver / "docs" / "01-需求对接" / "01-需求说明书.pdf"
    doc.parent.mkdir(parents=True)
    doc.write_bytes(b"%PDF offline fixture")
    state.mkdir()
    (state / "project.json").write_text(json.dumps({"name": "summary", "deliver_root": str(deliver), "crawl": {"evidence_index": "00-crawl"}}), encoding="utf-8")
    session = session_at(tmp_path, state)
    args = SimpleNamespace(session=str(session), title=None, force=False, project_linked=False, deliverable=["docs/01-需求对接/01-需求说明书.pdf|需求说明"])
    complete_fixture(session, "luz-writing", "requirements")
    with pytest.raises(SystemExit, match="Crawl"):
        session_module.cmd_summary(args)
    complete_fixture(state, "luz-writing", "requirements")
    session_module.cmd_summary(args)
    assert (session / f"{session.name}.html").is_file()
