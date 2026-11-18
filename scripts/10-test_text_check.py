#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/09-text_check.py: GB/T 15834 / 15835 rules and the client-document, agreement and copy checks."""
from __future__ import annotations

import importlib.util
import io
import json
import os
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
    def test_external_sources_and_law_titles_are_not_internal_file_deferrals(self) -> None:
        for text in ('[S1] 发布方，《年度研究报告》，第 3 章，https://example.org/report。',
                     '依据《中华人民共和国个人信息保护法》，仅收集业务必需信息。'):
            self.assertNotIn('ERROR', sev(text, 'C01', 'proposal'))

    def test_other_files_prices_and_placeholders_are_errors_in_a_proposal(self) -> None:
        self.assertIn("ERROR", sev("功能范围详见《功能清单》。", "C01", "proposal"))
        self.assertEqual(sev("配套文件：系统架构图", "C01", "proposal"), {"ERROR"})
        self.assertNotIn("ERROR", sev("处理个人信息按《中华人民共和国个人信息保护法》执行。", "C01", "proposal"))
        self.assertEqual(sev("报价合计 12 万元，人天单价 1000。", "C02", "proposal"), {"ERROR"})        # no switch on: refused
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


WORKDAYS_ON = {"workdays": True, "quote": False, "requested_by": "客户采购负责人", "requested_at": "2026-11-05", "request_note": "请在方案里给出人日"}
QUOTE_ON = dict(WORKDAYS_ON, quote=True)
HUMAN_QUOTE = {"unit_price": 1000, "provided_by": "商务经理", "provided_at": "2026-11-05", "request_note": "请按报价单给价",
               "evidence": "uploads/客户报价单.xlsx 第 2 行"}


def gate_for(estimate=None, quote=None):
    return tc.estimate_gate({"estimate": estimate or {}}, quote)


def gated(text: str, doc: str, gate) -> list:
    return tc.check_items(tc.text_items(text), doc, False, gate)


def c02_errors(found) -> list:
    return [f for f in found if f.rule == "C02" and f.sev == "ERROR"]


def cli(argv: list[str]) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = tc.main(argv)
    return code, out.getvalue() + err.getvalue()


