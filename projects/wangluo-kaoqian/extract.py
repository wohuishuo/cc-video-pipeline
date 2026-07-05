#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 计网考前速背.md 解析成结构化 JSON（按 PART 分组，每条含英文原题/中文结论/表格等）。
只解析一次性写好的固定模板，不追求通用性。
"""
import json
import re
from pathlib import Path

SRC = Path(r"C:\Users\艾莉\作业\hm68\BIT-CS-UnderGraduate\大三下\计算机网络\test paper\计网考前速背.md")
OUT = Path(__file__).parent / "parts.json"


def clean(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    return s.strip()


def delatex(s: str) -> str:
    """把行内 LaTeX 转成人话，给配音稿/屏幕都用得上的朴素写法。"""
    for _ in range(3):  # \frac 可能嵌套，多跑几轮
        s = re.sub(r"\\text\{(.+?)\}", r"\1", s)
        s = re.sub(r"\\frac\{(.+?)\}\{(.+?)\}", r"(\1)/(\2)", s)
    s = s.replace("\\cdot", "×").replace("\\quad", " ")
    s = s.replace("$$", "").replace("$", "")
    s = re.sub(r"[{}]", "", s)
    return s


def strip_quote_marker(line: str) -> str:
    # "> **[2013 填空]** Suppose ..." -> "Suppose ..."
    line = line.lstrip(">").strip()
    line = re.sub(r"^\*\*\[.*?\]\*\*\s*", "", line)
    return clean(line)


def main():
    text = SRC.read_text(encoding="utf-8")
    # 按 PART 切
    part_blocks = re.split(r"\n## PART (\d+)｜(.+?)\n", text)
    # part_blocks[0] 是PART1之前的前言，丢弃；之后是 (num, title, body) 三元组循环
    parts = []
    for i in range(1, len(part_blocks), 3):
        num, title, body = part_blocks[i], part_blocks[i + 1], part_blocks[i + 2]
        entries = []
        # 按 ### 切条目
        entry_blocks = re.split(r"\n### (.+?)\n", body)
        for j in range(1, len(entry_blocks), 2):
            header, ebody = entry_blocks[j], entry_blocks[j + 1]
            m = re.match(r"(\S+?)｜(.+)", header.strip())
            eid, etitle_full = (m.group(1), m.group(2)) if m else (header.strip(), header.strip())
            # 英文短标题（去掉中文括注）
            etitle_en = re.sub(r"（.+?）\s*$", "", etitle_full).strip()
            etitle_zh = ""
            mm = re.search(r"（(.+?)）\s*$", etitle_full)
            if mm:
                etitle_zh = mm.group(1)

            # 英文原题：只取条目开头第一段连续的 "> " 行（后面 ⚠️ 提示另起一段不要）
            first_block_m = re.match(r"(?:\s*\n)*((?:>.*\n)+)", ebody)
            quote_lines = re.findall(r"^>\s?(.*)$", first_block_m.group(1), flags=re.M) if first_block_m else []
            question_en = " ".join(strip_quote_marker(l) for l in quote_lines if l.strip())

            # 答案行 ✅ **...**
            ans_m = re.search(r"✅\s*\*\*(.+?)\*\*", ebody)
            answer = clean(ans_m.group(1)) if ans_m else ""

            # 全部"结论：..."（可能不止一条，且有时跨 ** 在行内）
            concl = re.findall(r"\*\*结论[：:](.+?)\*\*", ebody, flags=re.S)
            conclusion = " ".join(clean(c) for c in concl)

            # 根据 / 例子
            basis_m = re.search(r"根据[：:](.+?)(?:\n\n|\n例子|\Z)", ebody, flags=re.S)
            basis = clean(basis_m.group(1)) if basis_m else ""
            example_m = re.search(r"例子[：:](.+?)(?:\n\n|\Z)", ebody, flags=re.S)
            example = clean(example_m.group(1)) if example_m else ""

            # markdown 表格（如果有）—— 要先算出来，后面的兜底逻辑依赖它
            table_m = re.search(r"((?:\|.+\|\n)+)", ebody)
            table = None
            if table_m:
                rows = [r.strip() for r in table_m.group(1).strip().splitlines()]
                cells = [
                    [c.strip() for c in row.strip("|").split("|")]
                    for row in rows if not re.match(r"^\|?\s*-{2,}", row)
                ]
                if len(cells) >= 2:
                    table = {"header": cells[0], "rows": cells[1:]}

            # 没有"结论："的条目（多是计算题）：用 ✅ 答案行之后、到 根据/例子/表格/章节末
            # 之间的自由文本兜底，去掉列表符号后拼成一句话叙述。
            if not conclusion and ans_m:
                tail = ebody[ans_m.end():]
                tail = re.split(r"\n根据[：:]|\n例子[：:]|\n\|.+\|\n", tail)[0]
                lines = [
                    re.sub(r"^[-\d.、]+\s*", "", clean(ln.strip()))
                    for ln in tail.splitlines()
                    if ln.strip() and not ln.strip().startswith(("|", ">", "#"))
                ]
                conclusion = " ".join(lines).strip()

            # 公式速查类条目（没有 ✅，没有"结论："）：取整段正文兜底
            if not conclusion and not ans_m:
                body_no_table = re.sub(r"(?:\|.+\|\n?)+", "", ebody)
                lines = [
                    delatex(re.sub(r"^[-\d.、]+\s*", "", clean(ln.strip())))
                    for ln in body_no_table.splitlines()
                    if ln.strip() and not ln.strip().startswith(("|", ">", "#"))
                ]
                conclusion = " ".join(lines).strip()

            # 纯表格类条目（如"窗口大小对比"）：从表格自己拼一句话
            if not conclusion and table:
                rows_txt = "；".join(
                    f"{table['header'][0]} {r[0]}: " + "，".join(
                        f"{h}={c}" for h, c in zip(table["header"][1:], r[1:]))
                    for r in table["rows"]
                )
                conclusion = clean(rows_txt)

            entries.append({
                "id": eid,
                "title_en": etitle_en,
                "title_zh": etitle_zh,
                "question_en": question_en,
                "answer": answer,
                "conclusion": conclusion,
                "basis": basis,
                "example": example,
                "table": table,
            })
        parts.append({"part_no": int(num), "part_title": title.strip(), "entries": entries})

    OUT.write_text(json.dumps(parts, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(p["entries"]) for p in parts)
    print(f"[ok] {len(parts)} parts, {total} entries -> {OUT}")
    for p in parts:
        print(f"  PART {p['part_no']} {p['part_title']}: {len(p['entries'])} 题")


if __name__ == "__main__":
    main()
