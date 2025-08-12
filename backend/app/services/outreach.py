from __future__ import annotations

import datetime
import re
from typing import List, Optional, Dict, Any, Tuple

import requests
from fastapi import HTTPException

from app.core.startup import get_client
from app.core.config import settings
from app.schemas.outreach import OutreachItem


def _build_queries(last_name: str, first_name: str, company: Optional[str], department: Optional[str]) -> List[str]:
    # 氏名のバリアント（日本/英語順、スペースあり/なし）
    name_variants = [
        f"{last_name} {first_name}",
        f"{first_name} {last_name}",
        f"{last_name}{first_name}",
    ]
    base_terms_sets: List[List[str]] = []
    for name in name_variants:
        terms = [name]
        if company:
            terms.append(company)
        if department:
            terms.append(department)
        base_terms_sets.append(terms)

    # 外部発信に関する日本語キーワード
    keyword_sets = [
        ["登壇", "講演", "講師"],
        ["寄稿", "インタビュー", "執筆"],
        ["書籍", "出版", "著書"],
        ["論文", "学会", "研究発表"],
        ["keynote", "talk", "interview", "publication"],
    ]

    queries: List[str] = []
    for base_terms in base_terms_sets:
        base = " ".join([t for t in base_terms if t])
        for ks in keyword_sets:
            queries.append(base + " " + " ".join(ks))
        # 汎用
        queries.append(base + " 外部発信 実績")
    # 重複除去を保った順序
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    return unique_queries


def _google_cse_search(query: str, num: int = 10, timeout_sec: int = 15, site: Optional[str] = None) -> list[dict]:
    if not settings.google_cse_api_key or not settings.google_cse_cx:
        raise HTTPException(status_code=500, detail="GOOGLE_CSE_API_KEY/GOOGLE_CSE_CX is not configured")
    try:
        params = {
            "key": settings.google_cse_api_key,
            "cx": settings.google_cse_cx,
            "q": query,
            "num": num,
            "hl": "ja",
            "safe": "active",
        }
        if site:
            params["siteSearch"] = site
            params["siteSearchFilter"] = "i"  # include only
        resp = requests.get(settings.google_cse_endpoint, params=params, timeout=timeout_sec)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return items
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google CSE検索に失敗しました: {str(e)}")


def _normalize_google_results(results: list[dict], max_items: int = 30) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for r in results[:max_items]:
        link = r.get("link")
        title = r.get("title")
        snippet = r.get("snippet")
        display_link = r.get("displayLink")
        if not link:
            continue
        if "google.com" in link:
            continue
        normalized.append({
            "title": title or "",
            "link": link,
            "snippet": snippet or "",
            "source": display_link or "",
        })
    return normalized