class EstimatePolicyTests(unittest.TestCase):
    """用户 2026-11-05：预算、人日、报价默认不写；明确要求才写；报价必须人工，不许 agent 自拟。"""

    def test_default_has_both_switches_off(self) -> None:
        gate = tc.Gate()
        self.assertEqual((gate.workdays, gate.quote), (False, False))
        found = gated("本期预算 20 万元，共 30 人日，工时按 2 天计。", "proposal", gate)
        self.assertGreaterEqual(len(c02_errors(found)), 3)
        self.assertEqual(gate_for({}).findings, ())                                  # an empty estimate or no config turns nothing on
        self.assertEqual(tc.estimate_gate(None, None), tc.Gate())

    def test_old_amounts_switch_means_both_off(self) -> None:
        self.assertEqual(tc.estimate_gate({"amounts": False}, None), tc.Gate())
        gate = tc.estimate_gate({"amounts": True}, None)                              # no evidence: not a switch
        self.assertEqual((gate.workdays, gate.quote), (False, False))
        self.assertTrue(any(f.sev == "WARN" and "amounts: true" in f.message for f in gate.findings))

    def test_workdays_on_with_evidence_lets_workdays_through_but_not_prices(self) -> None:
        gate = gate_for(WORKDAYS_ON)
        self.assertEqual((gate.workdays, gate.quote, gate.findings), (True, False, ()))
        self.assertEqual(gated("合计约 30 人日。", "proposal", gate), [])
        self.assertTrue(c02_errors(gated("总价 20 万元，报价见下。", "proposal", gate)))

    def test_a_switch_without_evidence_is_an_error_and_does_not_count(self) -> None:
        for broken in ({"workdays": True}, dict(WORKDAYS_ON, request_note=""), dict(WORKDAYS_ON, requested_at=None)):
            gate = gate_for(broken)
            self.assertEqual((gate.workdays, gate.quote), (False, False), broken)
            self.assertTrue(any(f.sev == "ERROR" and f.rule == "C12" for f in gate.findings), broken)
        gate = gate_for(dict(WORKDAYS_ON, requested_by="智能体"))
        self.assertFalse(gate.workdays)
        self.assertTrue(any("不是具体的人" in f.message for f in gate.findings))
        self.assertTrue(any(f.sev == "ERROR" for f in gate_for({"workdays": "yes"}).findings))

    def test_quote_needs_workdays_and_a_human_quotation(self) -> None:
        gate = gate_for(dict(QUOTE_ON, workdays=False), HUMAN_QUOTE)
        self.assertEqual((gate.workdays, gate.quote), (False, False))
        self.assertTrue(any("workdays 必须同时为 true" in f.message for f in gate.findings))
        gate = gate_for(QUOTE_ON, None)                                               # nobody gave a number yet: stop
        self.assertEqual((gate.workdays, gate.quote), (True, False))
        self.assertTrue(any("等待人工报价" in f.message and f.sev == "ERROR" for f in gate.findings))
        ok = gate_for(QUOTE_ON, HUMAN_QUOTE)
        self.assertEqual((ok.workdays, ok.quote, ok.findings), (True, True, ()))
        self.assertEqual(c02_errors(gated("报价合计 12 万元，人天单价 1000。", "proposal", ok)), [])

    def test_quote_evidence_fields_and_who_may_give_them(self) -> None:
        for key in ("provided_by", "provided_at", "request_note", "evidence"):
            gate = gate_for(QUOTE_ON, {k: v for k, v in HUMAN_QUOTE.items() if k != key})
            self.assertFalse(gate.quote, key)
            self.assertTrue(any(key in f.message and f.sev == "ERROR" for f in gate.findings), key)
        for price in (0, -1, True, "1000", None):
            self.assertFalse(gate_for(QUOTE_ON, dict(HUMAN_QUOTE, unit_price=price)).quote, price)
        for who in ("智能体", "Claude", "agent", "示例", "暂估", "系统", "default"):
            gate = gate_for(QUOTE_ON, dict(HUMAN_QUOTE, provided_by=who))
            self.assertFalse(gate.quote, who)
            self.assertTrue(any("不是具体的人" in f.message for f in gate.findings), who)
        for evidence in ("暂估", "示例数据", "默认值", "sample"):
            self.assertFalse(gate_for(QUOTE_ON, dict(HUMAN_QUOTE, evidence=evidence)).quote, evidence)
        self.assertTrue(gate_for(QUOTE_ON, dict(HUMAN_QUOTE, provided_by="Zhang Wei")).quote)
        long_real = "uploads/客户报价单.xlsx 第 2 行，商务经理微信原话"
        self.assertTrue(gate_for(QUOTE_ON, dict(HUMAN_QUOTE, evidence=long_real)).quote)             # a long, real evidence is never read as a placeholder word

    def test_a_quote_whose_evidence_fails_leaves_the_price_words_forbidden(self) -> None:
        gate = gate_for(QUOTE_ON, {"unit_price": 500})                                # the old bare quote.json
        self.assertFalse(gate.quote)
        self.assertTrue(gate.workdays)
        self.assertTrue(c02_errors(gated("报价合计 12 万元。", "requirements", gate)))

    def test_requirements_follow_the_same_rule_and_usage_docs_only_refuse_sure_workday_words(self) -> None:
        self.assertEqual(sev("预算不超过 20 万元。", "C02", "requirements"), {"ERROR"})
        self.assertNotIn("C02", rules("单价以商品页为准，工时统计按月出报表。", "manual"))
        self.assertEqual(sev("本次实施共 30 人日。", "C02", "manual"), {"ERROR"})
        self.assertEqual(sev("本次实施共 30 人天。", "C02", "confirmation"), {"ERROR"})
        self.assertEqual(gated("本次实施共 30 人日。", "manual", gate_for(WORKDAYS_ON)), [])

    def test_a_business_word_can_be_allowed_by_name(self) -> None:
        found = tc.check_items(tc.text_items("员工工时统计按月出报表。"), "requirements", False, tc.Gate(), ("工时",))
        self.assertEqual(c02_errors(found), [])
        found = tc.check_items(tc.text_items("工时统计后报价。"), "requirements", False, tc.Gate(), ("工时",))
        self.assertEqual(len(c02_errors(found)), 1)                                   # 报价 is still refused

    def test_money_without_a_human_quote_stays_a_warning(self) -> None:
        self.assertEqual(sev("满 ¥200 减 ¥20。", "C02", "proposal"), {"WARN"})

    def test_cli_default_and_project_config(self) -> None:
        bad = json.loads(json.dumps(GOOD_PROPOSAL))
        bad["sections"][0]["blocks"][0]["text"] = "共 30 人日，报价合计 12 万元。"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)                                                       # a state root: config/documents.json beside data/client
            client = root / "data" / "client"
            client.mkdir(parents=True)
            (root / "config").mkdir()
            proposal = client / "proposal.json"
            proposal.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            run = lambda *a: cli([str(proposal), "--doc", "proposal", *a])
            code, out = run()
            self.assertEqual(code, 1, out)                                           # no config: both off
            self.assertIn("workdays=关", out)
            (root / "config" / "documents.json").write_text(json.dumps({"amounts": False}), encoding="utf-8")
            self.assertEqual(run()[0], 1)
            (root / "config" / "documents.json").write_text(json.dumps({"estimate": QUOTE_ON}), encoding="utf-8")
            code, out = run()
            self.assertEqual(code, 1, out)                                           # switches on but nobody gave a quote
            self.assertIn("等待人工报价", out)
            (client / "quote.json").write_text(json.dumps(HUMAN_QUOTE, ensure_ascii=False), encoding="utf-8")
            code, out = run()
            self.assertEqual(code, 0, out)                                           # evidence complete: found by the folder layout
            self.assertIn("quote=开", out)
            other = root / "off.json"
            other.write_text(json.dumps({"estimate": {}}), encoding="utf-8")
            self.assertEqual(run("--project-config", str(other))[0], 1)               # an explicit path wins
            self.assertEqual(run("--project-config", str(root / "missing.json"))[0], 2)
            code, out = run("--allow-term", "人日", "--allow-term", "报价", "--project-config", str(other))
            self.assertEqual(code, 0, out)

    def test_cli_reads_the_config_from_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "documents.json"
            config.write_text(json.dumps({"estimate": WORKDAYS_ON}), encoding="utf-8")
            draft = root / "a.md"
            draft.write_text("## 范围\n\n共 30 人日。\n", encoding="utf-8")
            old = os.environ.get("LUZ_DOCUMENTS_CONFIG")
            os.environ["LUZ_DOCUMENTS_CONFIG"] = str(config)
            try:
                code, out = cli([str(draft), "--doc", "proposal"])
            finally:
                if old is None:
                    os.environ.pop("LUZ_DOCUMENTS_CONFIG")
                else:
                    os.environ["LUZ_DOCUMENTS_CONFIG"] = old
            self.assertEqual(code, 0, out)
            self.assertEqual(cli([str(draft), "--doc", "proposal"])[0], 1)            # same file, no config: refused


class SharedTermsTests(unittest.TestCase):
    """The policy's words are one copy for every Luz skill: this copy must match Luz-Design's master, and the checks must not keep their own lists."""

    def test_estimate_terms_copy_matches_the_master(self) -> None:
        master = Path(r"D:\Codes\Luz-Design\scripts\estimate_terms.py")
        if not master.is_file():
            self.skipTest("Luz-Design scripts/estimate_terms.py is not installed: nothing to compare the copy with")
        spec_ = importlib.util.spec_from_file_location("luz_design_estimate_terms", master)
        module = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(module)
        self.assertEqual(tc.et.terms_digest(), module.terms_digest(), "run Luz-Design scripts/sync_estimate_terms.py --write")

    def test_the_check_reads_the_shared_words(self) -> None:
        for name in ("NOT_A_PERSON", "NOT_EVIDENCE"):
            self.assertFalse(hasattr(tc, name), f"09-text_check must not keep its own {name}")
        for word in tc.et.WORKDAY_WORDS:
            self.assertTrue(tc.WORKDAY_TERMS.search(word), word)
        self.assertTrue(tc.et.not_a_person("智能体") and not tc.et.not_a_person("商务经理"))


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
