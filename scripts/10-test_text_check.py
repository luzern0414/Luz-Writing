#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/09-text_check.py: GB/T 15834 / 15835 rules and the client-document, agreement and copy checks."""
from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("luz_writing_text_check", HERE / "09-text_check.py")
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)


def rules(text: str, doc: str | None = None, final: bool = False) -> set[str]:
    return {f.rule for f in tc.check_items(tc.text_items(text), doc, final)}


def sev(text: str, rule: str, doc: str | None = None) -> set[str]:
    return {f.sev for f in tc.check_items(tc.text_items(text), doc) if f.rule == rule}


GOOD_PROPOSAL = {
    "title": "门店预约与会员小程序建设方案",
    "format": "word",
    "toc": True,
    "hero": {"info": [["项目名称", "门店预约与会员小程序"], ["版本", "V1.0"], ["日期", "2026-11-02"]]},
    "sections": [
        {"key": "background", "title": "项目背景与需求分析", "blocks": [
            {"type": "text", "text": "门店目前靠微信群和纸质登记管理预约，高峰期容易漏记。"},
            {"type": "table", "caption": "当前的问题", "columns": ["现状问题", "具体表现", "带来的后果"],
             "rows": [["预约漏记", "高峰期靠群消息登记", "顾客到店无课"]]}]},
        {"key": "solution", "title": "解决方案", "blocks": [
            {"type": "sub", "text": "业务流程"},
            {"type": "text", "text": "顾客在小程序选择时段，系统校验名额后生成预约，开课前 2 小时内不能取消。"}]},
        {"key": "deliverables", "title": "交付内容", "blocks": [
            {"type": "table", "caption": "交付内容", "columns": ["交付项", "内容"], "rows": [["小程序", "顾客预约和会员"]]}]},
    ],
}


class StandardsTests(unittest.TestCase):
    def test_range_with_scale_unit_must_keep_both_ends(self) -> None:
        self.assertIn("N01", rules("预算 9~16亿"))
        self.assertIn("N01", rules("增长 15~30%"))
        self.assertNotIn("N01", rules("预算 9亿~16亿，增长 15%~30%，价格 12500~20000元"))

    def test_fullwidth_punctuation_in_chinese_sentences(self) -> None:
        self.assertIn("P01", rules("你好,世界"))
        self.assertIn("P01", rules("说明: 见下表"))
        self.assertNotIn("P01", rules("现在是 15:40，会议开始。"))
        self.assertNotIn("P01", rules("命令是 `a,b`，网址 https://a.com/x?y=1。"))

    def test_ellipsis_and_dash_forms(self) -> None:
        self.assertIn("P02", rules("他说...算了"))
        self.assertIn("P02", rules("他说…算了"))
        self.assertNotIn("P02", rules("他说……算了"))
        self.assertIn("P03", rules("会员--积分"))
        self.assertNotIn("P03", rules("会员——积分，时间 11:30—13:00"))

    def test_ellipsis_never_goes_with_deng(self) -> None:
        self.assertIn("P04", rules("猪肝、大豆……等"))
        self.assertIn("P05", rules("猪肝、大豆、等。"))
        self.assertNotIn("P05", rules("A、等待结果"))

    def test_dates_and_numbers(self) -> None:
        self.assertIn("N02", rules("日期 2026.11.02"))
        self.assertIn("N03", rules("26年11月起"))
        self.assertIn("N04", rules("比例 .46"))
        self.assertIn("N05", rules("共 4千 人"))
        self.assertNotIn("N05", rules("相距 4千米，增长百分之五"))
        self.assertNotIn("N02", rules("日期 2026-11-02，2026年11月2日"))

    def test_book_title_marks_are_not_for_activities_or_licences(self) -> None:
        self.assertIn("B01", rules("本市召开《全国食用色素应用研讨会》"))
        self.assertIn("B01", rules("向老人颁发《敬老证》"))
        self.assertNotIn("B01", rules("依据《中华人民共和国个人信息保护法》"))


