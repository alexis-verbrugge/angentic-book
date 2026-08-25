#!/usr/bin/env python3
"""CLI du workflow agentique d'ecriture de roman fantasy multi-personnages.

Etapes :
    python main.py premise              # discussion interactive -> story_bible/premise.md
    python main.py outline --chapters 12
    python main.py chapter --number 1 [--words 1800]
    python main.py sync --number 1      # re-synchronise la bible apres une edition manuelle
    python main.py check                # verification de coherence
    python main.py status               # etat du plan, de la bible, et repartition par POV
"""
import argparse

import config
import md_bible
import outline_store
from stage_chapter import sync_chapter, write_chapter
from stage_consistency import run_check
from stage_outline import generate_outline
from stage_premise import run_premise_chat


def cmd_status():
    chapters = outline_store.load_outline()
    print("=== Plan du roman ===")
    pov_word_counts = {}
    if not chapters:
        print("Aucun plan genere. Lance `python main.py outline`.")
    else:
        for ch in chapters:
            path = config.CHAPTERS_DIR / f"chapitre_{ch['number']:03d}.md"
            words = len(path.read_text(encoding="utf-8").split()) if path.exists() else 0
            pov = ch.get("pov") or "?"
            pov_word_counts[pov] = pov_word_counts.get(pov, 0) + words
            print(f"Chapitre {ch['number']} — {ch['title']} [{ch['statut']}] POV: {pov} ({words} mots)")

        print("\n=== Repartition par personnage POV ===")
        for pov, words in sorted(pov_word_counts.items(), key=lambda item: -item[1]):
            print(f"- {pov}: {words} mots")

    print("\n=== Bible d'univers ===")
    for category in md_bible.CATEGORIES:
        names = md_bible.list_names(category)
        print(f"- {category}: {len(names)} entree(s)")


def main():
    parser = argparse.ArgumentParser(description="Workflow agentique d'ecriture de roman fantasy.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("premise", help="Discussion interactive pour definir la premisse du roman.")

    p_outline = sub.add_parser("outline", help="Genere/regenere le plan du roman.")
    p_outline.add_argument("--chapters", type=int, default=12, help="Nombre de chapitres vises.")

    p_chapter = sub.add_parser("chapter", help="Redige un chapitre.")
    p_chapter.add_argument("--number", type=int, required=True)
    p_chapter.add_argument("--words", type=int, default=1800)

    p_sync = sub.add_parser(
        "sync", help="Resynchronise la bible avec le texte actuel d'un chapitre (apres edition manuelle)."
    )
    p_sync.add_argument("--number", type=int, required=True)

    sub.add_parser("check", help="Verifie la coherence de l'ensemble des chapitres rediges.")
    sub.add_parser("status", help="Affiche l'etat du plan, de la bible d'univers et la repartition par POV.")

    args = parser.parse_args()

    if args.command == "premise":
        run_premise_chat()
    elif args.command == "outline":
        generate_outline(num_chapters=args.chapters)
    elif args.command == "chapter":
        write_chapter(args.number, target_words=args.words)
    elif args.command == "sync":
        sync_chapter(args.number)
    elif args.command == "check":
        run_check()
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()
