#!/usr/bin/env python3
"""Etape 3 : redaction d'un chapitre en prose, avec continuite par fil POV,
mise a jour de la bible (dont la chronologie partagee), et validation humaine.

Fournit aussi `sync_chapter`, pour re-synchroniser la bible apres une
edition manuelle d'un chapitre par l'auteur (liberte d'amelioration)."""
import config
import md_bible
import outline_store
import workflow

SAVE_CHAPTER_TOOL = {
    "name": "save_chapter_draft",
    "description": "Sauvegarde le texte final et integral du chapitre redige.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Texte integral du chapitre en prose."},
        },
        "required": ["content"],
    },
}

SYSTEM_PROMPT = """Tu es un romancier fantasy francophone qui ecrit un roman a plusieurs personnages \
(plusieurs POV en alternance). Tu ecris en prose immersive, dans la voix propre au personnage POV de ce \
chapitre (consulte sa fiche pour son registre/voix narrative), et respectes scrupuleusement la bible \
d'univers ainsi que le plan.

Regles importantes :
- Reste fidele au fil de continuite de CE personnage POV (ce qu'il sait, ou il se trouve), meme si \
d'autres chapitres se sont deroules entre-temps du point de vue d'autres personnages.
- Si tu introduis un nouvel element notable (personnage secondaire, lieu, objet, technique), appelle \
record_bible_entry.
- A la fin du chapitre, appelle aussi record_bible_entry pour mettre a jour la fiche du personnage POV \
lui-meme (ex: champs 'derniere_position', 'etat_actuel', et au premier chapitre le concernant, un champ \
'voix_narrative' decrivant son registre pour rester coherent dans les prochains chapitres).
- Si un evenement marquant se produit (combat, revelation, mort, deplacement majeur, rencontre entre \
personnages de fils differents), enregistre-le dans la categorie 'timeline' (champs libres, ex: \
'moment', 'personnages_impliques', 'lieu') pour permettre de verifier plus tard la coherence \
chronologique entre les differents fils POV.
- Utilise web_search si tu as besoin de verifier ou t'inspirer d'une reference reelle (mythologie, \
etymologie d'un nom, detail historique) que tu integres a l'univers.
- Prends en compte les eventuelles notes/directives de l'auteur fournies.

Termine en appelant save_chapter_draft UNE SEULE FOIS avec le texte integral et final du chapitre (pas \
de resume, la prose complete)."""


def _same_pov_previous_chapter(number, pov):
    """Cherche le dernier chapitre (numero < number) qui suit le meme personnage POV."""
    if not pov:
        return None, None
    for ch in reversed(outline_store.load_outline()):
        if ch["number"] < number and ch.get("pov", "").strip().lower() == pov.strip().lower():
            path = config.CHAPTERS_DIR / f"chapitre_{ch['number']:03d}.md"
            if path.exists():
                return ch["number"], path.read_text(encoding="utf-8")
    return None, None