def _classify_and_structure_with_gpt(name_variants: List[str], candidates: List[Dict[str, Any]], limit: int) -> Tuple[List[OutreachItem], int]:
    if not candidates:
        return [], 0

    client = get_client()
    # Use small reasoning to map links into the requested schema
    instruction = (
        f"以下の検索結果候補（title, link, snippet, source）を精査し、対象人物の外部発信（書籍/登壇/講演/寄稿/インタビュー/論文など）を最大{limit}件、"
        "JSONで返してください。人物名のバリアント、会社名、部署名と強く関連する候補を優先し、確度が低いものは除外。"
        "出力は items: OutreachItem[] とし、各要素は {{category: string, date: YYYY-MM-DD or null, title: string, details: url}}。"
        "categoryは 書籍/登壇/講演/寄稿/インタビュー/論文 のいずれかに近い値を用い、日本語で簡潔に。日付は判明すればISO形式。"
    )

    import json
    payload = json.dumps({"candidates": candidates}, ensure_ascii=False)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise data extraction agent that outputs strict JSON only."},
            {"role": "user", "content": (
                "対象人物バリアント: " + ", ".join(name_variants) + "\n" +
                instruction + "\n候補JSON:\n" + payload
            )},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "outreach_items",
                "schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": "string"},
                                    "date": {"type": ["string", "null"], "format": "date"},
                                    "title": {"type": "string"},
                                    "details": {"type": "string", "format": "uri"}
                                },
                                "required": ["title", "details"]
                            }
                        }
                    },
                    "required": ["items"]
                }
            }
        }
    )

    raw = response.choices[0].message.content

    # The model returns a JSON object; support two shapes: {items:[...]} or just [{...}]
    import json
    try:
        data = json.loads(raw)
    except Exception:
        # Try to strip code fences or fall back empty
        raw = re.sub(r"```json\s*|```", "", raw)
        try:
            data = json.loads(raw)
        except Exception:
            return []

    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        items_raw = data["items"]
    elif isinstance(data, list):
        items_raw = data
    else:
        items_raw = []

    items: List[OutreachItem] = []
    for it in items_raw[:limit]:
        try:
            # Normalize date string to ISO or None
            date_val: Optional[str] = it.get("date") if isinstance(it, dict) else None
            if date_val:
                try:
                    d = datetime.date.fromisoformat(date_val)
                except Exception:
                    # try YYYY/MM/DD or YYYY.MM.DD
                    date_val2 = re.sub(r"[./]", "-", date_val)
                    try:
                        d = datetime.date.fromisoformat(date_val2)
                    except Exception:
                        d = None
            else:
                d = None

            category_val = it.get("category") if isinstance(it, dict) else None
            title_val = it.get("title") if isinstance(it, dict) else ""
            details_val = it.get("details") if isinstance(it, dict) else ""
            item = OutreachItem(
                category=str(category_val) if category_val else "外部発信",
                date=d,
                title=str(title_val) if title_val else "",
                details=str(details_val) if details_val else "",
            )
            items.append(item)
        except Exception:
            continue

    return items, len(items_raw)


def find_outreach(last_name: str, first_name: str, companies_name: Optional[str], department: Optional[str], limit: int = 10) -> List[OutreachItem]:
    """人物名と所属情報をもとにWeb検索し、外部発信情報を収集・整形する。"""
    name_variants = [f"{last_name} {first_name}", f"{first_name} {last_name}", f"{last_name}{first_name}"]

    # 1) 検索クエリ作成
    queries = _build_queries(last_name, first_name, companies_name, department)

    # 2) Google CSE検索とリンク収集
    candidate_results: List[Dict[str, Any]] = []
    for q in queries:
        results = _google_cse_search(q, num=10)
        normalized = _normalize_google_results(results, max_items=30)
        # 重複リンク除去
        existing_links = {c["link"] for c in candidate_results}
        for item in normalized:
            if item["link"] in existing_links:
                continue
            candidate_results.append(item)
            existing_links.add(item["link"])
        if len(candidate_results) >= limit * 5:
            break

    # 3) LLMで分類・整形
    items, _ = _classify_and_structure_with_gpt(name_variants, candidate_results, limit)
    return items[:limit]


def find_outreach_with_debug(last_name: str, first_name: str, companies_name: Optional[str], department: Optional[str], limit: int = 10, company_domain: Optional[str] = None) -> Tuple[List[OutreachItem], Dict[str, Any]]:
    """デバッグ情報付きで外部発信情報を返す。"""
    name_variants = [f"{last_name} {first_name}", f"{first_name} {last_name}", f"{last_name}{first_name}"]
    queries = _build_queries(last_name, first_name, companies_name, department)

    candidate_results: List[Dict[str, Any]] = []
    for q in queries:
        # 会社ドメインに限定した検索を先に試行し、0件なら全Webにフォールバック
        results = _google_cse_search(q, num=10, site=company_domain) if company_domain else _google_cse_search(q, num=10)
        if not results and company_domain:
            results = _google_cse_search(q, num=10)
        normalized = _normalize_google_results(results, max_items=30)
        existing_links = {c["link"] for c in candidate_results}
        for item in normalized:
            if item["link"] in existing_links:
                continue
            candidate_results.append(item)
            existing_links.add(item["link"])
        if len(candidate_results) >= limit * 5:
            break

    items, llm_items_count = _classify_and_structure_with_gpt(name_variants, candidate_results, limit)

    debug: Dict[str, Any] = {
        "queries": queries,
        "name_variants": name_variants,
        "candidates_count": len(candidate_results),
        "llm_items_count": llm_items_count,
        "final_count": len(items[:limit]),
    }
    return items[:limit], debug


