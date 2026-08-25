#!/usr/bin/env python3
"""Etape d'import : permet d'injecter du contenu deja existant (notes de
worldbuilding en vrac, fiches personnages, evenements prevus, chapitres deja
rediges avant d'utiliser cet outil) pour poser les bases sans tout re-taper
a la main.

Deux imports independants :
- import_notes(path)   : notes brutes -> entites de la bible d'univers.
- import_chapter(...)  : chapitre deja ecrit -> chapters/ + bible synchronisee
  (reutilise stage_chapter.sync_chapter).

Le fichier source n'est jamais modifie ni supprime."""
from pathlib import Path

import config
import md_bible
import outline_store
import workflow
from stage_chapter import sync_chapter

IMPORT_NOTES_SYSTEM_PROMPT = """Tu es un assistant d'ingestion de worldbuilding. On te fournit des \
notes brutes deja ecrites par l'auteur (worldbuilding, personnages, evenements, ou un melange des \
trois), potentiellement en vrac, mal structurees ou incompletes. Ta seule tache est d'extraire CHAQUE \
element identifiable (personnage, lieu, peuple/espece, culture, religion, faction, objet, regle ou \
element du systeme de magie, element cosmologique, evenement) et de l'enregistrer via \
record_bible_entry, dans la categorie la plus appropriee, en reutilisant les noms deja connus (liste \
fournie ci-dessous) quand ils correspondent a la meme entite plutot que d'en creer un doublon.

Regles strictes :
- N'invente et n'extrapole RIEN qui ne soit pas present ou clairement sous-entendu dans les notes \
fournies. Une information manquante doit rester absente du champ correspondant plutot que d'etre \
devinee.
- Pour un evenement qui n'a PAS ENCORE eu lieu dans l'histoire (evenement prevu/futur souhaite par \
l'auteur pour la suite), enregistre-le quand meme dans la categorie 'timeline' mais ajoute un champ \
'statut': 'a_venir' pour bien le distinguer des evenements passes etablis.
- Si une meme information apparait plusieurs fois dans les notes, ne l'enregistre qu'une seule fois \
par entite (fusionne).

Termine par un court resume (en francais), categorie par categorie, de ce qui a ete importe."""


def import_notes(source_path):
    """Lit un fichier texte/markdown de notes brutes et en extrait les
    entites vers la bible d'univers (story_bible/*.md)."""
    path = Path(source_path)
    if not path.exists():
        print(f"✗ Fichier introuvable : {path}")
        return

    raw_text = path.read_text(encoding="utf-8")
    content_text = f"{md_bible.summarize_names()}\n\nNotes brutes de l'auteur a importer :\n\n{raw_text}"

    summary = workflow.run_tool_loop(
        system_prompt=IMPORT_NOTES_SYSTEM_PROMPT,
        content=[{"type": "text", "text": content_text}],
        tools=[workflow.RECORD_BIBLE_TOOL],
        tool_handlers={
            "record_bible_entry": workflow.make_bible_handler(
                chapter_ref="import", source_label=f"import:{path.name}"
            )
        },
        max_tokens=4000,
        model=config.MODEL_LIGHT,
    )
    print(summary)
    print(
        "\n✓ Import termine. Relis/edite librement story_bible/*.md, et ajoute "
        "'- **verrouille**: oui' sur les fiches que tu considere definitives."
    )


def import_chapter(source_path, number, title=None, pov=None):
    """Copie un chapitre deja redige vers chapters/chapitre_XXX.md, cree (ou
    laisse intacte) l'entree de plan correspondante, puis synchronise la
    bible a partir de ce texte (reutilise stage_chapter.sync_chapter)."""
    source = Path(source_path)
    if not source.exists():
        print(f"✗ Fichier introuvable : {source}")
        return

    config.CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.CHAPTERS_DIR / f"chapitre_{number:03d}.md"
    dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"✓ Chapitre copie vers {dest}")

    if not outline_store.get_chapter(number):
        outline_store.upsert_chapter(
            {
                "number": number,
                "title": title or f"Chapitre {number} (importe)",
                "pov": pov or "",
                "objectif": "",
                "synopsis": "(chapitre importe, synopsis a completer si besoin)",
                "statut": "redige",
            }
        )
        print(
            "✓ Entree de plan minimale creee dans outline.md (a completer/regenerer via "
            "`python main.py outline` si besoin)."
        )

    print("→ Synchronisation de la bible a partir du texte importe...")
    sync_chapter(number)