def _continuity_context(number, pov):
    """Combine la continuite narrative immediate (chapitre precedent, tout POV
    confondu) et la continuite du fil de CE personnage (dernier chapitre ou il
    etait POV, potentiellement plus loin en arriere si d'autres POV se sont
    intercales)."""
    parts = []

    prev_path = config.CHAPTERS_DIR / f"chapitre_{number - 1:03d}.md"
    if number > 1 and prev_path.exists():
        parts.append(
            "Fin du chapitre precedent, pour la continuite narrative immediate du recit :\n"
            + prev_path.read_text(encoding="utf-8")[-1200:]
        )

    same_pov_number, same_pov_text = _same_pov_previous_chapter(number, pov)
    if same_pov_number and same_pov_number != number - 1 and same_pov_text:
        parts.append(
            f"Dernier passage suivant ce meme personnage POV ({pov}), au chapitre {same_pov_number}, "
            "pour la continuite de son fil narratif :\n" + same_pov_text[-1200:]
        )

    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def _author_notes(number):
    """Notes globales (story_bible/notes.md) + notes specifiques au chapitre
    (chapters/chapitre_XXX.notes.md), si l'auteur les a redigees a la main."""
    parts = []
    global_notes = config.BIBLE_DIR / "notes.md"
    if global_notes.exists():
        parts.append("Notes globales de l'auteur :\n" + global_notes.read_text(encoding="utf-8"))
    chapter_notes = config.CHAPTERS_DIR / f"chapitre_{number:03d}.notes.md"
    if chapter_notes.exists():
        parts.append(
            f"Notes de l'auteur specifiques au chapitre {number} :\n"
            + chapter_notes.read_text(encoding="utf-8")
        )
    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def write_chapter(number, target_words=1800):
    outline = outline_store.get_chapter(number)
    if not outline:
        print(f"✗ Chapitre {number} introuvable dans le plan. Lance d'abord `python main.py outline`.")
        return

    premise_path = config.BIBLE_DIR / "premise.md"
    premise_text = premise_path.read_text(encoding="utf-8") if premise_path.exists() else ""
    bible_summary = md_bible.summarize_names()
    pov = outline.get("pov", "")
    pov_sheet = md_bible.get_entity_text("characters", pov) if pov else None
    continuity = _continuity_context(number, pov)
    notes = _author_notes(number)

    saved = {}

    def handle_save(args):
        saved["content"] = args["content"]
        return "Chapitre sauvegarde."

    tools = [workflow.RECORD_BIBLE_TOOL, SAVE_CHAPTER_TOOL]
    if config.ENABLE_WEB_SEARCH:
        tools.insert(0, workflow.WEB_SEARCH_TOOL)

    def generate(feedback):
        saved.clear()
        content_text = (
            f"Premisse :\n{premise_text}\n\n{bible_summary}\n\n"
            f"Plan du chapitre {number} — {outline['title']}\n"
            f"POV : {pov}\nObjectif : {outline.get('objectif', '')}\n"
            f"Synopsis : {outline.get('synopsis', '')}"
        )
        if pov_sheet:
            content_text += f"\n\nFiche complete du personnage POV ({pov}) :\n{pov_sheet}"
        content_text += f"{continuity}{notes}\n\n"
        content_text += (
            f"Redige le chapitre {number} en francais, environ {target_words} mots, en prose complete, "
            "coherent avec la bible, le fil de ce personnage POV et la continuite narrative."
        )
        if feedback:
            content_text += f"\n\nFeedback de l'auteur sur la version precedente a prendre en compte : {feedback}"

        workflow.run_tool_loop(
            system_prompt=SYSTEM_PROMPT,
            content=[{"type": "text", "text": content_text}],
            tools=tools,
            tool_handlers={
                "record_bible_entry": workflow.make_bible_handler(
                    chapter_ref=f"chapitre {number}", source_label=f"chapitre {number}"
                ),
                "save_chapter_draft": handle_save,
            },
            max_tokens=8000,
        )
        return saved.get("content")

    def describe(content):
        if not content:
            print("✗ L'agent n'a pas produit de texte.")
            return
        word_count = len(content.split())
        print(f"\n=== Chapitre {number} — POV {pov} ({word_count} mots) ===\n")
        print(content[:1500] + ("..." if len(content) > 1500 else ""))

    result = workflow.validate_with_feedback(generate, describe)
    if result:
        config.CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
        path = config.CHAPTERS_DIR / f"chapitre_{number:03d}.md"
        path.write_text(f"# Chapitre {number} — {outline['title']}\n\n{result}\n", encoding="utf-8")
        outline_store.update_chapter_status(number, "redige")
        print(f"✓ Chapitre sauvegarde dans {path}")


SYNC_SYSTEM_PROMPT = """Tu relis un chapitre potentiellement modifie a la main par l'auteur (liberte \
d'edition). Compare son contenu avec la bible d'univers existante et mets a jour la bible \
(record_bible_entry) pour qu'elle reflete fidelement ce texte : elements nouveaux, changements de \
statut, corrections de noms, evenements a ajouter a la chronologie 'timeline'. N'invente rien qui ne \
soit pas dans le texte fourni. Si une entite est verrouillee par l'auteur, n'insiste pas. Termine par \
un court resume des changements effectues."""


def sync_chapter(number):
    """Re-synchronise la bible avec le contenu ACTUEL d'un chapitre (utile
    apres une edition manuelle du fichier .md par l'auteur)."""
    path = config.CHAPTERS_DIR / f"chapitre_{number:03d}.md"
    if not path.exists():
        print(f"✗ Chapitre {number} introuvable ({path}).")
        return

    outline = outline_store.get_chapter(number)
    pov = outline.get("pov", "") if outline else ""
    text = path.read_text(encoding="utf-8")
    content_text = (
        f"{md_bible.summarize_names()}\n\nTexte actuel du chapitre {number} (POV : {pov}) :\n\n{text}"
    )

    summary = workflow.run_tool_loop(
        system_prompt=SYNC_SYSTEM_PROMPT,
        content=[{"type": "text", "text": content_text}],
        tools=[workflow.RECORD_BIBLE_TOOL],
        tool_handlers={
            "record_bible_entry": workflow.make_bible_handler(
                chapter_ref=f"chapitre {number} (sync)", source_label=f"edition manuelle chapitre {number}"
            )
        },
        max_tokens=2000,
    )
    print(summary)
    print("✓ Bible resynchronisee avec le texte actuel du chapitre.")
