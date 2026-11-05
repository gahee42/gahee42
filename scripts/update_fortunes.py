#!/usr/bin/env python3
"""Refresh only the fortune-cookie block. Python 3.10+, standard library only."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import random
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- FORTUNE-COOKIES:START -->"
END = "<!-- FORTUNE-COOKIES:END -->"
KST = timezone(timedelta(hours=9), "KST")
CATEGORIES = {"encouragement", "developer_joke"}


def parse_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Date must use YYYY-MM-DD.")
    return date.fromisoformat(value)


def today_kst() -> date:
    return datetime.now(KST).date()


def load_fortunes(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) < 3:
        raise ValueError("The fortune pool must be an array with at least 3 messages.")

    seen_ids: set[str] = set()
    seen_text: set[str] = set()
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Fortune {index} must be an object.")
        for key in ("id", "category", "text"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Fortune {index} needs a nonempty string: {key}.")
        if item["id"] != item["id"].strip() or item["text"] != item["text"].strip():
            raise ValueError(f"Fortune {index} has leading or trailing whitespace.")
        if item["category"] not in CATEGORIES:
            raise ValueError(f"Fortune {index} has an unknown category.")
        if item["id"] in seen_ids or item["text"] in seen_text:
            raise ValueError("Fortune IDs and message texts must both be unique.")
        if "\n" in item["text"] or "\r" in item["text"]:
            raise ValueError(f"Fortune {index} must be a single line.")
        seen_ids.add(item["id"])
        seen_text.add(item["text"])

    if {item["category"] for item in data} != CATEGORIES:
        raise ValueError("Include at least one encouragement and one developer_joke.")
    return data


def choose_daily_fortunes(
    fortunes: list[dict[str, str]], day: date, namespace: str = "gahee42"
) -> list[dict[str, str]]:
    """Pick 3 distinct messages, mixing both categories; same date => same draw."""
    # Stable ordering means rearranging the JSON does not change today's draw.
    pool = sorted(fortunes, key=lambda item: item["id"])
    seed = hashlib.sha256(f"fortune-v1|{namespace}|{day.isoformat()}".encode()).digest()
    rng = random.Random(int.from_bytes(seed, "big"))
    selected = [
        rng.choice([item for item in pool if item["category"] == category])
        for category in ("encouragement", "developer_joke")
    ]
    chosen_ids = {item["id"] for item in selected}
    selected.append(rng.choice([item for item in pool if item["id"] not in chosen_ids]))
    rng.shuffle(selected)
    return selected


def render_block(fortunes: list[dict[str, str]], day: date) -> str:
    lines = [
        "## 🥠 오늘의 포춘쿠키",
        "",
        "잠깐 쉬어 가세요. 마음이 가는 쿠키 하나를 골라 열어 보세요.",
        "",
        f"*{day.isoformat()} · 한국 시간 기준으로 하루에 한 번 구워요.*",
        "",
    ]
    for label, fortune in zip(("첫 번째", "두 번째", "세 번째"), fortunes, strict=True):
        lines.extend([
            "<details>",
            f"<summary>🥠 {label} 쿠키 열기</summary>",
            "",
            f"<p>{escape(fortune['text'])}</p>",
            "",
            "</details>",
            "",
        ])
    lines.extend([
        "<sub>오늘은 모두에게 같은 세 가지 쿠키가 보여요. 내일 또 들러 주세요 ☕</sub>",
    ])
    return "\n".join(lines)


def replace_block(readme: str, block: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one START marker and one END marker.")
    start = readme.index(START) + len(START)
    end = readme.index(END)
    if start > end:
        raise ValueError("The START marker must appear before the END marker.")
    newline = "\r\n" if "\r\n" in readme else "\n"
    return readme[:start] + newline + block.replace("\n", newline) + newline + readme[end:]


def update_readme(readme_path: Path, pool_path: Path, day: date, namespace: str) -> bool:
    fortunes = load_fortunes(pool_path)
    original_bytes = readme_path.read_bytes()
    original = original_bytes.decode("utf-8")
    selected = choose_daily_fortunes(fortunes, day, namespace)
    updated = replace_block(original, render_block(selected, day)).encode("utf-8")
    if updated == original_bytes:
        return False
    readme_path.write_bytes(updated)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--pool", type=Path, default=ROOT / "data" / "fortunes.json")
    parser.add_argument("--date", help="Test date in YYYY-MM-DD; default: today's date in KST.")
    parser.add_argument("--namespace", default="gahee42", help="Stable seed namespace, e.g. your username.")
    args = parser.parse_args(argv)
    try:
        day = parse_date(args.date) if args.date else today_kst()
        changed = update_readme(args.readme, args.pool, day, args.namespace)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Fortune update failed: {exc}", file=sys.stderr)
        return 1
    print(f"{'Updated' if changed else 'Already current'}: {args.readme.name} ({day.isoformat()}, KST)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
