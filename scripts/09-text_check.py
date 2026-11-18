#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文文字的机器可判断部分：标点、数字、日期（GB/T 15834、15835），以及客户文件、协议和营销文案各自的硬性写法。

  py -X utf8 scripts/09-text_check.py <文件> [--doc proposal|requirements|manual|confirmation|agreement|copy|article] [--final] [--max-title N]
                                      [--project-config <状态根>/config/documents.json] [--quote-file quote.json] [--allow-term 词]

文件可以是 .txt / .md 正文，也可以是 Luz-Project 的 proposal.json / requirements.json / manual.json（逐个字符串检查，标题与表题按位置识别）。
没有 --doc 时只查标点、数字、日期、占位。ERROR 会让命令失败，WARN 只提示；它只找能机器判断的问题，
事实、依据、读者能否看懂仍要人读。规则出处见 references/18-client-documents.md 与 19-chinese-text-standards.md。

预算、人日与报价（用户 2026-11-05 的规定）：客户文件默认不写人日、工时、预算、单价、报价和付款，方案与需求说明书里出现这些字样就是 ERROR。
只有项目的 config/documents.json 里 estimate.workdays（人日）或 estimate.quote（单价与报价）打开，并且带着证据，才放行：
  - 开关证据 estimate.requested_by、requested_at、request_note 三项齐全，requested_by 是具体的人；
  - 报价还要有人工报价单 quote.json（provided_by、provided_at、request_note、evidence、unit_price），provided_by 不能是智能体、技能、工具、示例或暂估。
配置路径来自 --project-config、环境变量 LUZ_DOCUMENTS_CONFIG，或检查 <状态根>/data/client/ 下的文件时自动找 <状态根>/config/documents.json；
都没有就按两个开关都关。quote.json 来自 --quote-file，或与被检文件同目录。证据缺失时开关等于没开，并另报一条错误。
业务本身就有的词（例如人事系统的“工时统计”）确需出现时，用 --allow-term 逐个放行。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import NamedTuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_terms as et  # noqa: E402  the policy's words, one copy for every Luz skill (master in Luz-Design, copied by its sync_estimate_terms.py)