class ClientDocumentTests(unittest.TestCase):
    def test_other_files_prices_and_placeholders_are_errors_in_a_proposal(self) -> None:
        self.assertIn("ERROR", sev("功能范围详见《功能清单》。", "C01", "proposal"))
        self.assertEqual(sev("配套文件：系统架构图", "C01", "proposal"), {"ERROR"})
        self.assertEqual(sev("报价合计 12 万元，人天单价 500。", "C02", "proposal"), {"ERROR"})
        self.assertEqual(sev("此处待补充。", "X01", "proposal"), {"ERROR"})
        self.assertEqual(sev("功能 [待核实：来源]", "X02", "proposal"), {"WARN"})  # a draft may carry gaps
        final = tc.check_items(tc.text_items("功能 [待核实：来源]"), "proposal", True)
        self.assertEqual({f.sev for f in final if f.rule == "X02"}, {"ERROR"})  # a delivered file may not

    def test_price_is_only_forbidden_in_the_proposal(self) -> None:
        self.assertNotIn("C02", rules("取消订单后退还 20 元券，单价以商品页为准。", "manual"))

    def test_technical_words_and_function_ids_warn_for_the_client(self) -> None:
        self.assertIn("C03", rules("通过 API 接口调用数据库，对应 FN-001。", "proposal"))
        self.assertNotIn("C03", rules("顾客预约时段后，店员核销。", "proposal"))

    def test_headings_have_no_parenthetical_explanations(self) -> None:
        self.assertEqual(sev("## 一天的运转（以午餐为例）", "C06", "proposal"), {"ERROR"})
        self.assertNotIn("C06", rules("## 一天的运转", "proposal"))

    def test_good_proposal_json_has_no_errors(self) -> None:
        items = tc.json_items(GOOD_PROPOSAL)
        findings = tc.check_items(items, "proposal") + tc.structural_findings(GOOD_PROPOSAL, "proposal")
        self.assertEqual([str(f) for f in findings if f.sev == "ERROR"], [])

    def test_proposal_json_structure_is_checked(self) -> None:
        bad = json.loads(json.dumps(GOOD_PROPOSAL))
        bad["sections"][0]["blocks"][1].pop("caption")
        bad["sections"] = [s for s in bad["sections"] if s["key"] != "solution"]
        bad["sections"][0]["title"] = "项目背景（含现状）"
        found = {f.rule for f in tc.check_items(tc.json_items(bad), "proposal") + tc.structural_findings(bad, "proposal")}
        self.assertTrue({"C09", "C10", "C06"} <= found, found)

    def test_requirements_json_is_checked_like_a_client_document_with_its_own_seven_chapters(self) -> None:
        section = lambda key, title, text: {"key": key, "title": title, "blocks": [{"type": "text", "text": text}]}
        good = {"title": "需求说明书", "format": "word", "toc": True, "sections": [
            section("background", "项目背景", "销售聊完客户后需要马上记下来。"), section("goals", "建设目标", "语音录入不超过 60 秒。"),
            section("scope", "范围与使用者", "销售用手机录入。"), section("requirements", "需求清单", "录入洽谈记录。"),
            section("rules", "业务规则与约束", "销售只看自己的客户。"), section("acceptance", "验收标准", "现场计时。"),
            section("open", "需要客户确认的事项", "服务器位置。")]}
        findings = tc.check_items(tc.json_items(good), "requirements") + tc.structural_findings(good, "requirements")
        self.assertEqual([str(f) for f in findings if f.sev == "ERROR"], [])
        bad = json.loads(json.dumps(good))
        bad["sections"] = [s for s in bad["sections"] if s["key"] != "open"]
        bad["sections"][0]["blocks"][0]["text"] = "报价合计 12 万元；对应 FN-001，详见《功能清单》。"
        found = {f.rule for f in tc.check_items(tc.json_items(bad), "requirements") + tc.structural_findings(bad, "requirements")}
        self.assertTrue({"C10", "C02", "C01", "C03"} <= found, found)

    def test_manual_chapters_need_their_fields(self) -> None:
        manual = {"title": "使用说明", "chapters": [{"id": "c1", "heading": "预约课程", "features": ["FN-001"], "entry": "首页 › 预约",
                                                    "steps": ["点击“预约”"], "rules": []}]}
        found = tc.structural_findings(manual, "manual")
        self.assertEqual([f.rule for f in found], ["C11"])
        self.assertIn("rules", found[0].message)

    def test_manual_steps_are_imperative(self) -> None:
        self.assertIn("C08", rules("您可以点击预约按钮", "manual"))
        self.assertNotIn("C08", rules("点击“预约”按钮", "manual"))

    def test_secrets_never_go_into_a_table(self) -> None:
        self.assertEqual(sev("支付密钥：abcd1234", "C05", "confirmation"), {"ERROR"})


class AgreementAndCopyTests(unittest.TestCase):
    def test_final_interpretation_is_an_error_and_actual_is_a_warning(self) -> None:
        self.assertEqual(sev("本活动最终解释权归本公司所有。", "A01", "agreement"), {"ERROR"})
        self.assertEqual(sev("价格以门店实际为准。", "A02", "agreement"), {"WARN"})

    def test_absolute_words_warn_and_normal_ordinals_do_not(self) -> None:
        self.assertIn("M01", rules("全网最低价，国家级品质，唯一选择", "copy"))
        self.assertNotIn("M01", rules("第一步，先登录。第一次使用会收到提示。", "copy"))
        self.assertIn("M02", rules("手慢无！", "copy"))

    def test_title_length_limit(self) -> None:
        items = tc.text_items("# " + "字" * 33 + "\n\n正文。")
        self.assertEqual([f.rule for f in tc.check_title(items, 32)], ["T01"])
        self.assertEqual(tc.check_title(items, 33), [])


class CliTests(unittest.TestCase):
    def run_cli(self, name: str, content: str, *args: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / name
            path.write_text(content, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = tc.main([str(path), *args])
            return code, out.getvalue() + err.getvalue()

    def test_clean_text_passes_and_errors_fail(self) -> None:
        code, text = self.run_cli("a.md", "## 预约规则\n\n开课前 2 小时内不能取消。\n", "--doc", "manual")
        self.assertEqual(code, 0, text)
        code, text = self.run_cli("a.md", "## 预约规则\n\n详见《功能清单》。\n", "--doc", "proposal")
        self.assertEqual(code, 1)
        self.assertIn("C01", text)

    def test_json_file_is_read_by_structure(self) -> None:
        code, text = self.run_cli("proposal.json", json.dumps(GOOD_PROPOSAL, ensure_ascii=False), "--doc", "proposal")
        self.assertEqual(code, 0, text)

    def test_missing_file_is_an_error(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(tc.main(["no-such-file.txt"]), 2)


if __name__ == "__main__":
    unittest.main()
