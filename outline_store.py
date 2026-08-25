#!/usr/bin/env python3
"""Stockage du plan du roman (outline.md) : un chapitre = un bloc Markdown
avec statut, POV, objectif narratif et synopsis."""
import re

from config import BIBLE_DIR

OUTLINE_PATH = BIBLE_DIR / "outline.md"


def save_outline(chapters):
    """chapters: liste de dict {number, title, pov, objectif, synopsis, statut?}"""
    BIBLE_DIR.mkdir(parents=True, exist_ok=True)
    blocks = ["# Plan du roman", ""]
    for ch in sorted(chapters, key=lambda c: c["number"]):
        blocks.append(f"## Chapitre {ch['number']} — {ch['title']}")
        blocks.append("")
        blocks.append(f"- **statut**: {ch.get('statut', 'planifie')}")
        blocks.append(f"- **pov**: {ch.get('pov', '')}")
        blocks.append(f"- **objectif**: {ch.get('objectif', '')}")
        blocks.append("")
        blocks.append("Synopsis :")
        blocks.append(ch.get("synopsis", ""))
        blocks.append("")
    OUTLINE_PATH.write_text("\n".join(blocks), encoding="utf-8")


def _extract_field(block, key):
    m = re.search(rf"-\s+\*\*{key}\*\*:\s*(.*)", block)
    return m.group(1).strip() if m else ""


def load_outline():
    if not OUTLINE_PATH.exists():
        return []
    text = OUTLINE_PATH.read_text(encoding="utf-8")
    chapters = []
    blocks = re.split(r"(?=^## Chapitre )", text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block.startswith("## Chapitre"):
            continue
        header_match = re.match(r"## Chapitre (\d+)\s*—\s*(.+)", block.splitlines()[0])
        if not header_match:
            continue
        synopsis_match = re.search(r"Synopsis\s*:\s*\n(.+)", block, re.DOTALL)
        chapters.append(
            {
                "number": int(header_match.group(1)),
                "title": header_match.group(2).strip(),
                "statut": _extract_field(block, "statut") or "planifie",
                "pov": _extract_field(block, "pov"),
                "objectif": _extract_field(block, "objectif"),
                "synopsis": synopsis_match.group(1).strip() if synopsis_match else "",
            }
        )
    return sorted(chapters, key=lambda c: c["number"])


def get_chapter(number):
    for ch in load_outline():
        if ch["number"] == number:
            return ch
    return None


def update_chapter_status(number, statut):
    chapters = load_outline()
    for ch in chapters:
        if ch["number"] == number:
            ch["statut"] = statut
    save_outline(chapters)