CJK = "一-鿿"
OTHER_FILES = et.INTERNAL_DOCUMENT_REFERENCES
POINTERS = re.compile(r"详见|参见|另见|请参阅|参阅")
PLACEHOLDER = re.compile(r"待补充|TODO|TBD|占位符|占位文字|xxx|lorem ipsum|××|【请填写[^】]*】", re.I)
GAP = re.compile(r"\[待核实[:：][^\]]*\]")
# 预算、人日与报价：两组词各由一个开关放行（estimate.workdays / estimate.quote），默认都关。
def _words(words) -> re.Pattern:
    return re.compile("|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)))


WORKDAY_TERMS = _words(et.WORKDAY_WORDS)
# 使用说明、确认表里也不会有的词；“工时”可能是业务概念，只在方案与需求说明书里查
SURE_WORKDAY_TERMS = _words(w for w in et.WORKDAY_WORDS if w != "工时")
# 正文里的价格词：共用词表里写在行文中不会是业务概念的几个（金额、折扣在业务规则里很常见，不在此列），加上只有合同与报价文字才有的付款说法。
PAYMENT_PHRASES = ("含税", "首付款", "尾款", "付款节点", "付款方式", "项目预算", "开发费用", "实施费用", "合同金额")
QUOTE_TERMS = _words([w for w in ("报价", "单价", "总价", "预算") if w in et.MONEY_WORDS] + list(PAYMENT_PHRASES))
ESTIMATE_DOCS = ("proposal", "requirements")
MONEY = re.compile(r"[¥￥]\s*\d|人民币\s*\d|RMB\s*\d", re.I)
JARGON = re.compile(r"\b(?:API|SDK|JSON|SQL|Redis|MySQL|Docker|Kubernetes|K8s|HTTPS?|RESTful|WebSocket|Nginx)\b"
                    r"|接口|数据库|表结构|微服务|前端|后端|中间件|幂等|并发|缓存|鉴权|回调|FN-\d{3}")
BUZZ = re.compile(r"赋能|抓手|闭环|拉通|底层逻辑|顶层设计|降本增效|全链路|组合拳|一站式|新质生产力|高质量发展|行业领先|业界领先")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
ABSOLUTE = re.compile(r"国家级|最高级|最佳|最好|最优|最大|最强|最先进|最低价|唯一|首个|首选|顶级|极致|绝对|万能|百分之百|100%|零风险|史无前例|全网最|世界级|独家"
                      r"|第一(?!步|次|章|节|条|天|页|个月|季度|时间|眼|行|批|周|期|轮|阶段|类|项|方面)")
HEAD_PAREN = re.compile(r"[（(][^）)]+[）)]")
CHAPTER_KEYS = ("id", "heading", "features", "entry", "steps", "rules")

DOCS = ("proposal", "requirements", "manual", "confirmation", "agreement", "copy", "article")
CLIENT_DOCS = ("proposal", "requirements", "manual", "confirmation")


class Finding(NamedTuple):
    sev: str
    rule: str
    where: str
    message: str
    snippet: str = ""

    def __str__(self) -> str:
        tail = f"：{self.snippet}" if self.snippet else ""
        return f"{self.sev} {self.rule} {self.where} {self.message}{tail}"


class Item(NamedTuple):
    where: str
    text: str
    kind: str = "body"  # body | heading | caption


def mask(text: str) -> str:
    """Blank out code, URLs and paths so punctuation checks do not fire on them (keeps positions)."""
    def blank(m: re.Match) -> str:
        return " " * len(m.group(0))
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    for pattern in (r"`[^`\n]*`", r"https?://[^\s)）]+", r"\]\([^)\n]*\)", r"[A-Za-z]:\\[^\s，。；、）)]+"):
        text = re.sub(pattern, blank, text)
    return text


def snippet(text: str, m: re.Match, width: int = 14) -> str:
    return text[max(0, m.start() - width):m.end() + width].replace("\n", " ").strip()


def punctuation_findings(item: Item) -> list[Finding]:
    text, out = mask(item.text), []

    def add(sev: str, rule: str, message: str, pattern: str, flags: int = 0) -> None:
        for m in re.finditer(pattern, text, flags):
            out.append(Finding(sev, rule, item.where, message, snippet(text, m)))

    add("WARN", "P01", "中文句子里的标点用全角（，；！？）", rf"[{CJK}][,;!?]")
    add("WARN", "P01", "中文句子里的句号、冒号、括号用全角", rf"[{CJK}]\.(?=\s|$|[{CJK}])|[{CJK}]:(?![\d/])|[{CJK}]\(|\)[{CJK}]")
    add("WARN", "P02", "省略号写成“……”（六个点，占两个字位置）", r"(?<![.\d])\.{3,6}(?!\.)|。{3,}|(?<!…)…(?!…)")
    add("WARN", "P03", "破折号写成“——”，不写“--”；单个“—”只用于标起止（北京—上海，GB/T 15834 4.13），其余改成“——”", rf"[{CJK}]\s?(?:--|—)\s?[{CJK}]")
    add("WARN", "P04", "省略号不与“等”“等等”“什么的”同用（GB/T 15834 A.9.2）", r"(?:……|…)\s*(?:等等|等|什么的)|(?:等等|等)\s*……")
    add("WARN", "P05", "“等”“等等”之前不加顿号（B.1.2）", r"、等(?:等)?(?=[，。；：！？、）\s]|$)")
    add("WARN", "P06", "中文引文用“ ”，不用英文直引号", rf'"[^"\n]*[{CJK}][^"\n]*"')
    add("WARN", "N01", "数值范围两端单位相同时，万、亿、百分号不能只留一端（写“9亿~16亿”“15%~30%”，GB/T 15835 5.1.3）",
        r"\d(?:\.\d+)?\s*[~～—–-]\s*\d+(?:\.\d+)?\s*(?:%|％|万|亿)")
    add("WARN", "N02", "日期写“2026年11月2日”或“2026-11-02”（5.1.4）", r"(?<!\d)\d{4}[./]\d{1,2}[./]\d{1,2}(?!\d)")
    add("WARN", "N03", "四位年份不简写成两位（5.1.4）", r"(?<!\d)\d{2}年(?=\d{1,2}月)")
    add("WARN", "N04", "纯小数要写出个位的 0（5.1.2）", r"(?<![\w.])\.\d+(?![\w.])")
    add("WARN", "N05", "汉字与阿拉伯数字不混写（写“四千”或“4000”，不写“4千”，5.3）",
        r"(?<![\d.])[1-9]\d*[百千](?!米|克|瓦|分|万|亿|字|兆|赫|伏|焦|帕|欧|吉|卡|人次)")
    add("WARN", "B01", "课程、课题、赛事、活动、证照名称不用书名号（A.13.1）",
        rf"《[^》]{{1,20}}(?:课程|课题|大赛|比赛|研讨会|联欢会|发布会|活动|会议)》|《[^》]{{1,12}}证》")
    if EMOJI.search(text):
        out.append(Finding("WARN", "F01", item.where, "不用 emoji 和装饰符号", EMOJI.search(text).group(0)))
    return out


def placeholder_findings(item: Item, final: bool) -> list[Finding]:
    text, out = mask(item.text), []
    for m in PLACEHOLDER.finditer(text):
        out.append(Finding("ERROR", "X01", item.where, "占位文字交付前必须清掉", snippet(text, m)))
    for m in GAP.finditer(text):
        out.append(Finding("ERROR" if final else "WARN", "X02", item.where, "缺口标记交给客户或发布前必须处理（补事实，或改成有依据的说法）", snippet(text, m)))
    return out


class Gate(NamedTuple):
    """What the project has switched on (config/documents.json estimate), counted only when its evidence is complete."""
    workdays: bool = False
    quote: bool = False
    findings: tuple = ()


_blank = et.is_blank


def estimate_gate(documents, quote, config_name: str = "config/documents.json") -> Gate:
    """Both switches default to off. A switch counts only with who asked, when and in what words; the quote also needs a human quotation."""
    findings: list[Finding] = []

    def error(where: str, message: str) -> None:
        findings.append(Finding("ERROR", "C12", where, message))

    est = documents.get("estimate") if isinstance(documents, dict) and isinstance(documents.get("estimate"), dict) else {}
    if isinstance(documents, dict) and not est and documents.get("amounts") is True:
        findings.append(Finding("WARN", "C12", config_name, "旧配置 amounts: true 没有 estimate 开关和要求证据，按人日与报价都关闭处理"))
    for key in ("workdays", "quote"):
        if key in est and not isinstance(est[key], bool):
            error(config_name, f"estimate.{key} 须是 true 或 false，按关闭处理")
    workdays, quote_on = est.get("workdays") is True, est.get("quote") is True
    if quote_on and not workdays:
        error(config_name, "estimate.quote 为 true 时 estimate.workdays 必须同时为 true（报价基于人日），按都关闭处理")
        return Gate(False, False, tuple(findings))
    if workdays or quote_on:
        missing = [k for k in ("requested_by", "requested_at", "request_note") if _blank(est.get(k))]
        if missing:
            error(config_name, "estimate 开关已打开但缺 " + "、".join(missing) + "：没有谁、何时、用什么原话要求的证据，开关不算打开，按都关闭处理")
            return Gate(False, False, tuple(findings))
        if et.not_a_person(str(est.get("requested_by"))):
            error(config_name, f"estimate.requested_by“{est.get('requested_by')}”不是具体的人：写要求的用户或客户的姓名或角色，按都关闭处理")
            return Gate(False, False, tuple(findings))
    if quote_on:
        problems: list[str] = []
        if quote is None:
            problems.append("没有 quote.json：等待人工报价，把它列为用户待办并停下，不自拟、不暂估、不套用示例值")
        elif not isinstance(quote, dict):
            problems.append("quote.json 须是对象")
        else:
            price = quote.get("unit_price")
            if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                problems.append("缺大于 0 的 unit_price，且只能来自人工报价单")
            missing = [k for k in ("provided_by", "provided_at", "request_note", "evidence") if _blank(quote.get(k))]
            if missing:
                problems.append("缺人工证据字段 " + "、".join(missing))
            if not _blank(quote.get("provided_by")) and et.not_a_person(str(quote["provided_by"])):
                problems.append(f"provided_by“{quote['provided_by']}”不是具体的人，报价只能由人工提供")
            if not _blank(quote.get("evidence")) and len(json.dumps(quote["evidence"], ensure_ascii=False)) <= 10 and et.not_a_person(str(quote["evidence"])):
                problems.append("evidence 只有一个示例、暂估或默认之类的词，写提供数字的原话或来源文件路径")
        for problem in problems:
            error("quote.json", problem + "；报价字样按未开启处理")
        if problems:
            return Gate(workdays, False, tuple(findings))
    return Gate(workdays, quote_on, tuple(findings))


def client_findings(item: Item, doc: str, gate: Gate | None = None, allow_terms: tuple = ()) -> list[Finding]:
    gate = gate or Gate()
    text, out = mask(item.text), []
    for m in OTHER_FILES.finditer(text):
        out.append(Finding("ERROR", "C01", item.where, "客户文件不提及其他文件，内容直接写进本文件", snippet(text, m)))
    for m in POINTERS.finditer(text):
        out.append(Finding("WARN", "C01", item.where, "“详见/参见”如果指向别的文件，改成直接写内容", snippet(text, m)))
    if doc in ESTIMATE_DOCS:
        for m in WORKDAY_TERMS.finditer(text):
            if not gate.workdays and m.group(0) not in allow_terms:
                out.append(Finding("ERROR", "C02", item.where, "没有明确要求就不写人日、工时：打开 estimate.workdays 并带要求证据才写，数字不得自拟，缺依据停下问用户", snippet(text, m)))
        for m in QUOTE_TERMS.finditer(text):
            if not gate.quote and m.group(0) not in allow_terms:
                out.append(Finding("ERROR", "C02", item.where, "没有明确要求就不写预算、报价和付款：打开 estimate.quote 并有人工报价单才写，数字不得自拟，缺依据停下问用户", snippet(text, m)))
        if not gate.quote:
            for m in MONEY.finditer(text):
                out.append(Finding("WARN", "C02", item.where, "确认这笔金额是客户业务里的规则；本项目的价格没有人工报价单就不能写", snippet(text, m)))
    elif doc in CLIENT_DOCS and not gate.workdays:
        for m in SURE_WORKDAY_TERMS.finditer(text):
            if m.group(0) not in allow_terms:
                out.append(Finding("ERROR", "C02", item.where, "使用说明和确认表里不写人日：人日只在明确要求的功能清单里出现", snippet(text, m)))
    for m in JARGON.finditer(text):
        out.append(Finding("WARN", "C03", item.where, "客户看不懂的技术词，换成客户的话；功能编号不出现在客户文件里", snippet(text, m)))
    for m in BUZZ.finditer(text):
        out.append(Finding("WARN", "C04", item.where, "空话回到具体事实（17 › 三、中文词汇）", snippet(text, m)))
    if EMOJI.search(text):
        out.append(Finding("ERROR", "F01", item.where, "客户文件不用 emoji、图标和装饰", EMOJI.search(text).group(0)))
    for m in re.finditer(r"(?i)(?:password|secret|token|密码|密钥|私钥)\s*[:：=]\s*\S+", text):
        out.append(Finding("ERROR", "C05", item.where, "密钥、密码不进表格，只问“已通过安全渠道发送 / 尚未发送”", snippet(text, m)))
    if item.kind == "heading" and HEAD_PAREN.search(text):
        out.append(Finding("ERROR", "C06", item.where, "标题不写括号说明，说明放进正文或表题", text.strip()))
    if item.kind == "caption" and text.strip().endswith("。"):
        out.append(Finding("WARN", "C07", item.where, "表题是短语，末尾不加句号（A.1）", text.strip()))
    if doc == "manual" and item.kind == "body" and re.match(r"^\s*(?:您)?(?:可以|需要|应该|能够)", text):
        out.append(Finding("WARN", "C08", item.where, "步骤写祈使句：动词开头，先写条件和位置", text.strip()[:20]))
    return out


def agreement_findings(item: Item) -> list[Finding]:
    text, out = mask(item.text), []
    for m in re.finditer(r"最终解释权|解释权归", text):
        out.append(Finding("ERROR", "A01", item.where, "不写“最终解释权”，规则本身写完整", snippet(text, m)))
    for m in re.finditer(r"以(?:门店|商家|官方|实际)?(?:实际|为准)", text):
        out.append(Finding("WARN", "A02", item.where, "“以实际为准”这类无法核对的话改成具体规则", snippet(text, m)))
    return out


def copy_findings(item: Item) -> list[Finding]:
    text, out = mask(item.text), []
    for m in ABSOLUTE.finditer(text):
        out.append(Finding("WARN", "M01", item.where, "绝对化用语需要可核实依据，否则不用（广告法第九条第三项；限定时间地域的销量等事实、商品名称商标含有的词等情形除外）", snippet(text, m)))
    for m in re.finditer(r"手慢无|恭喜您|治愈|根治|包治|保过|保本", text):
        out.append(Finding("WARN", "M02", item.where, "不写假紧迫、客套和无法兑现的承诺", snippet(text, m)))
    return out


def structural_findings(data, doc: str) -> list[Finding]:
    """Checks that need the JSON structure: tables need captions, manual chapters need their fields."""
    out: list[Finding] = []
    if not isinstance(data, dict):
        return out
    for si, sec in enumerate(data.get("sections", []) if isinstance(data.get("sections"), list) else []):
        for bi, block in enumerate(sec.get("blocks", []) if isinstance(sec, dict) else []):
            if isinstance(block, dict) and block.get("type") in ("table", "matrix") and not block.get("caption"):
                out.append(Finding("ERROR", "C09", f"sections[{si}].blocks[{bi}]", "每张表必须有表题（caption）"))
    if doc == "proposal" and isinstance(data.get("sections"), list):
        keys = {s.get("key") for s in data["sections"] if isinstance(s, dict)}
        for key, label in (("background", "项目背景与需求分析"), ("solution", "解决方案"), ("deliverables", "交付内容")):
            if key not in keys:
                out.append(Finding("ERROR", "C10", "sections", f"缺少章节「{label}」（key = {key}）"))
    if doc == "requirements" and isinstance(data.get("sections"), list):
        keys = {s.get("key") for s in data["sections"] if isinstance(s, dict)}
        for key, label in (("background", "项目背景"), ("goals", "建设目标"), ("scope", "范围与使用者"), ("requirements", "需求清单"),
                           ("rules", "业务规则与约束"), ("acceptance", "验收标准"), ("open", "需要客户确认的事项")):
            if key not in keys:
                out.append(Finding("ERROR", "C10", "sections", f"缺少章节「{label}」（key = {key}）"))
    if doc == "manual" and isinstance(data.get("chapters"), list):
        for ci, chapter in enumerate(data["chapters"]):
            for key in CHAPTER_KEYS:
                if isinstance(chapter, dict) and not chapter.get(key):
                    out.append(Finding("ERROR", "C11", f"chapters[{ci}]", f"章节缺少 {key}"))
    return out


def json_items(data, path: str = "$", key: str = "", parent_type: str = "") -> list[Item]:
    items: list[Item] = []
    if isinstance(data, str):
        kind = "heading" if key in ("heading", "title") and parent_type != "root" else ("caption" if key == "caption" else "body")
        if parent_type == "sub" and key == "text":
            kind = "heading"
        items.append(Item(path, data, kind))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            items += json_items(value, f"{path}[{i}]", key, parent_type)
    elif isinstance(data, dict):
        block_type = data.get("type", "") if isinstance(data.get("type"), str) else ""
        has_blocks = isinstance(data.get("blocks"), list) or "heading" in data
        for k, value in data.items():
            ptype = block_type or ("section" if has_blocks else parent_type)
            if path == "$" and k == "title":
                items.append(Item(f"{path}.{k}", str(value), "body"))
                continue
            items += json_items(value, f"{path}.{k}", k, ptype)
    return items


def text_items(text: str) -> list[Item]:
    items: list[Item] = []
    heading = re.compile(r"^\s*(?:#{1,6}\s+|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）|\d+\.\s)")
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip():
            continue
        kind = "heading" if heading.match(line) and len(line.strip()) <= 40 else ("caption" if re.match(r"^\s*表\s*\d*\s", line) else "body")
        items.append(Item(f"第 {n} 行", line, kind))
    return items


def check_items(items: list[Item], doc: str | None, final: bool = False, gate: Gate | None = None, allow_terms: tuple = ()) -> list[Finding]:
    """gate: what the project switched on for workdays and quote; None = both off (the default of the policy)."""
    out: list[Finding] = []
    for item in items:
        out += punctuation_findings(item)
        out += placeholder_findings(item, final)
        if doc in CLIENT_DOCS:
            out += client_findings(item, doc, gate, allow_terms)
        if doc == "agreement":
            out += agreement_findings(item)
        if doc in ("copy", "article"):
            out += copy_findings(item)
    return out


def check_title(items: list[Item], limit: int) -> list[Finding]:
    first = next((i for i in items if i.text.strip()), None)
    if first is None:
        return []
    title = re.sub(r"^\s*#+\s*", "", first.text).strip()
    if len(title) > limit:
        return [Finding("ERROR", "T01", first.where, f"标题 {len(title)} 个字，超过 {limit} 个字的限制", title[:20])]
    return []


def load_items(path: Path) -> tuple[list[Item], object | None]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        return json_items(data), data
    return text_items(raw), None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--doc", choices=DOCS, help="文件类型；不写只查标点、数字、日期和占位")
    ap.add_argument("--final", action="store_true", help="交付版：[待核实：…] 缺口也算错误")
    ap.add_argument("--max-title", type=int, help="第一行标题的字数上限（例如公众号接口文档写明标题不超过 32 个字）")
    ap.add_argument("--project-config", type=Path,
                    help="项目状态根的 config/documents.json（读其中的 estimate）；也可设环境变量 LUZ_DOCUMENTS_CONFIG；"
                         "检查 <状态根>/data/client/ 下的文件时自动找 <状态根>/config/documents.json；都没有就按人日与报价都关闭")
    ap.add_argument("--quote-file", type=Path, help="人工报价单 quote.json；默认取被检文件同目录的 quote.json")
    ap.add_argument("--allow-term", action="append", default=[], metavar="词",
                    help="放行业务本身就有的词（例如“工时”），可重复；人日与报价的开关不受它影响")
    args = ap.parse_args(argv)
    path = Path(args.file)
    if not path.is_file():
        print(f"FAIL: 找不到文件 {path}", file=sys.stderr)
        return 2
    try:
        items, data = load_items(path)
    except (OSError, ValueError) as exc:
        print(f"FAIL: 读不了 {path}: {exc}", file=sys.stderr)
        return 2
    config = args.project_config or (Path(os.environ["LUZ_DOCUMENTS_CONFIG"]) if os.environ.get("LUZ_DOCUMENTS_CONFIG") else None)
    here = path.resolve().parent
    if config is None and here.name == "client" and here.parent.name == "data":
        guess = here.parent.parent / "config" / "documents.json"
        config = guess if guess.is_file() else None
    try:
        documents = json.loads(config.read_text(encoding="utf-8-sig")) if config else None
        quote_path = args.quote_file or (here / "quote.json" if (here / "quote.json").is_file() else None)
        quote = json.loads(quote_path.read_text(encoding="utf-8-sig")) if quote_path else None
    except (OSError, ValueError) as exc:
        print(f"FAIL: 读不了估算配置或报价单: {exc}", file=sys.stderr)
        return 2
    gate = estimate_gate(documents, quote, str(config) if config else "config/documents.json") if args.doc in CLIENT_DOCS else Gate()
    if args.doc in ESTIMATE_DOCS:
        print(f"估算开关: workdays={'开' if gate.workdays else '关'}，quote={'开' if gate.quote else '关'}（{config if config else '未提供配置，默认关闭'}）")
    findings = list(gate.findings) + check_items(items, args.doc, args.final, gate, tuple(args.allow_term))
    if data is not None:
        findings += structural_findings(data, args.doc or "")
    if args.max_title:
        findings += check_title(items, args.max_title)
    for f in findings:
        print(f)
    errors = sum(1 for f in findings if f.sev == "ERROR")
    print(f"{'FAIL' if errors else 'PASS'}: {path.name} · {errors} 个错误 · {len(findings) - errors} 个提示")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
