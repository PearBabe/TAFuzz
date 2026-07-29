#!/usr/bin/env python3
"""Create a read-only, reproducible snapshot of selected Zotero collections."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:23119/api/users/0"


def api_json(route: str, params: dict[str, object] | None = None) -> object:
    query = urllib.parse.urlencode(params or {})
    url = f"{BASE_URL}/{route.lstrip('/')}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def paged(route: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    start = 0
    limit = 100
    while True:
        page = api_json(route, {"start": start, "limit": limit, "include": "data"})
        if not isinstance(page, list):
            raise RuntimeError(f"Expected list from {route}, got {type(page).__name__}")
        records.extend(page)
        if len(page) < limit:
            return records
        start += limit


def safe_fulltext(attachment_key: str) -> dict[str, object]:
    try:
        payload = api_json(f"items/{attachment_key}/fulltext")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {"available": False, "http_status": 404}
        raise
    if not isinstance(payload, dict):
        return {"available": False, "unexpected_payload": type(payload).__name__}
    content = payload.get("content")
    return {
        "available": isinstance(content, str) and bool(content.strip()),
        "indexedPages": payload.get("indexedPages"),
        "totalPages": payload.get("totalPages"),
        "content": content if isinstance(content, str) else "",
    }


def snapshot_collection(key: str, label: str, out_dir: Path) -> dict[str, object]:
    raw_collection = api_json(f"collections/{key}")
    all_items = paged(f"collections/{key}/items")
    top_items = [
        item
        for item in all_items
        if not item.get("data", {}).get("parentItem")
        and item.get("data", {}).get("itemType") not in {"attachment", "note"}
    ]

    collection_dir = out_dir / label
    fulltext_dir = collection_dir / "fulltext"
    fulltext_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for item in top_items:
        data = item.get("data", {})
        item_key = str(data.get("key", item.get("key", "")))
        children = api_json(f"items/{item_key}/children", {"limit": 100, "include": "data"})
        if not isinstance(children, list):
            children = []

        attachment_records: list[dict[str, object]] = []
        for child in children:
            child_data = child.get("data", {})
            if child_data.get("itemType") != "attachment":
                continue
            attachment_key = str(child_data.get("key", child.get("key", "")))
            fulltext = safe_fulltext(attachment_key)
            content = str(fulltext.pop("content", ""))
            fulltext_path = None
            if content.strip():
                target = fulltext_dir / f"{item_key}__{attachment_key}.txt"
                target.write_text(content, encoding="utf-8")
                fulltext_path = str(target.resolve())
            attachment_records.append(
                {
                    "key": attachment_key,
                    "title": child_data.get("title"),
                    "contentType": child_data.get("contentType"),
                    "filename": child_data.get("filename"),
                    "url": child_data.get("url"),
                    "fulltext": fulltext,
                    "fulltext_path": fulltext_path,
                }
            )

        records.append(
            {
                "key": item_key,
                "itemType": data.get("itemType"),
                "title": data.get("title"),
                "date": data.get("date"),
                "creators": data.get("creators", []),
                "abstractNote": data.get("abstractNote"),
                "publicationTitle": data.get("publicationTitle"),
                "proceedingsTitle": data.get("proceedingsTitle"),
                "publisher": data.get("publisher"),
                "DOI": data.get("DOI"),
                "url": data.get("url"),
                "citationKey": data.get("citationKey"),
                "tags": data.get("tags", []),
                "attachments": attachment_records,
            }
        )

    result = {
        "collection": raw_collection,
        "collection_key": key,
        "label": label,
        "top_level_item_count": len(records),
        "items": records,
    }
    collection_dir.mkdir(parents=True, exist_ok=True)
    (collection_dir / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collection",
        action="append",
        required=True,
        metavar="KEY:LABEL",
        help="Collection key and filesystem label; repeat for multiple collections",
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    for specification in args.collection:
        key, separator, label = specification.partition(":")
        if not separator or not key or not label:
            parser.error(f"Invalid --collection value: {specification!r}")
        result = snapshot_collection(key, label, args.out_dir)
        summary.append(
            {
                "collection_key": key,
                "label": label,
                "top_level_item_count": result["top_level_item_count"],
            }
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
