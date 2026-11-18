"""The scratch builder cannot bypass packaging by targeting another deliverable root."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("article_boundary_builder", Path(__file__).with_name("02-article_builder.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.mark.parametrize("relative", ["Luz-Design/001-task/001-task.html", "project/docs/02-产品开发/01-page.html", "002-article/002-article.html", "02-article/02-article.html", "003_article/003_article.html"])
def test_test_out_cannot_write_business_deliverables(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(builder, "OUTPUT_ROOT", tmp_path / "Luz-Writing")
    body = tmp_path / "body.txt"
    body.write_text("## 测试正文\n\n这是一段离线测试文字。", encoding="utf-8")
    target = tmp_path / relative
    with pytest.raises(SystemExit):
        builder.main(["--title", "离线测试", "--body", str(body), "--out", str(target), "--no-check"])
    assert not target.exists()


def test_test_out_still_accepts_a_scratch_file(tmp_path, monkeypatch):
    monkeypatch.setattr(builder, "OUTPUT_ROOT", tmp_path / "Luz-Writing")
    body = tmp_path / "body.txt"
    body.write_text("## 测试正文\n\n临时目录中的离线渲染测试。", encoding="utf-8")
    target = tmp_path / "scratch" / "test.html"
    builder.main(["--title", "离线测试", "--body", str(body), "--out", str(target), "--no-check"])
    assert target.is_file()


def test_article_rejects_unregistered_template_paths_before_output(tmp_path):
    body = tmp_path / "body.txt"
    body.write_text("离线模板边界测试。", encoding="utf-8")
    template = tmp_path / "invented.html"
    template.write_text("<html>{{BODY}}</html>", encoding="utf-8")
    target = tmp_path / "scratch" / "article.html"
    with pytest.raises(SystemExit):
        builder.main(["--title", "离线测试", "--body", str(body), "--out", str(target), "--template", str(template)])
    assert not target.exists()
