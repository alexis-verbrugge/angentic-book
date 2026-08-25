#!/usr/bin/env python3
"""CLI du workflow agentique d'ecriture de roman fantasy multi-personnages.

Etapes :
    python main.py premise                    # discussion interactive -> story_bible/premise.md
    python main.py world --list                # liste le pipeline de worldbuilding
    python main.py world --stage cosmology      # lance une etape de worldbuilding
    python main.py outline --chapters 12
    python main.py chapter --number 1 [--words 1800]
    python main.py sync --number 1             # re-synchronise la bible apres une edition manuelle
    python main.py critique --number 1         # critique litteraire severe et constructive
    python main.py import-notes --file mes_notes.txt      # importe des notes brutes dans la bible
    python main.py import-chapter --file brouillon.md --number 1   # importe un chapitre deja ecrit
    python main.py check                       # verification de coherence
    python main.py status                      # etat du plan, de la bible, repartition par POV
"""
import argparse

import config
import md_bible
import outline_store
from stage_chapter import sync_chapter, write_chapter
from stage_consistency import run_check
from stage_critique import run_critique
from stage_import import import_chapter, import_notes
from stage_outline import generate_outline
from stage_premise import run_premise_chat
from stage_world import list_stages, run_stage


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

    p_world = sub.add_parser(
        "world", help="Pipeline de worldbuilding complet (cosmologie, magie, geographie, histoire, ...)."
    )
    p_world.add_argument("--stage", help="Cle de l'etape a lancer (voir --list).")
    p_world.add_argument("--list", action="store_true", help="Liste les etapes de worldbuilding et leur avancement.")

    p_outline = sub.add_parser("outline", help="Genere/regenere le plan du roman.")
    p_outline.add_argument("--chapters", type=int, default=12, help="Nombre de chapitres vises.")

    p_chapter = sub.add_parser("chapter", help="Redige un chapitre.")
    p_chapter.add_argument("--number", type=int, required=True)
    p_chapter.add_argument("--words", type=int, default=1800)

    p_sync = sub.add_parser(
        "sync", help="Resynchronise la bible avec le texte actuel d'un chapitre (apres edition manuelle)."
    )
    p_sync.add_argument("--number", type=int, required=True)

    p_critique = sub.add_parser(
        "critique", help="Critique litteraire severe et constructive d'un chapitre (rythme, voix, style, ...)."
    )
    p_critique.add_argument("--number", type=int, required=True)

    p_import_notes = sub.add_parser(
        "import-notes", help="Importe des notes brutes (worldbuilding, personnages, evenements) dans la bible."
    )
    p_import_notes.add_argument("--file", required=True, help="Chemin du fichier texte/markdown a importer.")

    p_import_chapter = sub.add_parser(
        "import-chapter", help="Importe un chapitre deja redige et synchronise la bible a partir de son texte."
    )
    p_import_chapter.add_argument("--file", required=True, help="Chemin du fichier du chapitre a importer.")
    p_import_chapter.add_argument("--number", type=int, required=True)
    p_import_chapter.add_argument("--title", help="Titre du chapitre (si absent du plan).")
    p_import_chapter.add_argument("--pov", help="Personnage POV du chapitre (si absent du plan).")

    sub.add_parser("check", help="Verifie la coherence de l'ensemble des chapitres rediges.")
    sub.add_parser("status", help="Affiche l'etat du plan, de la bible d'univers et la repartition par POV.")

    args = parser.parse_args()

    if args.command == "premise":
        run_premise_chat()
    elif args.command == "world":
        if args.list or not args.stage:
            list_stages()
        else:
            run_stage(args.stage)
    elif args.command == "outline":
        generate_outline(num_chapters=args.chapters)
    elif args.command == "chapter":
        write_chapter(args.number, target_words=args.words)
    elif args.command == "sync":
        sync_chapter(args.number)
    elif args.command == "critique":
        run_critique(args.number)
    elif args.command == "import-notes":
        import_notes(args.file)
    elif args.command == "import-chapter":
        import_chapter(args.file, args.number, title=args.title, pov=args.pov)
    elif args.command == "check":
        run_check()
    elif args.command == "status":
        cmd_status()


if __name__ == "__main__":
    main()
