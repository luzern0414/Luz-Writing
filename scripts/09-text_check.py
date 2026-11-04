#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文文字的机器可判断部分：标点、数字、日期（GB/T 15834、15835），以及客户文件、协议和营销文案各自的硬性写法。

  py -X utf8 scripts/09-text_check.py <文件> [--doc proposal|manual|confirmation|agreement|copy|article] [--final] [--max-title N]

文件可以是 .txt / .md 正文，也可以是 Luz-Project 的 proposal.json / manual.json（逐个字符串检查，标题与表题按位置识别）。
没有 --doc 时只查标点、数字、日期、占位。ERROR 会让命令失败，WARN 只提示；它只找能机器判断的问题，
事实、依据、读者能否看懂仍要人读。规则出处见 references/18-client-documents.md 与 19-chinese-text-standards.md。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import NamedTuple
from pathlib import Path

CJK = "一-鿿"
# 与项目模式客户文件校验同名的规则：方案不提及其他文件、不留占位。
OTHER_FILES = re.compile(r"《[^》]{2,16}》|配套文件|见功能清单|见系统架构图|见业务逻辑确认表")
POINTERS = re.compile(r"详见|参见|另见|请参阅|参阅")
PLACEHOLDER = re.compile(r"待补充|TODO|TBD|占位符|占位文字|xxx|lorem ipsum|××|【请填写[^】]*】", re.I)
GAP = re.compile(r"\[待核实[:：][^\]]*\]")
PRICE_TERMS = re.compile(r"报价|单价|总价|人天|工时|含税|首付款|尾款|付款节点|付款方式|项目预算|开发费用|实施费用|合同金额")
MONEY = re.compile(r"[¥￥]\s*\d|人民币\s*\d|RMB\s*\d", re.I)
JARGON = re.compile(r"\b(?:API|SDK|JSON|SQL|Redis|MySQL|Docker|Kubernetes|K8s|HTTPS?|RESTful|WebSocket|Nginx)\b"
                    r"|接口|数据库|表结构|微服务|前端|后端|中间件|幂等|并发|缓存|鉴权|回调|FN-\d{3}")
BUZZ = re.compile(r"赋能|抓手|闭环|拉通|底层逻辑|顶层设计|降本增效|全链路|组合拳|一站式|新质生产力|高质量发展|行业领先|业界领先")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
ABSOLUTE = re.compile(r"国家级|最高级|最佳|最好|最优|最大|最强|最先进|最低价|唯一|首个|首选|顶级|极致|绝对|万能|百分之百|100%|零风险|史无前例|全网最|世界级|独家"
                      r"|第一(?!步|次|章|节|条|天|页|个月|季度|时间|眼|行|批|周|期|轮|阶段|类|项|方面)")
HEAD_PAREN = re.compile(r"[（(][^）)]+[）)]")
CHAPTER_KEYS = ("id", "heading", "features", "entry", "steps", "rules")

DOCS = ("proposal", "manual", "confirmation", "agreement", "copy", "article")
CLIENT_DOCS = ("proposal", "manual", "confirmation")


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
    add("WARN", "P03", "破折号写成“——”，不写单个“—”或“--”", rf"[{CJK}]\s?(?:--|—)\s?[{CJK}]")
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


def client_findings(item: Item, doc: str) -> list[Finding]:
    text, out = mask(item.text), []
    for m in OTHER_FILES.finditer(text):
        out.append(Finding("ERROR", "C01", item.where, "客户文件不提及其他文件，内容直接写进本文件", snippet(text, m)))
    for m in POINTERS.finditer(text):
        out.append(Finding("WARN", "C01", item.where, "“详见/参见”如果指向别的文件，改成直接写内容", snippet(text, m)))
    if doc == "proposal":
        for m in PRICE_TERMS.finditer(text):
            out.append(Finding("ERROR", "C02", item.where, "方案里不写价格、工时和付款，价格只在功能清单的报价清单里", snippet(text, m)))
        for m in MONEY.finditer(text):
            out.append(Finding("WARN", "C02", item.where, "确认这笔金额是客户业务里的规则，不是本项目的价格", snippet(text, m)))
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


def check_items(items: list[Item], doc: str | None, final: bool = False) -> list[Finding]:
    out: list[Finding] = []
    for item in items:
        out += punctuation_findings(item)
        out += placeholder_findings(item, final)
        if doc in CLIENT_DOCS:
            out += client_findings(item, doc)
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
    findings = check_items(items, args.doc, args.final)
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
