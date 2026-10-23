#!/usr/bin/env python3
"""Fetch recent arXiv papers related to moduli in algebraic geometry (v1.3)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API_URL = "https://export.arxiv.org/api/query"
ATOM = "http://www.w3.org/2005/Atom"
ARXIV = "http://arxiv.org/schemas/atom"
DEFAULT_TERMS = (
    "moduli", "moduli space", "moduli spaces", "moduli stack", "moduli stacks",
    "stable map", "stable maps", "hilbert scheme", "hilbert schemes",
    "gromov-witten", "gromov witten", "donaldson-thomas", "quiver variety",
)
DEFAULT_CATEGORIES = ("math.AG",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每周筛选 arXiv 代数几何模空间论文并生成 Markdown 摘要。")
    parser.add_argument("--days", type=int, default=7, help="回溯天数，默认 7")
    parser.add_argument("--output", type=Path, help="报告文件路径，默认 reports/YYYY-MM-DD.md")
    parser.add_argument("--state", type=Path, default=Path("data/seen.json"), help="已处理论文 ID 文件")
    parser.add_argument("--max-results", type=int, default=1000, help="最多读取的候选论文数；脚本按页请求")
    parser.add_argument("--categories", default=",".join(DEFAULT_CATEGORIES), help="逗号分隔的 arXiv 分类")
    parser.add_argument("--include-seen", action="store_true", help="也在本次报告中包含此前已处理的论文")
    return parser.parse_args()


def fetch_entries(categories: list[str], start: date, end: date, max_results: int) -> list[dict[str, str | list[str]]]:
    category_query = " OR ".join(f"cat:{category.strip()}" for category in categories if category.strip())
    query = f"({category_query})" if " OR " in category_query else category_query
    papers = []
    lower, upper = datetime.combine(start, datetime.min.time(), timezone.utc), datetime.combine(end + timedelta(days=1), datetime.min.time(), timezone.utc)
    page_size = 100
    seen_ids: set[str] = set()
    for offset in range(0, max_results, page_size):
        page_limit = min(page_size, max_results - offset)
        params = {
            "search_query": query,
            "start": str(offset),
            "max_results": str(page_limit),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        request = urllib.request.Request(
            f"{API_URL}?{urllib.parse.urlencode(params)}",
            headers={"User-Agent": "ArxivModuliDigest/1.3 (weekly research digest)"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            root = ET.fromstring(response.read())
        entries = root.findall(f"{{{ATOM}}}entry")
        if not entries:
            break
        for entry in entries:
            published = entry.findtext(f"{{{ATOM}}}published", "")
            try:
                published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                continue
            if not lower <= published_at < upper:
                continue
            raw_id = entry.findtext(f"{{{ATOM}}}id", "")
            paper_id = re.sub(r"v\d+$", "", raw_id.rsplit("/", 1)[-1])
            if paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            authors = [a.findtext(f"{{{ATOM}}}name", "") for a in entry.findall(f"{{{ATOM}}}author")]
            updated_text = entry.findtext(f"{{{ATOM}}}updated", published)
            try:
                updated_at = datetime.fromisoformat(updated_text.replace("Z", "+00:00"))
            except ValueError:
                updated_at = published_at
            categories_found = [c.attrib.get("term", "") for c in entry.findall(f"{{{ARXIV}}}primary_category")]
            categories_found += [c.attrib.get("term", "") for c in entry.findall(f"{{{ATOM}}}category")]
            papers.append({
                "id": paper_id,
                "url": f"https://arxiv.org/abs/{paper_id}",
                "title": " ".join(entry.findtext(f"{{{ATOM}}}title", "").split()),
                "abstract": " ".join(entry.findtext(f"{{{ATOM}}}summary", "").split()),
                "authors": authors,
                "published": published_at.date().isoformat(),
                "updated": updated_at.date().isoformat(),
                "categories": list(dict.fromkeys(categories_found)),
            })
        if len(entries) < page_limit:
            break
        time.sleep(3)
    return papers


def score_paper(paper: dict[str, str | list[str]]) -> tuple[int, list[str]]:
    title = str(paper["title"]).lower()
    abstract = str(paper["abstract"]).lower()
    combined = f"{title} {abstract}"
    matched = [term for term in DEFAULT_TERMS if term in combined]
    score = sum(3 if term in title else 1 for term in matched)
    if "moduli" in title:
        score += 3
    return score, matched


def short_overview(abstract: str, limit: int = 480) -> str:
    """Use the paper's own opening sentences as a concise, non-generated overview."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", abstract.strip())
    overview = " ".join(sentences[:2]).strip() or abstract.strip()
    if len(overview) > limit:
        overview = overview[: limit - 1].rsplit(" ", 1)[0] + "…"
    return overview


def make_report(papers: list[dict[str, str | list[str]]], start: date, end: date) -> str:
    lines = [f"# arXiv 代数几何模空间周报 ({start.isoformat()} 至 {end.isoformat()})", "", f"共找到 **{len(papers)}** 篇候选论文。", ""]
    if not papers:
        lines.append("本周期没有匹配的论文。")
        return "\n".join(lines) + "\n"
    for paper in papers:
        score, matched = score_paper(paper)
        authors = ", ".join(paper["authors"][:5])
        if len(paper["authors"]) > 5:
            authors += " et al."
        tags = ", ".join(matched) if matched else "分类匹配"
        lines.extend([
            f"## [{paper['title']}]({paper['url']})",
            f"- **日期：** {paper['published']}  |  **相关度：** {score}  |  **分类：** {', '.join(paper['categories'])}",
            f"- **作者：** {authors}",
            f"- **匹配主题：** {tags}",
            f"- **概述（原摘要节选）：** {short_overview(str(paper['abstract']))}",
            "",
        ])
    lines.extend(["---", "概述取自论文原摘要前两句，未使用生成式模型；建议点击标题查看原文及完整摘要。", ""])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.days < 1 or args.max_results < 1:
        print("--days 和 --max-results 必须为正数。", file=sys.stderr)
        return 2
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=args.days - 1)
    try:
        all_papers = fetch_entries([c.strip() for c in args.categories.split(",")], start, end, args.max_results)
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
        print(f"读取 arXiv API 失败：{exc}", file=sys.stderr)
        return 1

    state_path = args.state
    seen: set[str] = set()
    if state_path.exists():
        try:
            seen = set(json.loads(state_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError):
            print(f"警告：无法读取去重记录 {state_path}，将重新建立。", file=sys.stderr)
    fresh = [p for p in all_papers if args.include_seen or p["id"] not in seen]
    relevant = [p for p in fresh if score_paper(p)[0] > 0]
    relevant.sort(key=lambda p: str(p["published"]), reverse=True)

    output = args.output or Path("reports") / f"{end.isoformat()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(make_report(relevant, start, end), encoding="utf-8")
    web_data = {
        "version": "1.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "papers": sorted(relevant, key=lambda p: str(p["published"]), reverse=True),
    }
    Path("papers.json").write_text(json.dumps(web_data, ensure_ascii=False, indent=2), encoding="utf-8")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(sorted(seen | {str(p["id"]) for p in all_papers}), indent=2), encoding="utf-8")
    print(f"候选论文 {len(all_papers)} 篇，主题匹配 {len(relevant)} 篇。报告：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
