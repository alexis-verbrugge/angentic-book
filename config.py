#!/usr/bin/env python3
"""Configuration centrale du workflow (cle API, modele, chemins)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() != "false"

BASE_DIR = Path(__file__).resolve().parent
BIBLE_DIR = BASE_DIR / "story_bible"
CHAPTERS_DIR = BASE_DIR / "chapters"
REPORTS_DIR = BASE_DIR / "reports"
